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

    try:
        prepared_dataset = task.prepare_for_task(
            dataset=loaded_dataset,
            input_columns=model_session.input_columns,
            output_columns=model_session.output_columns,
        )
    except Exception as e:
        log.exception(e)
        raise JobError(
            f"""Can not prepare Dataset {dataset.id}
            for Task {model_session.task_name}""",
        ) from e

    try:
        X, Y = select_columns(
            prepared_dataset,
            model_session.input_columns,
            model_session.output_columns,
        )
    except Exception as e:
        log.exception(e)
        raise JobError(
            f"Error selecting input and output columns from dataset {dataset.id}"
        ) from e

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
