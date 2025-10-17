import json
import logging
import os
from pathlib import Path
from typing import Any, List

import numpy as np
from fastapi import status
from fastapi.exceptions import HTTPException
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, load_dataset
from DashAI.back.dependencies.database.models import Dataset, Experiment, Run
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_model import BaseModel
from DashAI.back.tasks import BaseTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class PredictJob(BaseJob):
    """PredictJob class to run the prediction."""

    @inject
    def set_status_as_delivered(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered."""
        log.debug("Prediction job marked as delivered")

    @inject
    def set_status_as_error(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the prediction job as error."""
        log.error(f"Prediction job failed: {self.kwargs}")

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        run_id = self.kwargs.get("run_id")
        dataset_id = self.kwargs.get("id")
        json_filename = self.kwargs.get("json_filename", "")

        if json_filename:
            return f"Predict: {json_filename}"

        if run_id and dataset_id:
            from kink import di

            session_factory = di["session_factory"]

            try:
                with session_factory() as db:
                    run = db.get(Run, run_id)
                    dataset = db.get(Dataset, dataset_id)
                    if run and dataset:
                        return f"Predict: {run.name} on {dataset.name}"
            except Exception:
                pass

        return f"Prediction (Run:{run_id}, Dataset:{dataset_id})"

    @inject
    def run(
        self,
    ) -> List[Any]:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        run_id: int = self.kwargs["run_id"]
        id: int = self.kwargs["id"]
        json_filename: str = self.kwargs["json_filename"]
        with session_factory() as db:
            try:
                run: Run = db.get(Run, run_id)
                if not run:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
                    )

                exp: Experiment = db.get(Experiment, run.experiment_id)
                if not exp:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Experiment not found",
                    )
                dataset: Dataset = db.get(Dataset, id)
                if not dataset:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Dataset not found",
                    )
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal database error",
                ) from e

            try:
                loaded_dataset: DashAIDataset = load_dataset(
                    str(Path(f"{dataset.file_path}/dataset/"))
                )
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Can not load dataset from path {dataset.file_path}/dataset/"
                ) from e
            try:
                model = component_registry[run.model_name]["class"]
                trained_model: BaseModel = model.load(run.run_path)
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Model {run.model_name} not found in the registry"
                ) from e

            try:
                prepared_dataset = loaded_dataset.select_columns(exp.input_columns)
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
                train_dataset: DashAIDataset = load_dataset(
                    str(Path(f"{exp.dataset.file_path}/dataset/"))
                )
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Can not load dataset from path {exp.dataset.file_path}/dataset/"
                ) from e
            try:
                task: BaseTask = component_registry[exp.task_name]["class"]()
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Task {exp.task_name} not found in the registry",
                ) from e

            try:
                prepared_dataset = loaded_dataset.select_columns(exp.input_columns)
                y_pred_proba = np.array(trained_model.predict(prepared_dataset))

                y_pred = task.process_predictions(
                    train_dataset, y_pred_proba, exp.output_columns[0]
                )
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Processing predictions failed",
                ) from e
            try:
                path = str(Path(f"{config['DATASETS_PATH']}/predictions/"))
                os.makedirs(path, exist_ok=True)
                existing_files = os.listdir(path)
                existing_ids = []
                for f in existing_files:
                    if f.endswith(".json"):
                        file_path = os.path.join(path, f)
                        with open(file_path, "r") as json_file:
                            data = json.load(json_file)
                            existing_ids.append(data["metadata"]["id"])
                next_id = max(existing_ids, default=0) + 1

                json_name = f"{json_filename}.json"

                json_data = {
                    "metadata": {
                        "id": next_id,
                        "pred_name": json_name,
                        "run_name": run.model_name,
                        "model_name": run.name,
                        "dataset_name": dataset.name,
                        "task_name": exp.task_name,
                    },
                    "prediction": y_pred.tolist(),
                }

                with open(os.path.join(path, json_name), "w") as json_file:
                    json.dump(json_data, json_file, indent=4)
            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Can not save prediction to json file",
                ) from e
