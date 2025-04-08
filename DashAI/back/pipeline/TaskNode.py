import logging
import os
import pathlib
import pickle
from typing import Any, Dict

import numpy as np
from sklearn.metrics import accuracy_score


from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, load_dataset, select_columns
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models import BaseModel
from DashAI.back.tasks import BaseTask
from DashAI.back.pipeline.registry import component_registry

log = logging.getLogger(__name__)

class TaskSelector(BaseJob):
    def __init__(self, task: str, models: list) -> None:
        super().__init__(kwargs={"task": task, "models": models})

    def set_status_as_delivered(self) -> None:
        log.info("TaskSelector executed successfully.")

    def run(self, context: Dict[str, Any]) -> Any:
        task_name = self.kwargs["task"]
        models = self.kwargs["models"]

        dataset = context.get("dataset")
        if not dataset:
            raise JobError("No dataset found in context.")
        
        dataset_dir = ""
        output_columns = ["Species"]
        input_columns = ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"]

        try:
                loaded_dataset: DashAIDataset = load_dataset(str(dataset_dir))

        except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Can not load dataset from path {dataset_dir}",
                ) from e

        try:
            task: BaseTask = component_registry[task_name]["class"]()
        except Exception as e:
            log.exception(e)
            raise JobError(f"Unable to instantiate Task {task_name}") from e
        
        try:
            prepared_dataset = task.prepare_for_task(loaded_dataset, output_columns)
            x, y = select_columns(prepared_dataset, input_columns, output_columns)
            x_train, x_test, x_validation = x['train'], x['test'], x['validation']
            y_train, y_test, y_validation = y['train'], y['test'], y['validation']
        except Exception as e:
            log.exception(e)
            raise JobError(f"Cannot prepare dataset for Task {task_name}") from e

        save_dir = "trained_models"
        os.makedirs(save_dir, exist_ok=True)
        model_paths = {}

        for model_name in models:
            if model_name not in component_registry.registry:
                raise JobError(f"Model {model_name} not found in component registry.")

            try:
                model_class = component_registry[model_name]["class"]
                model: BaseModel = model_class()
                model.fit(x_train, y_train)

                model_path = os.path.join(save_dir, f"{model_name}_model.pickle")
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
                
                model_paths[model_name] = model_path

                log.info(f"Model {model_name} trained successfully. Saved at {model_path}")

            except Exception as e:
                log.exception(e)
                raise JobError(f"Error training model {model_name}") from e

        return {"task": model_paths}


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
