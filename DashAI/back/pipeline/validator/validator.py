import os
from DashAI.back.dependencies.database.models import Dataset

class BaseNodeValidator:
    def __init__(self, data, db):
        self.data = data
        self.db = db

    def validate(self):
        raise NotImplementedError("Subclasses must implement this method")


class DataLoaderValidator(BaseNodeValidator):
    def validate(self):
            dataset_name = self.data.get("datasetName")
            dataset_path = self.data.get("datasetPath")

            if not dataset_name or not dataset_path:
                return {"status": "error", "message": "No dataset selected"}

            if not os.path.exists(dataset_path):
                return {"status": "error", "message": "Dataset not found"}

            return {"status": "ok"}


class DataExplorationValidator(BaseNodeValidator):
    def validate(self):
        options = self.data.get("options")
        dataloader = self.data.get("dataloader")

        if not dataloader:
            return {"status": "error", "message": "No previous node connected"}

        if dataloader.get("status") != "ok":
            return {"status": "error", "message": "The connected DataLoader node is not valid"}

        if not options or not isinstance(options, list) or len(options) == 0:
            return {"status": "error", "message": "No exploration options selected"}

        return {"status": "ok"}



class TaskValidator(BaseNodeValidator):
    def validate(self):
        return {"status": "ok"}


class MetricsValidator(BaseNodeValidator):
    def validate(self):
        return {"status": "ok"}


VALIDATOR_MAP = {
    "DataLoader": DataLoaderValidator,
    "DataExploration": DataExplorationValidator,
    "Task": TaskValidator,
    "Metrics": MetricsValidator,
}
