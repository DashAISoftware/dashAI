import os
from DashAI.back.dependencies.database.models import Dataset
from abc import ABC, abstractmethod
from typing import Any, Dict
from DashAI.back.tasks.base_task import BaseTask

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
    TYPE = "DataSelector"
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
        options = self.data.get("options")
        dataselector = self.data.get("dataselector")

        if not dataselector:
            return {"status": "error", "message": "No DataSelector node connected"}

        if dataselector.get("status") != "ok":
            return {"status": "error", "message": "The connected DataSelector node is not valid"}

        if not options or not isinstance(options, list) or len(options) == 0:
            return {"status": "error", "message": "No exploration options selected"}

        return {"status": "ok"}


class TrainValidator(BaseNodeValidator):
    def validate(self) -> Dict[str, str]:
        config = self.data.get("config")
        dataselector = self.data.get("dataselector")

        if not dataselector:
            return {"status": "error", "message": "No DataSelector node connected"}

        if dataselector.get("status") != "ok":
            return {"status": "error", "message": "The connected DataSelector node is not valid"}
        
        input_cols = config.get("input_columns")
        output_cols = config.get("output_columns")
        task = config.get("task")
        splits = config.get("splits", {})
        metrics = config.get("metrics")
        model = config.get("model")

        if not input_cols or not output_cols:
            return {"status": "error", "message": "Input and output columns are required"}
        
        if task is None:
            return {"status": "error", "message": "Task is required"}
        
        if model is None:
            return {"status": "error", "message": "Model is required"}
        
        if not metrics:
            return {"status": "error", "message": "At least one metric must be selected"}
        
        train, val, test = splits.get("train", 0), splits.get("validation", 0), splits.get("test", 0)
        if round(train + val + test, 5) != 1.0:
            return {"status": "error", "message": "Train, validation, and test splits must sum to 1"}

        return {"status": "ok"}


class PredictionValidator(BaseNodeValidator):
    def validate(self) -> Dict[str, str]:
        dataselector = self.data.get("dataselector")
        train = self.data.get("train")

        if not train:
            return {"status": "error", "message": "No Train node connected"}
        elif not dataselector:
            return {"status": "error", "message": "No DataSelector node connected"}

        if train.get("status") != "ok":
            return {"status": "error", "message": "The connected Train node is not valid"}
        elif dataselector.get("status") != "ok":
            return {"status": "error", "message": "The connected DataSelector node is not valid"}
        
        return {"status": "ok"}


VALIDATOR_MAP = {
    "DataSelector": DataSelectorValidator,
    "DataExploration": DataExplorationValidator,
    "Train": TrainValidator,
    "Prediction": PredictionValidator,
}
