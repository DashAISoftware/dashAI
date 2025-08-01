import json
import logging
import os
from typing import Any, Dict

import numpy as np
from fastapi import HTTPException

from DashAI.back.config import DefaultSettings
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_model import BaseModel

log = logging.getLogger(__name__)


class Prediction(BaseJob):
    """
    Prediction node for making predictions using trained models in pipelines.

    Predictions are saved to JSON files.

    Parameters
    ----------
    kwargs : Dict[str, Any]
        A dictionary containing the parameters for the node
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(kwargs=kwargs)

    def set_status_as_delivered(self) -> None:
        log.debug("Prediction executed successfully.")

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        loaded_dataset = context["dataset"]
        model = context["model_class"]
        model_path = context["model_path"]
        trained_model: BaseModel = model.load(model_path)

        try:
            prepared_dataset = loaded_dataset.select_columns(context["input_columns"])
            y_pred_proba = np.array(trained_model.predict(prepared_dataset))
            if isinstance(y_pred_proba[0], str):
                y_pred = y_pred_proba
            else:
                y_pred = np.argmax(y_pred_proba, axis=1)

        except ValueError as ve:
            log.error(f"Validation Error: {ve}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid columns selected: {str(ve)}",
            ) from ve
        except Exception as e:
            log.error(e)
            raise JobError(
                "Model prediction failed",
            ) from e

        try:
            settings = DefaultSettings()
            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            path = os.path.join(sqlite_local, "pipelines", "predictions")
            os.makedirs(path, exist_ok=True)
            existing_ids = []
            for f in os.listdir(path):
                if f.endswith(".json"):
                    with open(os.path.join(path, f), "r") as json_file:
                        try:
                            data = json.load(json_file)
                            existing_ids.append(data["metadata"]["id"])
                        except (json.JSONDecodeError, KeyError):
                            continue

            next_id = max(existing_ids, default=0) + 1
            json_name = f"prediction_{next_id}.json"

            json_data = {
                "metadata": {
                    "id": next_id,
                    "model_name": context["model_name"],
                    "dataset_name": context["dataset_name"],
                    "task_name": context["task_name"],
                },
                "prediction": y_pred.tolist(),
            }

            with open(os.path.join(path, json_name), "w") as json_file:
                json.dump(json_data, json_file, indent=4)

            return {"prediction": json_name}
        except Exception as e:
            log.exception(e)
            raise JobError("Can not save prediction to json file") from e
