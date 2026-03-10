import logging
import math
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
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


def sanitize_for_json(value):
    """Convert NaN/Inf float values to None for JSON serialization.

    Parameters
    ----------
    value : Any
        Value to sanitize (can be list, dict, float, etc.)

    Returns
    -------
    Any
        Sanitized value with NaN/Inf replaced by None
    """
    if isinstance(value, dict):
        return {k: sanitize_for_json(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    elif isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    elif isinstance(value, np.floating):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    return value


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

    def _validate_forecasting_dataset(
        self,
        dataset: DashAIDataset,
        model_session,
        trained_model: Any,
        train_dataset: DashAIDataset = None,
    ) -> str:
        """Validate dataset for forecasting prediction.

        Parameters
        ----------
        dataset : DashAIDataset
            The prediction dataset to validate.
        model_session : ModelSession
            The model session associated with the prediction.
        trained_model : Any
            The loaded trained model instance.
        train_dataset : DashAIDataset, optional
            The training dataset (used for backcasting validation).

        Returns
        -------
        str
            The name of the detected timestamp column

        Raises
        ------
        HTTPException
            If dataset is invalid for forecasting
        """
        pred_df = dataset.to_pandas()

        # Auto-detect timestamp column (try 'ds' first for compatibility)
        timestamp_col = None
        if "ds" in pred_df.columns:
            timestamp_col = "ds"
        else:
            for col in pred_df.columns:
                try:
                    pd.to_datetime(pred_df[col])
                    timestamp_col = col
                    log.info(f"Auto-detected timestamp column: '{col}'")
                    break
                except Exception:
                    continue

        if timestamp_col is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Forecasting prediction requires a timestamp column "
                f"(datetime). Available columns: {list(pred_df.columns)}",
            )

        # Parse and validate timestamps
        try:
            ds_series = pd.to_datetime(pred_df[timestamp_col])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(f"Cannot parse '{timestamp_col}' column as datetime: {str(e)}"),
            ) from e

        # Check for duplicates
        if ds_series.duplicated().any():
            duplicates = ds_series[ds_series.duplicated()].unique()[:5].tolist()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Duplicate timestamps found in '{timestamp_col}' column: "
                    f"{duplicates}"
                ),
            )

        # Check monotonicity (strictly increasing)
        if not ds_series.is_monotonic_increasing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Timestamps in '{timestamp_col}' column must be strictly "
                    "increasing (sorted)."
                ),
            )

        # Get training metadata from model
        train_frequency = getattr(trained_model, "frequency", None)
        train_last_ds = getattr(trained_model, "last_ds", None)
        exog_cols = getattr(trained_model, "exog_cols", [])

        log.info(
            f"Training metadata - frequency: {train_frequency}, "
            f"last_ds: {train_last_ds}, exog_cols: {exog_cols}"
        )

        # Validate frequency consistency (if available)
        if train_frequency and len(ds_series) >= 2:
            try:
                inferred_freq = pd.infer_freq(ds_series)
                if inferred_freq and inferred_freq != train_frequency:
                    log.warning(
                        f"Frequency mismatch: training={train_frequency}, "
                        f"prediction={inferred_freq}"
                    )
            except Exception:
                log.warning("Could not infer frequency from prediction dataset")

        # Check for backcasting (dates before training start)
        if train_last_ds and train_dataset is not None:
            try:
                train_df = train_dataset.to_pandas()

                # Auto-detect timestamp in training data
                train_timestamp_col = None
                if "ds" in train_df.columns:
                    train_timestamp_col = "ds"
                else:
                    for col in train_df.columns:
                        try:
                            pd.to_datetime(train_df[col])
                            train_timestamp_col = col
                            break
                        except Exception:
                            continue

                if train_timestamp_col:
                    train_ds_series = pd.to_datetime(train_df[train_timestamp_col])
                    train_start = train_ds_series.min()

                    min_pred_ds = ds_series.min()
                    if min_pred_ds < train_start:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=(
                                f"Requested timestamps precede the training "
                                f"window start (train_start = {train_start}). "
                                f"Retrain the model including those dates or "
                                f"submit only in-sample/future dates."
                            ),
                        )
            except HTTPException:
                raise
            except Exception as e:
                log.warning(f"Could not validate backcasting: {e}")

        # Validate exogenous regressors
        if exog_cols:
            missing_exog = [col for col in exog_cols if col not in pred_df.columns]
            if missing_exog:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Missing required exogenous columns for prediction: "
                        f"{missing_exog}. The model was trained with these "
                        f"regressors and requires values for all prediction "
                        f"timestamps."
                    ),
                )

            # Check for NaN values in exogenous columns
            for col in exog_cols:
                if pred_df[col].isna().any():
                    nan_count = pred_df[col].isna().sum()
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Exogenous column '{col}' contains {nan_count} "
                            f"missing values. All exogenous regressors must have "
                            f"values for every timestamp."
                        ),
                    )

        log.info(f"Forecasting validation passed for {len(ds_series)} timestamps")
        return timestamp_col

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        prediction_id: int = self.kwargs["prediction_id"]
        manual_input_data: list = self.kwargs.get("manual_input_data", [])
        forecast_periods = self.kwargs.get("forecast_periods")

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

                # Validate input data (forecast_periods also valid for forecasting)
                if (
                    not manual_input_data
                    and not dataset_id
                    and forecast_periods is None
                ):
                    prediction.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Either dataset_id, manual_input_data, or "
                        "forecast_periods must be provided."
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

            # Load training dataset for type info and label processing
            try:
                train_dataset: DashAIDataset = load_dataset(
                    str(Path(f"{dataset_trained.file_path}/dataset/"))
                )
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Cannot load training dataset from "
                    f"{dataset_trained.file_path}/dataset/"
                ) from e

            # Determine if this is a forecasting task
            is_forecasting = model_session.task_name == "ForecastingTask"

            if is_forecasting:
                # ============ FORECASTING PREDICTION ============
                try:
                    if forecast_periods is not None:
                        # --- Auto-generate future timestamps ---
                        log.info(
                            f"Auto-generating {forecast_periods} future timestamps"
                        )

                        timestamp_col = "ds"
                        frequency = getattr(trained_model, "frequency", "D")
                        if frequency is None:
                            frequency = "D"

                        # Get last training date from model
                        last_ds = getattr(trained_model, "last_ds", None)
                        if last_ds is None:
                            last_ds = getattr(trained_model, "last_timestamp", None)

                        if last_ds is None:
                            # Try to get from training dataset
                            try:
                                train_df = train_dataset.to_pandas()
                                if "ds" in train_df.columns:
                                    last_ds = pd.to_datetime(train_df["ds"]).max()
                                else:
                                    for col in train_df.columns:
                                        try:
                                            ds_series = pd.to_datetime(train_df[col])
                                            last_ds = ds_series.max()
                                            timestamp_col = col
                                            break
                                        except Exception:
                                            continue
                            except Exception as e:
                                log.warning(f"Could not read training dataset: {e}")

                        if last_ds is None:
                            raise JobError(
                                "Cannot auto-generate timestamps: Unable to "
                                "determine the last training date. "
                                "Please use a dataset instead."
                            )

                        last_training_date = pd.to_datetime(last_ds)

                        # Check exogenous regressors
                        exog_cols = getattr(trained_model, "exog_cols", [])
                        if exog_cols:
                            raise HTTPException(
                                status_code=(status.HTTP_422_UNPROCESSABLE_ENTITY),
                                detail=(
                                    f"Cannot auto-generate predictions for "
                                    f"models with exogenous variables "
                                    f"({exog_cols}). Please upload a dataset "
                                    f"with timestamps and exogenous values."
                                ),
                            )

                        # Generate future timestamps using DateOffset
                        freq_offset_map = {
                            "D": pd.DateOffset(days=1),
                            "H": pd.DateOffset(hours=1),
                            "W": pd.DateOffset(weeks=1),
                            "M": pd.DateOffset(months=1),
                            "MS": pd.DateOffset(months=1),
                            "ME": pd.DateOffset(months=1),
                            "Y": pd.DateOffset(years=1),
                            "YS": pd.DateOffset(years=1),
                            "YE": pd.DateOffset(years=1),
                            "A": pd.DateOffset(years=1),
                            "AS": pd.DateOffset(years=1),
                            "Q": pd.DateOffset(months=3),
                            "QS": pd.DateOffset(months=3),
                            "QE": pd.DateOffset(months=3),
                        }

                        first_offset = freq_offset_map.get(frequency)
                        if first_offset is None:
                            try:
                                first_offset = pd.Timedelta(1, unit=frequency[0])
                            except ValueError:
                                log.warning(
                                    "Unknown frequency '%s', defaulting to 1 day",
                                    frequency,
                                )
                                first_offset = pd.DateOffset(days=1)

                        start_date = last_training_date + first_offset

                        freq_alias_map = {
                            "M": "MS",
                            "Y": "YS",
                            "A": "YS",
                            "Q": "QS",
                            "ME": "MS",
                            "YE": "YS",
                            "QE": "QS",
                        }
                        safe_freq = freq_alias_map.get(frequency, frequency)

                        future_dates = pd.date_range(
                            start=start_date,
                            periods=forecast_periods,
                            freq=safe_freq,
                        )
                        future_df = pd.DataFrame({timestamp_col: future_dates})

                        log.info(
                            f"Generated timestamps from {future_dates[0]} "
                            f"to {future_dates[-1]}"
                        )

                    else:
                        # --- Use uploaded dataset for forecasting ---
                        if dataset_id:
                            loaded_dataset = load_dataset(
                                str(Path(f"{dataset.file_path}/dataset/"))
                            )
                        elif manual_input_data:
                            dataset_trained_path = str(
                                Path(f"{dataset_trained.file_path}/dataset/")
                            )
                            loaded_dataset = task.process_manual_input(
                                manual_input_data, dataset_trained_path
                            )
                        else:
                            raise JobError(
                                "Either dataset_id, manual_input_data, or "
                                "forecast_periods must be provided for "
                                "forecasting."
                            )

                        # Validate forecasting dataset
                        timestamp_col = self._validate_forecasting_dataset(
                            loaded_dataset,
                            model_session,
                            trained_model,
                            train_dataset,
                        )

                        pred_df = loaded_dataset.to_pandas()
                        exog_cols = getattr(trained_model, "exog_cols", [])
                        future_cols = [timestamp_col] + exog_cols
                        available_cols = [
                            col for col in future_cols if col in pred_df.columns
                        ]

                        if timestamp_col not in available_cols:
                            raise JobError(
                                f"Forecasting prediction requires "
                                f"'{timestamp_col}' column in dataset"
                            )

                        future_df = pred_df[available_cols].copy()
                        future_df[timestamp_col] = pd.to_datetime(
                            future_df[timestamp_col]
                        )

                    # Call model.predict with the future_df
                    log.info(f"Predicting on {len(future_df)} timestamps")
                    predictions = trained_model.predict(future_df)

                    # Handle different prediction formats
                    if hasattr(predictions, "yhat"):
                        y_pred = predictions["yhat"].to_numpy()
                    elif isinstance(predictions, np.ndarray):
                        y_pred = predictions
                    else:
                        y_pred = np.array(predictions)

                    # Build result dataset: timestamp + prediction
                    output_col = (
                        model_session.output_columns[0]
                        if model_session.output_columns
                        else "prediction"
                    )
                    result_df = future_df[[timestamp_col]].copy()
                    result_df[output_col] = y_pred

                    # Add confidence intervals if available
                    if hasattr(predictions, "columns"):
                        if "yhat_lower" in predictions.columns:
                            result_df["yhat_lower"] = predictions[
                                "yhat_lower"
                            ].to_numpy()
                        if "yhat_upper" in predictions.columns:
                            result_df["yhat_upper"] = predictions[
                                "yhat_upper"
                            ].to_numpy()

                    dataset_with_prediction = to_dashai_dataset(result_df)

                except HTTPException:
                    prediction.set_status_as_error()
                    db.commit()
                    raise
                except ValueError as ve:
                    prediction.set_status_as_error()
                    db.commit()
                    log.error(f"Validation Error: {ve}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid input data: {str(ve)}",
                    ) from ve
                except Exception as e:
                    prediction.set_status_as_error()
                    db.commit()
                    log.error(e)
                    raise JobError(
                        "Forecasting prediction failed",
                    ) from e

            else:
                # ============ STANDARD PREDICTION ============
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
                        train_dataset,
                        y_pred_proba,
                        model_session.output_columns[0],
                    )

                    # Build dataset with predictions
                    dataset_with_prediction = to_dashai_dataset(
                        prepared_dataset.add_column(
                            model_session.output_columns[0], y_pred
                        )
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

            # ============ SAVE PREDICTIONS TO ARROW ============
            try:
                path = str(Path(f"{config['DATASETS_PATH']}/predictions/"))
                folder_name = str(uuid.uuid4())
                full_path = Path(path) / folder_name
                full_path.mkdir(parents=True, exist_ok=True)

                # Build schema for the saved dataset
                if is_forecasting:
                    # For forecasting, no input/output column type filtering
                    filtered_schema = {}
                else:
                    trained_schema = train_dataset.types
                    filtered_schema = {
                        key: value.to_string()
                        for key, value in trained_schema.items()
                        if key
                        in model_session.input_columns + model_session.output_columns
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
                    "Cannot save prediction results",
                ) from e
