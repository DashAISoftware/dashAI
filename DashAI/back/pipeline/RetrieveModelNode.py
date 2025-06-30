import logging
from typing import Any, Dict, List
from kink import di

from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.dataloaders.classes.dashai_dataset import get_column_names_from_indexes

log = logging.getLogger(__name__)

class RetrieveModel(BaseJob):
    def __init__(self, model: str, model_path: str, input_columns: List[int], task: str) -> None:
        super().__init__(kwargs={"model": model, "model_path": model_path})
        self.model = model
        self.model_path = model_path
        self.input_columns = input_columns
        self.task = task

    def set_status_as_delivered(self) -> None:
        log.info("RetrieveModel executed successfully.")

    def run(
        self,
        context: Dict[str, Any],
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> Dict[str, Any]:
        try:
            context["model_name"] = self.model
            context["model_path"] = self.model_path
            context["task_name"] = self.task

            dataset = context["dataset"]
            input_columns_names = get_column_names_from_indexes(dataset, self.input_columns)
            context["input_columns"] = input_columns_names

            model_class = component_registry(di)[self.model]["class"]
            context["model_class"] = model_class

            log.info(f"Model '{self.model}' retrieved from path '{self.model_path}'.")

            return {
                "retrieve": {
                    "model_name": self.model,
                    "model_path": self.model_path,
                }
            }

        except KeyError as e:
            log.exception(e)
            raise JobError(f"Model '{self.model}' not found in registry.") from e
        except Exception as e:
            log.exception(e)
            raise JobError("Error retrieving model.") from e
