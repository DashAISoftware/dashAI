import logging
from typing import TYPE_CHECKING

from kink import inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.job.model_job_context import ModelJobContext
from DashAI.back.tasks.base_task import BaseTask

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ModelJob(BaseJob):
    """ModelJob class to run the model training."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered."""
        run_id: int = self.kwargs["run_id"]

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                raise JobError(f"Run {run_id} does not exist in DB.")
            try:
                run.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Internal database error",
                ) from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as error."""
        run_id: int = self.kwargs.get("run_id")
        if run_id is None:
            return

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            if not run:
                return
            try:
                run.set_status_as_error()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        run_id = self.kwargs.get("run_id")
        if not run_id:
            return "Model Training"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                run: Run = db.get(Run, run_id)
                if run and run.name:
                    return f"Train: {run.name}"
        except Exception:
            pass

        return f"Model Training ({run_id})"

    @inject
    def run(self) -> None:
        """Run a model job by delegating execution to the task executor."""
        import gc
        import os

        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        run_id: int = self.kwargs["run_id"]

        with session_factory() as db:
            run: Run = db.get(Run, run_id)
            run.huey_id = self.kwargs.get("huey_id", None)
            db.commit()

            try:
                context = self._build_context(
                    run=run,
                    db=db,
                    component_registry=component_registry,
                    config=config,
                )

                try:
                    run.set_status_as_started()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError(
                        "Connection with the database failed",
                    ) from e

                try:
                    executor = self._get_task_executor(context)
                    model = executor.execute(context)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Model training failed {e}",
                    ) from e

                try:
                    run_path = os.path.join(config["RUNS_PATH"], str(run.id))
                    model.save(run_path)
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Model saving failed",
                    ) from e

                try:
                    run.run_path = run_path
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    run.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Connection with the database failed",
                    ) from e

                try:
                    run.set_status_as_finished()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    raise JobError(
                        "Connection with the database failed",
                    ) from e
            except Exception as e:
                run.set_status_as_error()
                db.commit()
                raise e
            finally:
                gc.collect()

    def _build_context(self, run, db, component_registry, config) -> ModelJobContext:
        """Build the shared context consumed by task-specific executors."""
        from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

        model_session: ModelSession = db.get(ModelSession, run.model_session_id)
        if not model_session:
            raise JobError(
                f"Model session {run.model_session_id} does not exist in DB."
            )

        dataset: Dataset = db.get(Dataset, model_session.dataset_id)
        if not dataset:
            raise JobError(f"Dataset {model_session.dataset_id} does not exist in DB.")

        try:
            loaded_dataset: "DashAIDataset" = load_dataset(
                f"{dataset.file_path}/dataset"
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not load dataset from path {dataset.file_path}",
            ) from e

        try:
            task: BaseTask = component_registry[model_session.task_name]["class"]()
        except Exception as e:
            log.exception(e)
            raise JobError(
                (
                    f"Unable to find Task with name {model_session.task_name} "
                    "in registry"
                ),
            ) from e

        return ModelJobContext(
            run=run,
            model_session=model_session,
            dataset_record=dataset,
            dataset=loaded_dataset,
            task=task,
            component_registry=component_registry,
            db=db,
            config=config,
        )

    def _get_task_executor(self, context: ModelJobContext):
        """Resolve the executor compatible with the current task.

        Each task must have exactly one compatible executor. Executors are
        internal job components related to tasks through ``COMPATIBLE_COMPONENTS``;
        this keeps ``ModelJob`` independent from concrete task families such as
        supervised learning, clustering, or forecasting.
        """
        task_name = context.model_session.task_name
        component_registry = context.component_registry

        related_components = component_registry.get_related_components(task_name)
        executor_components = [
            component
            for component in related_components
            if component.get("type") == "TaskExecutor"
        ]

        if not executor_components:
            raise JobError(f"No task executor found for Task {task_name}.")

        if len(executor_components) > 1:
            raise JobError(f"Multiple task executors found for Task {task_name}.")

        return executor_components[0]["class"]()
