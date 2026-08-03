"""Job that turns a run's predictions over one split into reports."""

import logging
from typing import TYPE_CHECKING, List, Optional

from kink import inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import (
    Dataset,
    ModelSession,
    Report,
    Run,
)
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

#: Split name as stored on the row mapped to the key the split dict uses.
SPLIT_KEYS = {"train": "train", "validation": "validation", "test": "test"}


class ReportJob(BaseJob):
    """Compute one evaluation report for a run over one split.

    Rebuilds the requested split, predicts with the trained model, and hands
    the truth and the predictions to the report. The model's inputs are
    never passed on: a report compares predictions against the truth and
    nothing else, which is what separates it from an explainer.
    """

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Mark the report as queued.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory producing a SQLAlchemy session.

        Raises
        ------
        JobError
            If the report does not exist or the database rejects the update.
        """
        report_id: int = self.kwargs["report_id"]
        with session_factory() as db:
            report: Report = db.get(Report, report_id)
            if not report:
                raise JobError(f"Report with id {report_id} does not exist in DB.")
            try:
                report.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Internal database error") from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Mark the report as failed.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory producing a SQLAlchemy session.
        """
        report_id: Optional[int] = self.kwargs.get("report_id")
        if report_id is None:
            return
        with session_factory() as db:
            try:
                report: Report = db.get(Report, report_id)
                if report:
                    report.set_status_as_error()
                    db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    def get_job_name(self) -> str:
        """Build a descriptive name for this job.

        Returns
        -------
        str
            The report's name when it can be read, a generic label
            otherwise.
        """
        report_id = self.kwargs.get("report_id")
        if not report_id:
            return "Report"

        from kink import di

        try:
            with di["session_factory"]() as db:
                report: Report = db.get(Report, report_id)
                if report:
                    return f"Report: {report.report_name} ({report.split})"
        except Exception:
            pass
        return f"Report ({report_id})"

    @staticmethod
    def _class_names(model: BaseModel) -> Optional[List[str]]:
        """Recover the human readable class labels of a fitted classifier.

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
        classes = getattr(model, "classes_", None)
        if classes is None:
            return None
        return [str(label) for label in classes]

    @inject
    def run(self) -> None:
        """Compute and persist the report's artifacts.

        Raises
        ------
        JobError
            If any stage of the reconstruction or computation fails.
        """
        import json
        import os
        import pickle

        from kink import di

        from DashAI.back.core.artifacts import normalize_artifacts
        from DashAI.back.dataloaders.classes.dashai_dataset import (
            load_dataset,
            select_columns,
            split_dataset,
        )
        from DashAI.back.reports.base_report import ReportError
        from DashAI.back.tasks.base_task import BaseTask

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]
        report_id: int = self.kwargs["report_id"]

        with session_factory() as db:
            report: Report = db.get(Report, report_id)
            if not report:
                raise JobError(f"Report with id {report_id} does not exist in DB.")

            try:
                run: Run = db.get(Run, report.run_id)
                if not run:
                    raise JobError(f"Run {report.run_id} does not exist in DB.")
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

                split = report.split
                if split not in SPLIT_KEYS:
                    raise JobError(f"{split} is not a valid split")

                try:
                    report.set_status_as_started()
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

                try:
                    report_class = component_registry[report.report_name]["class"]
                    instance = report_class(**(report.parameters or {}))
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Unable to instantiate report {report.report_name}."
                    ) from e

                self.report_progress(0.3, "Rebuilding the split")
                try:
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
                        f"Can not prepare dataset {dataset.id} for the report"
                    ) from e

                self.report_progress(0.6, "Predicting")
                try:
                    split_key = SPLIT_KEYS[split]
                    # Inputs go in unprepared, exactly as the prediction job
                    # feeds them: the model applies its own preprocessing.
                    y_pred = trained_model.predict(data_x[split_key])
                    # Targets are encoded so they line up with the class
                    # indexes the model predicts.
                    y_true = (
                        trained_model.prepare_output(data_y[split_key], is_fit=False)
                        .to_pandas()
                        .to_numpy()
                        .ravel()
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Failed to predict the {split} split for the report"
                    ) from e

                self.report_progress(0.8, "Computing the report")
                try:
                    artifacts = normalize_artifacts(
                        instance.compute(
                            y_true, y_pred, self._class_names(trained_model)
                        )
                    )
                except ReportError as e:
                    log.exception(e)
                    raise JobError(str(e)) from e
                except Exception as e:
                    log.exception(e)
                    raise JobError("Failed to compute the report") from e

                try:
                    path = os.path.join(
                        config["RUNS_PATH"], f"report_{report_id}.pickle"
                    )
                    with open(path, "wb") as file:
                        pickle.dump(artifacts, file)
                except Exception as e:
                    log.exception(e)
                    raise JobError("Report file saving failed") from e

                try:
                    report.artifacts_path = path
                    report.plot_overrides = None
                    report.set_status_as_finished()
                    db.commit()
                except Exception as e:
                    log.exception(e)
                    raise JobError("Report path saving failed") from e

            except Exception as e:
                report.set_status_as_error()
                db.commit()
                raise e
