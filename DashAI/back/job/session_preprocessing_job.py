import logging
import os
import shutil
from typing import TYPE_CHECKING, Any, Optional, Tuple

from kink import inject
from sqlalchemy import exc

from DashAI.back.converters.execution import (
    apply_session_converters,
    fitted_converters_path,
    save_fitted_converters,
)
from DashAI.back.dependencies.database.models import ModelSession
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.job.dataset_split_utils import (
    NO_OUTPUT_PLACEHOLDER_COLUMN,
    load_dataset_and_splitter,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def merge_input_output_columns(
    x_partition: "DashAIDataset", y_partition: "DashAIDataset"
) -> "DashAIDataset":
    """Combine a partition's input and output columns into a single dataset,
    so it can be saved/loaded as one unit with `save_dataset`/`load_dataset`
    (the same "one combined dataset" shape the raw dataset already has)."""
    from DashAI.back.dataloaders.classes.dashai_dataset import modify_table

    return modify_table(
        x_partition,
        {col: y_partition.arrow_table[col] for col in y_partition.column_names},
        types={col: y_partition.types[col] for col in y_partition.column_names},
    )


def load_preprocessed_session_data(model_session: ModelSession) -> Tuple[Any, Any]:
    """Load the partitions written by `SessionPreprocessingJob.run()` back
    into the `(x, y)` shape `BaseEvaluationStrategy.execute()` expects — a
    single `DatasetDict` for holdout, or a list of `DatasetDict` (one per
    fold, plus a final `full_dataset` entry) for cross-validation.

    Lives alongside the code that writes this layout so both stay in sync.

    Parameters
    ----------
    model_session : ModelSession
        Must have a non-empty `preprocessed_path` (i.e. preprocessing has
        already finished for this session).

    Raises
    ------
    JobError
        If `preprocessed_path` is unset, or a partition can't be loaded.
    """
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import (
        load_dataset,
        select_columns,
    )

    session_dir = model_session.preprocessed_path
    if not session_dir:
        raise JobError(
            f"Model session {model_session.id} has no preprocessed_path; "
            "preprocessing may not have run yet."
        )

    def _load_partition(path: str):
        combined = load_dataset(path)
        # `model_session.input_columns`/`output_columns` are the session's
        # *finalized* selection — set by the wizard's Columns step, which
        # only ever runs after preprocessing, offering exactly the current
        # (already-transformed) column set. They're trustworthy here for
        # the same reason: a converter that only *appends* columns (e.g.
        # `LabelEncoder`'s `le_<col>`, `BagOfWords`'s `bow_<word>`) leaves
        # the original column sitting in the saved partition too — taking
        # "everything except output" as input used to silently pull that
        # leftover original column (e.g. raw text) into training data the
        # user never selected, alongside real errors from anything that
        # can't convert to a numeric feature.
        return select_columns(
            combined, model_session.input_columns, model_session.output_columns
        )

    if os.path.isdir(os.path.join(session_dir, "train")):
        x, y = {}, {}
        for split_name in ("train", "validation", "test"):
            part_path = os.path.join(session_dir, split_name)
            if os.path.isdir(part_path):
                x[split_name], y[split_name] = _load_partition(part_path)
        return DatasetDict(x), DatasetDict(y)

    fold_names = sorted(
        (d for d in os.listdir(session_dir) if d.startswith("fold_")),
        key=lambda d: int(d.split("_")[1]),
    )

    x_list, y_list = [], []
    for fold_name in [*fold_names, "full_dataset"]:
        x_fold, y_fold = {}, {}
        for split_name in ("train", "test"):
            part_path = os.path.join(session_dir, fold_name, split_name)
            if os.path.isdir(part_path):
                x_fold[split_name], y_fold[split_name] = _load_partition(part_path)
        x_list.append(DatasetDict(x_fold))
        y_list.append(DatasetDict(y_fold))

    return x_list, y_list


def get_reference_partition_path(model_session: ModelSession) -> Optional[str]:
    """Path to the single partition that best represents a session's
    current preprocessed state: `full_dataset/train` for cross-validation,
    `train` for holdout. Mirrors `get_preprocessed_columns`'s own
    resolution logic in `model_sessions.py` (duplicated rather than
    imported — endpoints and jobs live in different layers).

    Returns None if the session has no `preprocessed_path`, or the
    partition isn't on disk.
    """
    if not model_session.preprocessed_path:
        return None
    is_cv = model_session.evaluation_strategy == "CrossValidationEvaluationStrategy"
    relative = os.path.join("full_dataset", "train") if is_cv else "train"
    partition_path = os.path.join(model_session.preprocessed_path, relative)
    return partition_path if os.path.isdir(partition_path) else None


def load_preprocessed_reference_dataset(
    model_session: ModelSession,
) -> "DashAIDataset":
    """Load the combined (input+output columns together) reference
    partition — the session's *actual* training data, including any column
    a converter added or renamed (e.g. `LabelEncoder` appending
    `le_<col>`). `ModelJob` uses this to validate/prepare the session's
    final input/output selection and compute `n_labels` when converters are
    present, since the raw dataset never had those converter-produced
    columns to validate against.
    """
    from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

    partition_path = get_reference_partition_path(model_session)
    if not partition_path:
        raise JobError(
            f"Model session {model_session.id} has no usable preprocessed "
            "reference partition."
        )
    return load_dataset(partition_path)


class SessionPreprocessingJob(BaseJob):
    """Fits/transforms a ModelSession's converters once, ahead of any Run.

    Splits the raw dataset the same way `ModelJob` would (holdout partitions,
    or cross-validation folds), applies `apply_session_converters` (fit only
    on each partition's train, transform the rest — never re-fit), and
    persists every resulting partition to disk under the session's own
    storage folder, plus the fitted converters used for the final model.
    """

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the session preprocessing as delivered."""
        model_session_id = self.kwargs["model_session_id"]

        with session_factory() as db:
            model_session = db.get(ModelSession, model_session_id)
            if model_session is None:
                raise JobError(
                    f"ModelSession with id {model_session_id} does not exist in DB."
                )
            try:
                model_session.set_preprocessing_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Error setting session preprocessing status as delivered"
                ) from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the session preprocessing as error."""
        model_session_id = self.kwargs.get("model_session_id")
        if model_session_id is None:
            return

        with session_factory() as db:
            model_session = db.get(ModelSession, model_session_id)
            if model_session is None:
                return
            try:
                model_session.set_preprocessing_status_as_error()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        model_session_id = self.kwargs.get("model_session_id")
        if not model_session_id:
            return "Session Preprocessing Job"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                model_session = db.get(ModelSession, model_session_id)
                if model_session and model_session.name:
                    return f"Preprocessing: {model_session.name}"
        except Exception as e:
            log.exception(f"Error getting job name: {e}")

        return f"Session Preprocessing Job #{model_session_id}"

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        from DashAI.back.dataloaders.classes.dashai_dataset import save_dataset

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        model_session_id: int = self.kwargs["model_session_id"]

        with session_factory() as db:
            model_session: ModelSession = db.get(ModelSession, model_session_id)
            if not model_session:
                raise JobError(
                    f"ModelSession with id {model_session_id} does not exist in DB."
                )

            try:
                model_session.set_preprocessing_status_as_started()
                db.commit()

                self.report_progress(0.1, "Loading dataset")
                X, Y, splitter, _task, _prepared_dataset = load_dataset_and_splitter(
                    model_session, db, component_registry
                )

                self.report_progress(0.2, "Splitting dataset")
                x, y, _splits = splitter.split(X, Y)

                self.report_progress(0.4, "Fitting converters")
                x, y, fitted_converters = apply_session_converters(
                    x, y, model_session.converters, component_registry
                )

                self.report_progress(0.7, "Saving preprocessed partitions")
                session_dir = os.path.join(
                    str(config["MODEL_SESSIONS_PATH"]), str(model_session.id)
                )
                # Clear any stale content first (e.g. a re-run, or a reused
                # session id after a previous session was deleted) so old
                # partitions from a different split shape never linger
                # alongside the new ones.
                if os.path.isdir(session_dir):
                    shutil.rmtree(session_dir)
                stale_converters_path = fitted_converters_path(session_dir)
                if os.path.exists(stale_converters_path):
                    os.remove(stale_converters_path)

                # `y` carries only the `NO_OUTPUT_PLACEHOLDER_COLUMN`
                # placeholder (see `dataset_split_utils.py`) whenever no
                # real output was available to split on — either no output
                # column has been chosen yet (the wizard's Preprocessing
                # step comes before its Columns step), or one was chosen
                # but doesn't resolve against the raw dataset (a converter
                # produced it, e.g. `LabelEncoder` appending `le_<col>`).
                # Checking `y` itself (not `model_session.output_columns`)
                # is what actually matches what's about to be merged below
                # — a converter-produced output column falls into the same
                # "no real output to merge" case even though
                # `output_columns` is set.
                first_y_partition = (
                    next(iter(y[0].values()))
                    if isinstance(y, list)
                    else next(iter(y.values()))
                )
                has_output_columns = (
                    NO_OUTPUT_PLACEHOLDER_COLUMN not in first_y_partition.column_names
                )

                if isinstance(x, list):
                    last_index = len(x) - 1
                    for i, (x_fold, y_fold) in enumerate(zip(x, y, strict=True)):
                        fold_name = "full_dataset" if i == last_index else f"fold_{i}"
                        for split_name, x_part in x_fold.items():
                            if len(x_part) == 0:
                                continue
                            combined = (
                                merge_input_output_columns(x_part, y_fold[split_name])
                                if has_output_columns
                                else x_part
                            )
                            save_dataset(
                                combined,
                                os.path.join(session_dir, fold_name, split_name),
                            )
                else:
                    for split_name, x_part in x.items():
                        if len(x_part) == 0:
                            continue
                        combined = (
                            merge_input_output_columns(x_part, y[split_name])
                            if has_output_columns
                            else x_part
                        )
                        save_dataset(combined, os.path.join(session_dir, split_name))

                save_fitted_converters(session_dir, fitted_converters)

                model_session.preprocessed_path = session_dir
                model_session.set_preprocessing_status_as_finished()
                db.commit()
            except Exception as e:
                log.exception(e)
                model_session.set_preprocessing_status_as_error()
                db.commit()
                raise JobError(
                    f"Error preprocessing session {model_session_id}: {e}"
                ) from e
