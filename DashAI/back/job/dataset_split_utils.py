"""Shared "load raw dataset, prepare for task, instantiate splitter" logic.

Used by both `ModelJob` (training a single Run) and `SessionPreprocessingJob`
(fitting/transforming session converters once, ahead of any Run). Kept in its
own module so neither job has to import from the other.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from DashAI.back.dependencies.database.models import Dataset, ModelSession
from DashAI.back.job.base_job import JobError
from DashAI.back.splitters.base_splitter import BaseSplitter
from DashAI.back.tasks.base_task import BaseTask

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)

NO_OUTPUT_PLACEHOLDER_COLUMN = "__no_output_placeholder__"
"""Reserved column name used as `Y` when a session has no output columns yet
(the wizard's Preprocessing step comes before its Columns step). A
`DashAIDataset` with zero columns always reports zero rows — a
`datasets.Dataset` quirk, `num_rows` isn't derived from the arrow table's
actual row count once there are no columns — so a genuinely empty `Y` can't
track `X`'s row count through the splitter. Callers that persist a session's
preprocessed partitions (`SessionPreprocessingJob`) must strip this column
back out rather than merge it in as a real output column.
"""


def load_dataset_and_splitter(
    model_session: ModelSession,
    db: Any,
    component_registry: "ComponentRegistry",
    splitted_indexes: Optional[Dict[str, Any]] = None,
) -> Tuple["DashAIDataset", "DashAIDataset", BaseSplitter, BaseTask, "DashAIDataset"]:
    """Load a session's raw dataset, prepare it for its task, and build its
    configured splitter, ready to call `.split(X, Y)`.

    Parameters
    ----------
    model_session : ModelSession
        The session whose `dataset_id`, `task_name`, `input_columns`,
        `output_columns`, and `splits` configuration drive this.
    db : Session
        Database session, used to load the `Dataset` row.
    component_registry : ComponentRegistry
        Used to resolve the task and splitter classes by name.
    splitted_indexes : dict, optional
        Previously computed split indices to reuse (e.g. a `Run`'s
        `split_indexes`) instead of letting the splitter recompute them.
        Defaults to None (always recompute).

    Returns
    -------
    tuple
        `(X, Y, splitter, task, prepared_dataset)`: the input/output column
        datasets and the instantiated splitter, ready for
        `splitter.split(X, Y)` — plus the task instance and the (still
        unsplit) task-prepared dataset, since `ModelJob` needs those to
        compute `n_labels` for its `ModelFactory`.

    Raises
    ------
    JobError
        If the dataset, task, or splitter cannot be loaded/resolved.
    """
    from DashAI.back.dataloaders.classes.dashai_dataset import (
        load_dataset,
        select_columns,
    )

    dataset: Dataset = db.get(Dataset, model_session.dataset_id)
    if not dataset:
        raise JobError(f"Dataset {model_session.dataset_id} does not exist in DB.")

    try:
        loaded_dataset: "DashAIDataset" = load_dataset(f"{dataset.file_path}/dataset")
    except Exception as e:
        log.exception(e)
        raise JobError(f"Can not load dataset from path {dataset.file_path}") from e

    try:
        task: BaseTask = component_registry[model_session.task_name]["class"]()
    except Exception as e:
        log.exception(e)
        raise JobError(
            f"Unable to find Task with name {model_session.task_name} in registry"
        ) from e

    def _build_placeholder_xy():
        # No output column chosen yet (the wizard's Preprocessing step comes
        # before its Columns step) — nothing to validate against the task
        # yet, so skip `prepare_for_task` entirely. Treat the whole dataset
        # as X; Y carries only `NO_OUTPUT_PLACEHOLDER_COLUMN` (see its
        # docstring for why a genuinely empty Y can't work here), so the
        # splitter and `apply_session_converters` keep working uniformly. A
        # `SUPERVISED` converter that needs a real target in this state
        # supplies its own `target_column` (see `fit_transform_on_partition`
        # in `execution.py`), pulled out of X directly.
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import (
            DashAIDataset,
            to_dashai_dataset,
        )

        placeholder_prepared = to_dashai_dataset(loaded_dataset)
        try:
            placeholder_x = placeholder_prepared
            placeholder_y = DashAIDataset(
                table=pa.table(
                    {
                        NO_OUTPUT_PLACEHOLDER_COLUMN: pa.array(
                            [0] * len(placeholder_prepared), type=pa.int64()
                        )
                    }
                )
            )
        except Exception as e:
            log.exception(e)
            raise JobError(f"Error selecting columns from dataset {dataset.id}") from e
        return placeholder_x, placeholder_y, placeholder_prepared

    if model_session.output_columns:
        try:
            prepared_dataset = task.prepare_for_task(
                dataset=loaded_dataset,
                input_columns=model_session.input_columns,
                output_columns=model_session.output_columns,
            )
            X, Y = select_columns(
                prepared_dataset,
                model_session.input_columns,
                model_session.output_columns,
            )
        except Exception as e:
            if not model_session.converters:
                log.exception(e)
                raise JobError(
                    f"""Can not prepare Dataset {dataset.id}
                    for Task {model_session.task_name}""",
                ) from e
            # Converters can add or rename columns the raw dataset never had
            # (e.g. `LabelEncoder` appending `le_<col>`), so a session's
            # final input/output selection may not resolve against the raw
            # data once one of those columns is picked. This function's
            # result is only used for row-index bookkeeping in that case —
            # callers that need the real, typed prepared dataset when
            # converters are present must load it from the preprocessed
            # partitions instead (see `load_preprocessed_reference_dataset`
            # in `session_preprocessing_job.py`).
            log.info(
                "Falling back to a placeholder split for session %s: "
                "input/output columns don't resolve against the raw "
                "dataset (likely converter-produced columns): %s",
                model_session.id,
                e,
            )
            X, Y, prepared_dataset = _build_placeholder_xy()
    else:
        X, Y, prepared_dataset = _build_placeholder_xy()

    try:
        splits_data = json.loads(model_session.splits)
        if splitted_indexes:
            splits_data["splitted_indexes"] = splitted_indexes
    except Exception as e:
        log.exception(e)
        raise JobError(
            f"Can not load splits data from model session {model_session.id}"
        ) from e

    try:
        splitter_name = splits_data.get("splitter_name", None)
        splitter: BaseSplitter = component_registry[splitter_name]["class"](
            splits_data=splits_data,
        )
    except Exception as e:
        log.exception(e)
        raise JobError(
            f"""Unable to find Splitter with name
            {splitter_name} in registry.""",
        ) from e

    return X, Y, splitter, task, prepared_dataset
