import logging
from typing import Any, Dict

import pandas as pd
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)

class DataExploration(BaseJob): 
    def __init__(self, options: list = None) -> None:
        super().__init__(kwargs={"options": options or []})

    def set_status_as_delivered(self) -> None:
        log.info("DataExploration executed successfully.")

    def run(self, context: Dict[str, Any]) -> Any:
        try:
            dataset = context.get("dataset")
            if dataset is None:
                raise JobError("No se encontró el dataset en el contexto.")

            train_data = dataset.get("train")
            if train_data is None:
                raise JobError("No se encontró la partición de entrenamiento en el dataset.")

            df = pd.DataFrame(train_data["features"])
            log.info(f"Explorando dataset con opciones: {self.kwargs['options']}")

            exploration_results = {}

            if "shape" in self.kwargs["options"]:
                exploration_results["shape"] = df.shape

            if "columns" in self.kwargs["options"]:
                exploration_results["columns"] = list(df.columns)

            if "dtypes" in self.kwargs["options"]:
                exploration_results["dtypes"] = df.dtypes.astype(str).to_dict()

            if "null_values" in self.kwargs["options"]:
                exploration_results["null_values"] = df.isnull().sum().to_dict()

            if "unique_values" in self.kwargs["options"]:
                exploration_results["unique_values"] = {
                    col: df[col].nunique() for col in df.columns
                }

            log.info("Exploración de datos completada exitosamente.")
            print("resutls:::::", exploration_results)
            return {"exploration": exploration_results}

        except Exception as e:
            log.error(f"Error durante la exploración de datos: {e}")
            raise JobError(f"Error durante la exploración de datos: {e}")