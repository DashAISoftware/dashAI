import logging
import os
import shutil
from typing import TYPE_CHECKING, Any, Tuple

from kink import inject
from sqlalchemy import exc

from DashAI.back.converters.execution import (
    apply_session_converters,
    fitted_converters_path,
    save_fitted_converters,
)
from DashAI.back.dependencies.database.models import ModelSession
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.job.dataset_split_utils import load_dataset_and_splitter

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def _merge_input_output_columns(
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
        # Not `model_session.input_columns`: converters like PCA or an
        # encoder can rename/add/drop input columns, so those names go
        # stale. Output columns are never renamed by any converter, so
        # they're the only safe fixed point — everything else is input.
        output_columns = model_session.output_columns
        input_columns = [
            col for col in combined.column_names if col not in output_columns
        ]
        return select_columns(combined, input_columns, output_columns)

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

                if isinstance(x, list):
                    last_index = len(x) - 1
                    for i, (x_fold, y_fold) in enumerate(zip(x, y, strict=True)):
                        fold_name = "full_dataset" if i == last_index else f"fold_{i}"
                        for split_name, x_part in x_fold.items():
                            if len(x_part) == 0:
                                continue
                            combined = _merge_input_output_columns(
                                x_part, y_fold[split_name]
                            )
                            save_dataset(
                                combined,
                                os.path.join(session_dir, fold_name, split_name),
                            )
                else:
                    for split_name, x_part in x.items():
                        if len(x_part) == 0:
                            continue
                        combined = _merge_input_output_columns(x_part, y[split_name])
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
