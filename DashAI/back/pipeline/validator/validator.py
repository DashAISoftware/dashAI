import os
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseNodeValidator(ABC):
    TYPE: str = "BaseNode"

    def __init__(self, data: Dict[str, Any], db: Any):
        self.data = data
        self.db = db

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return {
            "type": cls.TYPE,
            "description": "Base node validator",
        }

    @abstractmethod
    def validate(self) -> Dict[str, str]:
        raise NotImplementedError("Subclasses must implement this method")


class DataSelectorValidator(BaseNodeValidator):
    def validate(self) -> Dict[str, str]:
        dataset_name = self.data.get("datasetName")
        dataset_path = self.data.get("datasetPath")

        if not dataset_name or not dataset_path:
            return {"status": "error", "message": "No dataset selected"}

        if not os.path.exists(dataset_path):
            return {"status": "error", "message": "Dataset not found"}

        return {"status": "ok"}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return {
            "type": cls.TYPE,
            "required_fields": ["datasetName", "datasetPath"],
        }


class DataExplorationValidator(BaseNodeValidator):
    def validate(self) -> Dict[str, str]:
        options = self.data.get("explorations")

        if not options or not isinstance(options, list) or len(options) == 0:
            return {"status": "error", "message": "No explorations selected"}

        return {"status": "ok"}


class TrainValidator(BaseNodeValidator):
    def validate(self) -> Dict[str, str]:
        input_cols = self.data.get("input_columns")
        output_cols = self.data.get("output_columns")
        task = self.data.get("task")
        splits = self.data.get("splits", {})
        metrics = self.data.get("metrics")
        model = self.data.get("model")

        if not input_cols or not output_cols:
            return {
                "status": "error",
                "message": "Input and output columns are required",
            }

        if task is None:
            return {"status": "error", "message": "Task is required"}

        if model is None:
            return {"status": "error", "message": "Model is required"}

        if not metrics:
            return {
                "status": "error",
                "message": "At least one metric must be selected",
            }

        train, val, test = (
            splits.get("train", 0),
            splits.get("validation", 0),
            splits.get("test", 0),
        )
        if round(train + val + test, 5) != 1.0:
            return {
                "status": "error",
                "message": "Train, validation, and test splits must sum to 1",
            }

        return {"status": "ok"}


class RetrieveModelValidator(BaseNodeValidator):
    def validate(self) -> Dict[str, str]:
        model = self.data.get("model")
        model_path = self.data.get("model_path")
        input_columns = self.data.get("input_columns")
        task = self.data.get("task")

        if not model or not model_path or not input_columns or not task:
            return {
                "status": "error",
                "message": "Error in trained model selected",
            }

        return {"status": "ok"}


VALIDATOR_MAP = {
    "DataSelector": DataSelectorValidator,
    "DataExploration": DataExplorationValidator,
    "Train": TrainValidator,
    "RetrieveModel": RetrieveModelValidator,
}
