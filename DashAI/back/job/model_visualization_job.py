"""Job that turns a trained model into renderable artifacts."""

import logging
from typing import TYPE_CHECKING, List, Optional

from kink import inject
from sqlalchemy import exc

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ModelVisualizationJob(BaseJob):
    """Generate renderable views of a trained model.

    Reads the run's trained model back from disk, rebuilds the training split
    it was fitted on, calls the model's ``get_model_artifacts`` hook, and
    persists the normalized artifacts next to the run so the frontend can read
    them back without recomputing.
    """

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Mark the run's visualization as queued.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory producing a SQLAlchemy session.

        Raises
        ------
        JobError
            If the run does not exist or the database rejects the update.
        """
        run_id: int = self.kwargs["run_id"]
        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                raise JobError(f"Run with id {run_id} does not exist in DB.")
            try:
                run.model_artifacts_status = RunStatus.DELIVERED
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Internal database error") from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Mark the run's visualization as failed.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory producing a SQLAlchemy session.
        """
        run_id: Optional[int] = self.kwargs.get("run_id")
        if run_id is None:
            return
        with session_factory() as db:
            try:
                run: Run = db.get(Run, run_id)
                if run:
                    run.model_artifacts_status = RunStatus.ERROR
                    db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    def get_job_name(self) -> str:
        """Build a descriptive name for this job.

        Returns
        -------
        str
            The run's name when it can be read, a generic label otherwise.
        """
        run_id = self.kwargs.get("run_id")
        if not run_id:
            return "Model visualization"

        from kink import di

        try:
            with di["session_factory"]() as db:
                run: Run = db.get(Run, run_id)
                if run and run.name:
                    return f"Visualize: {run.name}"
        except Exception:
            pass
        return f"Model visualization ({run_id})"

    @staticmethod
    def _class_names(model: BaseModel) -> Optional[List[str]]:
        """Recover the human readable class labels of a fitted classifier.

        The label encoder stores ``{column: {label: index}}``. Only the output
        column is relevant here, and the labels are returned in encoded order
        so a class index can be used to look one up directly.

        Parameters
        ----------
        model : BaseModel
            The trained model, which may carry output encodings.

        Returns
        -------
        Optional[List[str]]
            Class labels in encoded order, or None for a regressor.
        """
        encodings = getattr(model, "output_encodings", None)
        mapping = next(iter(encodings.values()), None) if encodings else None
        if mapping:
            return [
                str(label) for label, _ in sorted(mapping.items(), key=lambda p: p[1])
            ]
        # A classifier trained on already numeric targets has no encodings, so
        # fall back to the estimator's own classes. Regressors have neither and
        # correctly yield None.
        classes = getattr(model, "classes_", None)
        if classes is None:
            return None
        return [str(label) for label in classes]

    def _save(self, run: Run, artifacts: List[dict], db) -> None:
        """Pickle the artifacts and record their path on the run.

        Parameters
        ----------
        run : Run
            The run being visualized.
        artifacts : List[dict]
            Normalized artifact wire dicts.
        db : Session
            The open SQLAlchemy session.

        Raises
        ------
        JobError
            If the file cannot be written or the row cannot be updated.
        """
        import os
        import pickle

        from kink import di

        config = di["config"]
        try:
            path = os.path.join(config["RUNS_PATH"], f"model_artifacts_{run.id}.pickle")
            with open(path, "wb") as file:
                pickle.dump(artifacts, file)
        except Exception as e:
            log.exception(e)
            raise JobError("Model artifacts file saving failed") from e

        try:
            run.model_artifacts_path = path
            run.model_artifacts_status = RunStatus.FINISHED
            db.commit()
        except Exception as e:
            log.exception(e)
            raise JobError("Model artifacts path saving failed") from e

    @inject
    def run(self) -> None:
        """Generate and persist the run's model artifacts.

        Raises
        ------
        JobError
            If any stage of the reconstruction or generation fails.
        """
        import json

        from kink import di

        from DashAI.back.core.artifacts import normalize_artifacts
        from DashAI.back.dataloaders.classes.dashai_dataset import (
            load_dataset,
            select_columns,
            split_dataset,
        )
        from DashAI.back.models.model_artifact_context import ModelArtifactContext
        from DashAI.back.tasks.base_task import BaseTask

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        run_id: int = self.kwargs["run_id"]

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                raise JobError(f"Run with id {run_id} does not exist in DB.")

            try:
                model_session: ModelSession = db.get(ModelSession, run.model_session_id)
                if not model_session:
                    raise JobError(
                        f"Model session {run.model_session_id} does not exist in DB."
                    )
                dataset: Dataset = db.get(Dataset, model_session.dataset_id)
                if not dataset:
                    raise JobError(
                        f"Dataset {model_session.dataset_id} does not exist in DB."
                    )

                try:
                    run.model_artifacts_status = RunStatus.STARTED
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError("Connection with the database failed") from e

                try:
                    model_class = component_registry[run.model_name]["class"]
                    model: BaseModel = model_class(**run.parameters)
                    trained_model = model.load(run.run_path)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Can not load model {run.model_name} from {run.run_path}"
                    ) from e

                # A model without the hook is not a failure: the run simply has
                # nothing to show, and an empty artifact list says so.
                if not type(trained_model).supports_model_artifacts():
                    self._save(run, [], db)
                    return

                self.report_progress(0.3, "Rebuilding the training split")
                try:
                    # Same reconstruction the explainer job performs: split,
                    # prepare for the task, select the input/output columns,
                    # then split each side.
                    loaded_dataset = load_dataset(f"{dataset.file_path}/dataset")
                    splits = json.loads(run.split_indexes)
                    loaded_dataset = split_dataset(
                        loaded_dataset,
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )
                    task: BaseTask = component_registry[model_session.task_name][
                        "class"
                    ]()
                    prepared_dataset = task.prepare_for_task(
                        dataset=loaded_dataset,
                        input_columns=model_session.input_columns,
                        output_columns=model_session.output_columns,
                    )
                    data_x, data_y = select_columns(
                        prepared_dataset,
                        model_session.input_columns,
                        model_session.output_columns,
                    )
                    data_x = split_dataset(
                        data_x,
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )
                    data_y = split_dataset(
                        data_y,
                        train_indexes=splits["train_indexes"],
                        test_indexes=splits["test_indexes"],
                        val_indexes=splits["val_indexes"],
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Can not prepare dataset {dataset.id} for the visualization"
                    ) from e

                self.report_progress(0.6, "Generating the visualization")
                try:
                    # The context is expressed in the model's own feature space
                    # so tree feature names match the columns it split on.
                    x_prepared = trained_model.prepare_dataset(
                        data_x["train"], is_fit=False
                    ).to_pandas()
                    y_prepared = trained_model.prepare_output(
                        data_y["train"], is_fit=False
                    ).to_pandas()
                    context = ModelArtifactContext(
                        x_train=x_prepared,
                        y_train=y_prepared.to_numpy().ravel(),
                        feature_names=[str(c) for c in x_prepared.columns],
                        class_names=self._class_names(trained_model),
                    )
                    artifacts = normalize_artifacts(
                        trained_model.get_model_artifacts(context)
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError("Failed to generate the model visualization") from e

                self.report_progress(0.9, "Saving the visualization")
                self._save(run, artifacts, db)

            except Exception as e:
                run.model_artifacts_status = RunStatus.ERROR
                db.commit()
                raise e
