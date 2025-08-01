import logging
import os
from typing import Any, Dict, List

from kink import di

from DashAI.back.config import DefaultSettings
from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_column_names_from_indexes,
    prepare_for_experiment,
    select_columns,
    split_dataset,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.tasks.base_task import BaseTask

log = logging.getLogger(__name__)


class Train(BaseJob):
    """
    Train node for training machine learning models in pipelines.

    Parameters
    ----------
    input_columns : List[int]
        List of column indices to use as input features
    output_columns : List[int]
        List of column indices to use as output targets
    splits : Dict[str, float]
        Dictionary with train/validation/test split ratios
    task : str
        Name of the task to perform (e.g., "TabularClassificationTask")
    model : str
        Name of the model to train
    metrics : List[str]
        List of metric names to evaluate
    parameters : Dict[str, Any], optional
        Model-specific parameters for training
    """

    def __init__(
        self,
        input_columns: List[int],
        output_columns: List[int],
        splits: Dict[str, float],
        task: str,
        model: str,
        metrics: List[str],
        parameters: Dict[str, Any] = None,
    ) -> None:
        super().__init__(
            kwargs={
                "input_columns": input_columns,
                "output_columns": output_columns,
                "splits": splits,
                "task": task,
                "model": model,
                "metrics": metrics,
                "parameters": parameters,
            }
        )
        self.input_columns = input_columns
        self.output_columns = output_columns
        self.splits = splits
        self.task = task
        self.model = model
        self.metrics = metrics
        self.parameters = parameters

    def set_status_as_delivered(self) -> None:
        log.debug("Train executed successfully.")

    async def run(
        self,
        context: Dict[str, Any],
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> Dict[str, Any]:
        context["task_name"] = self.task
        context["model_name"] = self.model
        pipeline_id = context["pipeline_id"]
        dataset = context["dataset"]
        task: BaseTask = component_registry(di)[self.task]["class"]
        task_instance = task()

        input_columns_names = get_column_names_from_indexes(dataset, self.input_columns)
        context["input_columns"] = input_columns_names
        output_columns_names = get_column_names_from_indexes(
            dataset, self.output_columns
        )

        all_metrics = {
            component_dict["name"]: component_dict
            for component_dict in component_registry(di).get_components_by_types(
                select="Metric"
            )
        }
        metrics: List[BaseMetric] = []
        for metric_name in self.metrics:
            metric_class = all_metrics.get(metric_name)["class"]
            if metric_class:
                metrics.append(metric_class)
            else:
                log.warning(f"Metric '{metric_name}' not found in registry.")

        try:
            prepared_dataset = task_instance.prepare_for_task(
                dataset, output_columns_names
            )
            n_labels = None
            if self.task in [
                "TextClassificationTask",
                "TabularClassificationTask",
                "ImageClassificationTask",
            ]:
                all_classes = prepared_dataset.unique(output_columns_names[0])
                n_labels = len(all_classes)

            splits = self.splits
            prepared_dataset, splits = prepare_for_experiment(
                dataset=prepared_dataset,
                splits=splits,
                output_columns=output_columns_names,
            )

            x, y = select_columns(
                prepared_dataset, input_columns_names, output_columns_names
            )
            x = split_dataset(x)
            y = split_dataset(y)

        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not prepare dataset for task {self.task}",
            ) from e

        try:
            model_class = component_registry(di)[self.model]["class"]
            context["model_class"] = model_class
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to find Model with name {self.model} in registry.",
            ) from e

        try:
            parameters = self.parameters
            factory = ModelFactory(model_class, parameters, n_labels=n_labels)
            model: BaseModel = factory.model
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to instantiate model {self.model}",
            ) from e

        try:
            model.fit(x["train"], y["train"])
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Model training failed",
            ) from e

        try:
            model_metrics = factory.evaluate(x, y, metrics)
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Metrics calculation failed",
            ) from e

        try:
            settings = DefaultSettings()
            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            path = os.path.join(sqlite_local, "pipelines", "train")
            os.makedirs(path, exist_ok=True)
            model_path = os.path.join(path, str(pipeline_id))
            model.save(model_path)
            context["model_path"] = model_path
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Model saving failed",
            ) from e

        return {
            "train": {
                "info": self.model,
                "parameters": self.parameters,
                "metrics": model_metrics,
                "model_path": model_path,
                "input_columns": self.input_columns,
                "task": self.task,
            }
        }
