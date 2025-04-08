import json
import logging
import pathlib
from typing import Any, Dict

import pandas as pd
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)

class DataLoader(BaseJob):
    def __init__(self, filePath: str) -> None:
        super().__init__(kwargs={"filePath": filePath})

    def set_status_as_delivered(self) -> None:
        log.info("DataLoader executed successfully.")

    def run(self, context: Dict[str, Any]) -> Any:
        #dataset_dir = pathlib.Path(self.kwargs['filePath'])
        dataset_dir = ""

        dataset_dict_path = dataset_dir / "dataset_dict.json"
        if not dataset_dict_path.exists():
            raise JobError(f"No se encontró el dataset_dict.json en {dataset_dict_path}")

        try:
            with open(dataset_dict_path, 'r') as f:
                dataset_dict = json.load(f)

            train_data_path = dataset_dir / "train" / "dataset_info.json"
            test_data_path = dataset_dir / "test" / "dataset_info.json"
            validation_data_path = dataset_dir / "validation" / "dataset_info.json"

            with open(train_data_path, 'r') as f:
                train_data = json.load(f)

            with open(test_data_path, 'r') as f:
                test_data = json.load(f)

            with open(validation_data_path, 'r') as f:
                validation_data = json.load(f)

        except Exception as e:
            log.error(f"Error cargando el dataset desde {dataset_dir}: {e}")
            raise JobError(f"Error cargando el dataset: {e}")

        log.info(f"Dataset cargado correctamente desde: {dataset_dir}")

        return {
            "dataset": {
                "metadata": dataset_dict,
                "train": train_data,
                "test": test_data,
                "validation": validation_data
            }
        }