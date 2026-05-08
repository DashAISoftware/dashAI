import logging
from typing import Any, Dict

from fastapi import HTTPException
from kink import di, inject

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

    def set_status_as_error(self) -> None:
        log.error("Prediction encountered an error.")

    def get_job_name(self) -> str:
        return "Prediction"

    @inject
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        import json
        import os

        import numpy as np

        loaded_dataset = context["dataset"]
        model = context["model_class"]
        config = di["config"]

        sqlite_local = config["LOCAL_PATH"]
        pipeline_id = context.get("pipeline_id")
        model_node_id = context.get("model_node_id")

        model_path = context["model_path"]
        if pipeline_id is not None and model_node_id:
            node_model_path = os.path.join(
                sqlite_local,
                "pipelines",
                "train",
                str(pipeline_id),
                str(model_node_id),
                "model",
            )
            if os.path.exists(node_model_path):
                model_path = node_model_path

        try:
            trained_model: BaseModel = model.load(model_path)
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Failed to load trained model for Prediction. "
                f"model_name={context.get('model_name')}, "
                f"model_path={model_path}, "
                f"model_node_id={model_node_id}, "
                f"pipeline_id={pipeline_id}"
            ) from e

        try:
            prepared_dataset = loaded_dataset.select_columns(context["input_columns"])
            y_pred_proba = np.array(trained_model.predict(prepared_dataset))

            if isinstance(y_pred_proba[0], str):
                y_pred = y_pred_proba
            elif y_pred_proba.ndim == 2:
                y_pred = np.argmax(y_pred_proba, axis=1)
            else:
                y_pred = y_pred_proba

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
