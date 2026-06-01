"""Executor for clustering tasks."""

import logging

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import select_columns
from DashAI.back.dependencies.database.models import Metric
from DashAI.back.job.base_job import JobError
from DashAI.back.job.model_job_context import ModelJobContext
from DashAI.back.job.task_executors.base_task_executor import BaseTaskExecutor
from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ClusteringTaskExecutor(BaseTaskExecutor):
    """Execute clustering runs without assuming target columns or splits."""

    COMPATIBLE_COMPONENTS = ["ClusteringTask"]

    def execute(self, context: ModelJobContext) -> BaseModel:
        component_registry = context.component_registry
        db = context.db
        run = context.run
        model_session = context.model_session
        task = context.task

        try:
            metrics: list[type[BaseMetric]] = [
                component_registry[m]["class"]
                for m in (model_session.test_metrics or [])
            ]
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Unable to find metrics associated with "
                f"Task {model_session.task_name} in registry",
            ) from e

        try:
            prepared_dataset = task.prepare_for_task(
                dataset=context.dataset,
                input_columns=model_session.input_columns,
                output_columns=[],
            )
            x, _ = select_columns(
                prepared_dataset,
                model_session.input_columns,
                [],
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not prepare dataset for Task {model_session.task_name}",
            ) from e

        try:
            run_model_class = component_registry[run.model_name]["class"]
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to find Model with name {run.model_name} in registry.",
            ) from e

        try:
            factory = ModelFactory(
                run_model_class,
                run.parameters,
                run.id,
                n_labels=None,
            )
            model: BaseModel = factory.model
            model.train(x)
            labels = model.get_cluster_labels(x)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Clustering model training failed {e}",
            ) from e

        try:
            results = {}
            for metric in metrics:
                score = metric.score(x, labels)
                if score is not None:
                    results[metric.__name__] = score

            self._save_full_metrics(run.id, results, db)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Clustering metric calculation failed {e}",
            ) from e

        return model

    def _save_full_metrics(self, run_id: int, results: dict[str, float], db) -> None:
        """Persist clustering metrics evaluated over the full dataset."""

        for name, value in results.items():
            existing_metric = (
                db.query(Metric)
                .filter_by(
                    run_id=run_id,
                    split=SplitEnum.FULL,
                    level=LevelEnum.LAST,
                    name=name,
                )
                .first()
            )

            if existing_metric:
                existing_metric.value = value
                existing_metric.step = 0
            else:
                db.add(
                    Metric(
                        run_id=run_id,
                        split=SplitEnum.FULL,
                        level=LevelEnum.LAST,
                        name=name,
                        value=value,
                        step=0,
                    )
                )

        db.commit()
