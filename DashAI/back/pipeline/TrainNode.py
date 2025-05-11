import logging
import os
from typing import Any, Dict, List

from DashAI.back.config import DefaultSettings
from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_column_names_from_indexes,
    prepare_for_experiment,
    select_columns,
    split_dataset,
)
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.metrics.base_metric import BaseMetric
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.pipeline.registry import component_registry
from DashAI.back.tasks.base_task import BaseTask

log = logging.getLogger(__name__)

class Train(BaseJob):
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
        log.info("Train executed successfully.")

    def run(self, context: Dict[str, Any]) -> Any:
        context["task_name"] = self.task
        context["model_name"] = self.model
        #context["input_columns"] = self.input_columns
        pipeline_id = context["pipeline_id"]
        dataset = context["dataset"]
        task: BaseTask = component_registry[self.task][0]["class"]()

        input_columns_names = get_column_names_from_indexes(dataset, self.input_columns)
        context["input_columns"] = input_columns_names
        output_columns_names = get_column_names_from_indexes(dataset, self.output_columns)
        
        all_metrics = {
            component["class"].__name__: component["class"]
            for component in component_registry["Metric"]
        }
        metrics: List[BaseMetric] = []
        for metric_name in self.metrics:
            metric_class = all_metrics.get(metric_name)
            if metric_class:
                metrics.append(metric_class)
            else:
                log.warning(f"Métrica '{metric_name}' no encontrada en el registry.")
        
        # split
        try:
            prepared_dataset = task.prepare_for_task(
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

            #splits = json.loads(self.splits)

            prepared_dataset = prepare_for_experiment(
                dataset=prepared_dataset,
                splits=self.splits,
                output_columns=output_columns_names,
            )

            x, y = select_columns(prepared_dataset,
                                  input_columns_names,
                                  output_columns_names)
            x = split_dataset(x)
            y = split_dataset(y)
            
        except Exception as e:
            raise JobError(f"Error en preparación de datos: {e}")
        
        try:
                model_class = component_registry[self.model][0]["class"]
                context["model_class"] = model_class
        except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Unable to find Model with name {self.model} in registry.",
                ) from e

        try:
            parameters = self.parameters
            factory = ModelFactory(
                model_class,
                parameters,
                n_labels=n_labels
            )
            model: BaseModel = factory.model
        except Exception as e:
            raise JobError(f"Error durante el entrenamiento: {e}")
        
        try:
            model.fit(x["train"], y["train"])
        except Exception as e:
            log.exception(e)
            raise JobError(f"Error during model training: {e}")
        
        # metrics
        try:
            model_metrics = factory.evaluate(x, y, metrics)
        except Exception as e:
                log.exception(e)
                raise JobError(
                    "Metrics calculation failed",
                ) from e
        
        # save model
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
            raise JobError(f"Error saving model: {e}")

        
        return {
            "train": 
                {
                    "info": self.model,
                    "parameters": self.parameters,
                    "metrics":model_metrics
                }
        }


from DashAI.back.tasks import TabularClassificationTask, TextClassificationTask, TranslationTask, ImageClassificationTask
from DashAI.back.models import (
    SVC,
    DecisionTreeClassifier,
    DummyClassifier,
    HistGradientBoostingClassifier,
    KNeighborsClassifier,
    LogisticRegression,
    RandomForestClassifier
)
from DashAI.back.metrics import (
    Accuracy,
    F1,
    Precision,
    Recall,
    MAE,
    RMSE,
    Bleu,
    Ter,
)

component_registry.register("TabularClassificationTask", TabularClassificationTask)
component_registry.register("TextClassificationTask", TextClassificationTask)
component_registry.register("TranslationTask", TranslationTask)
component_registry.register("ImageClassificationTask", ImageClassificationTask)

component_registry.register("SVC", SVC)
component_registry.register("DecisionTreeClassifier", DecisionTreeClassifier)
component_registry.register("DummyClassifier", DummyClassifier)
component_registry.register("HistGradientBoostingClassifier", HistGradientBoostingClassifier)
component_registry.register("KNeighborsClassifier", KNeighborsClassifier)
component_registry.register("LogisticRegression", LogisticRegression)
component_registry.register("RandomForestClassifier", RandomForestClassifier)

component_registry.register("Metric", Accuracy)
component_registry.register("Metric", F1)
component_registry.register("Metric", Precision)
component_registry.register("Metric", Recall)
component_registry.register("Metric", MAE)
component_registry.register("Metric", RMSE)
component_registry.register("Metric", Bleu)
component_registry.register("Metric", Ter)

