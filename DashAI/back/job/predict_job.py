import logging
import uuid
from pathlib import Path
from typing import Any, List

import numpy as np
from fastapi import status
from fastapi.exceptions import HTTPException
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    load_dataset,
    save_dataset,
    to_dashai_dataset,
)
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Prediction
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
        prediction_id = self.kwargs.get("prediction_id")

        try:
            with session_factory() as db:
                prediction: Prediction = db.get(Prediction, prediction_id)
                if prediction:
                    prediction.set_status_as_delivered()
                    db.commit()
                else:
                    log.error(f"Prediction with id {prediction_id} not found.")
        except exc.SQLAlchemyError as e:
            log.exception(f"Database error while setting prediction status: {e}")

    @inject
    def set_status_as_error(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the prediction job as error."""
        prediction_id = self.kwargs.get("prediction_id")

        try:
            with session_factory() as db:
                prediction: Prediction = db.get(Prediction, prediction_id)
                if prediction:
                    prediction.set_status_as_error()
                    db.commit()
                else:
                    log.error(f"Prediction with id {prediction_id} not found.")
        except exc.SQLAlchemyError as e:
            log.exception(f"Database error while setting prediction status: {e}")

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        prediction_id = self.kwargs.get("prediction_id")
        dataset_id = self.kwargs.get("dataset_id")

        if prediction_id:
            from kink import di

            session_factory = di["session_factory"]

            try:
                with session_factory() as db:
                    prediction = db.get(Prediction, prediction_id)
                    dataset = db.get(Dataset, dataset_id)
                    if prediction and dataset:
                        return f"Predict: {prediction.run.name} on {dataset.name}"
            except Exception:
                pass

        return f"Prediction (Prediction:{prediction_id}, Dataset:{dataset_id})"

    @inject
    def run(
        self,
    ) -> List[Any]:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        prediction_id: int = self.kwargs["prediction_id"]
        manual_input_data: List[dict] = self.kwargs.get("manual_input_data", [])

        with session_factory() as db:
            try:
                # Retrieve Prediction
                prediction: Prediction = db.get(Prediction, prediction_id)
                if not prediction:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Prediction not found for id {prediction_id}",
                    )

                # Set huey_id and update status to STARTED
                prediction.huey_id = self.kwargs.get("huey_id", None)
                prediction.set_status_as_started()
                db.commit()

                dataset_id = prediction.dataset_id

                # Validate input data
                if not manual_input_data and not dataset_id:
                    prediction.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Either dataset_id or manual_input_data must be provided."
                    )

                # Retrieve Model Session
                model_session: ModelSession = db.get(
                    ModelSession, prediction.run.model_session_id
                )
                if not model_session:
                    prediction.set_status_as_error()
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Model session not found",
                    )

                # Retrieve Dataset if dataset_id is provided
                dataset: Dataset = None
                dataset_trained: Dataset = db.get(Dataset, model_session.dataset_id)
                if not dataset_trained:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Training dataset not found",
                    )

                if dataset_id:
                    dataset: Dataset = db.get(Dataset, dataset_id)

            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal database error",
                ) from e

            # Retrieve Task
            try:
                task: BaseTask = component_registry[model_session.task_name]["class"]()
            except Exception as e:
                prediction.set_status_as_error()
                db.commit()
                log.exception(e)
                raise JobError(
                    f"Task {model_session.task_name} not found in the registry",
                ) from e

            # Load Model
            try:
                model = component_registry[prediction.run.model_name]["class"]
                trained_model: BaseModel = model.load(prediction.run.run_path)
            except Exception as e:
                prediction.set_status_as_error()
                db.commit()
                log.exception(e)
                raise JobError(
                    f"Model {prediction.run.model_name} not found in the registry"
                ) from e

            # Load Dataset and make Predictions
            try:
                # Load training dataset for type info and label processing
                train_dataset: DashAIDataset = load_dataset(
                    str(Path(f"{dataset_trained.file_path}/dataset/"))
                )
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Cannot load training dataset from "
                    f"{dataset_trained.file_path}/dataset/"
                ) from e

            try:
                # Load or create prediction dataset
                if dataset_id:
                    loaded_dataset: DashAIDataset = load_dataset(
                        str(Path(f"{dataset.file_path}/dataset/"))
                    )
                else:
                    dataset_trained_path = str(
                        Path(f"{dataset_trained.file_path}/dataset/")
                    )
                    loaded_dataset = task.process_manual_input(
                        manual_input_data, dataset_trained_path
                    )

                # Select input columns and make prediction
                prepared_dataset = loaded_dataset.select_columns(
                    model_session.input_columns
                )
                y_pred_proba = np.array(trained_model.predict(prepared_dataset))

                # Process predictions (convert to labels for classification)
                y_pred = task.process_predictions(
                    train_dataset, y_pred_proba, model_session.output_columns[0]
                )

            except ValueError as ve:
                prediction.set_status_as_error()
                db.commit()
                log.error(f"Validation Error: {ve}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input data: {str(ve)}",
                ) from ve
            except TypeError as te:
                log.error(f"Type Error: {te}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Type validation failed: {str(te)}",
                ) from te
            except Exception as e:
                prediction.set_status_as_error()
                db.commit()
                log.error(e)
                raise JobError(
                    "Model prediction failed",
                ) from e

            # Save Predictions to Arrow file
            try:
                # Create unique folder for predictions
                path = str(Path(f"{config['DATASETS_PATH']}/predictions/"))
                folder_name = str(uuid.uuid4())
                full_path = Path(path) / folder_name
                full_path.mkdir(parents=True, exist_ok=True)

                # Add predictions to loaded dataset
                dataset_with_prediction = to_dashai_dataset(
                    prepared_dataset.add_column(model_session.output_columns[0], y_pred)
                )

                # Filter schema from trained dataset
                trained_schema = train_dataset.types
                filtered_schema = {
                    key: value.to_string()
                    for key, value in trained_schema.items()
                    if key in model_session.input_columns + model_session.output_columns
                }

                # Store num of rows, columns, and column names
                dataset_with_prediction.compute_base_metadata()

                # Save dataset with predictions
                save_dataset(
                    dataset_with_prediction,
                    str(full_path / "dataset"),
                    filtered_schema,
                )

                # Update Prediction record
                prediction.results_path = str(full_path)
                prediction.set_status_as_finished()
                db.commit()
            except Exception as e:
                prediction.set_status_as_error()
                db.commit()
                log.exception(e)
                raise JobError(
                    "Can not save prediction to json file",
                ) from e
