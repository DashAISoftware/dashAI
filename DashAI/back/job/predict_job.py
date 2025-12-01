import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
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

    def _validate_forecasting_dataset(
        self, dataset: DashAIDataset, exp: Experiment, model: Any
    ) -> str:
        """Validate dataset for forecasting prediction.

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

        # Auto-detect timestamp column (try 'ds' first for compatibility, then detect)
        timestamp_col = None
        if "ds" in pred_df.columns:
            timestamp_col = "ds"
        else:
            # Try to auto-detect timestamp column
            for col in pred_df.columns:
                try:
                    pd.to_datetime(pred_df[col])
                    timestamp_col = col
                    log.info(f"🔍 Auto-detected timestamp column: '{col}'")
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
                detail=f"Cannot parse '{timestamp_col}' column as datetime: {str(e)}",
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

        # 5. Get training metadata from model
        train_frequency = getattr(model, "frequency", None)
        train_last_ds = getattr(model, "last_ds", None)
        exog_cols = getattr(model, "exog_cols", [])

        log.info(
            f"Training metadata - frequency: {train_frequency}, "
            f"last_ds: {train_last_ds}, exog_cols: {exog_cols}"
        )

        # 6. Validate frequency consistency (if available)
        if train_frequency and len(ds_series) >= 2:
            # Infer frequency from prediction dataset
            try:
                inferred_freq = pd.infer_freq(ds_series)
                if inferred_freq and inferred_freq != train_frequency:
                    log.warning(
                        f"Frequency mismatch: training={train_frequency}, "
                        f"prediction={inferred_freq}"
                    )
            except Exception:
                log.warning("Could not infer frequency from prediction dataset")

        # 7. Check for backcasting (dates before training start)
        if train_last_ds:
            # Get training start from experiment splits if available
            try:
                split_indexes = (
                    json.loads(exp.split_indexes) if exp.split_indexes else {}
                )
                train_indexes = split_indexes.get("train_indexes", [])

                if train_indexes:
                    # Load training dataset to get the actual start date
                    train_dataset_path = Path(f"{exp.dataset.file_path}/dataset/")
                    if train_dataset_path.exists():
                        train_ds = load_dataset(str(train_dataset_path))
                        train_df = train_ds.to_pandas()

                        # Auto-detect timestamp in training data (same logic
                        # as prediction)
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
                            train_ds_series = pd.to_datetime(
                                train_df[train_timestamp_col]
                            )
                            train_start = train_ds_series.iloc[train_indexes[0]]

                            # Check if any prediction timestamp is before start
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

        # 8. Validate exogenous regressors
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

        log.info(f"✅ Forecasting validation passed for {len(ds_series)} timestamps")

        # Return the detected timestamp column name
        return timestamp_col

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        run_id: int = self.kwargs["run_id"]
        id: int | None = self.kwargs.get("id")  # Optional when forecast_periods is used
        json_filename: str = self.kwargs["json_filename"]
        forecast_periods = self.kwargs.get("forecast_periods")

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

                # Dataset is optional when using auto-generated timestamps
                dataset: Dataset | None = None
                loaded_dataset: DashAIDataset | None = None

                if id is not None:
                    dataset = db.get(Dataset, id)
                    if not dataset:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Dataset not found",
                        )

                    try:
                        loaded_dataset = load_dataset(
                            str(Path(f"{dataset.file_path}/dataset/"))
                        )
                    except Exception as e:
                        log.exception(e)
                        raise JobError(
                            f"Cannot load dataset from path "
                            f"{dataset.file_path}/dataset/"
                        ) from e
                elif forecast_periods is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "Either 'id' (dataset) or 'forecast_periods' "
                            "must be provided"
                        ),
                    )

            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal database error",
                ) from e

            try:
                model_class = component_registry[run.model_name]["class"]
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Model {run.model_name} not found in the registry"
                ) from e

            try:
                # Instantiate model with parameters first
                model: BaseModel = model_class(**run.parameters)
                # Then load the trained weights
                trained_model: BaseModel = model.load(run.run_path)
            except Exception as e:
                log.exception(e)
                raise JobError(f"Cannot load model from path {run.run_path}") from e

            try:
                task: BaseTask = component_registry[exp.task_name]["class"]()
            except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Task {exp.task_name} not found in the registry",
                ) from e

            # ============ FORECASTING-SPECIFIC LOGIC ============
            is_forecasting = exp.task_name == "ForecastingTask"

            if is_forecasting:
                # Check if user provided forecast_periods for auto-generation
                forecast_periods = self.kwargs.get("forecast_periods")

                if forecast_periods is not None:
                    # ============ AUTO-GENERATE TIMESTAMPS ============
                    log.info(f"🔮 Auto-generating {forecast_periods} future timestamps")

                    # Get timestamp column (default to 'ds' for compatibility)
                    timestamp_col = "ds"

                    # Get frequency from model
                    frequency = getattr(trained_model, "frequency", "D")
                    if frequency is None:
                        frequency = "D"

                    # Get last training date from model
                    # Try last_ds (Prophet, ARIMA, SARIMAX) or last_timestamp (Sklearn)
                    last_ds = getattr(trained_model, "last_ds", None)
                    if last_ds is None:
                        last_ds = getattr(trained_model, "last_timestamp", None)

                    if last_ds is None:
                        # If not in model, try to get from training dataset
                        try:
                            train_dataset_path = Path(
                                f"{exp.dataset.file_path}/dataset/"
                            )
                            if train_dataset_path.exists():
                                train_ds = load_dataset(str(train_dataset_path))
                                train_df = train_ds.to_pandas()

                                # Try to find timestamp column
                                if "ds" in train_df.columns:
                                    last_ds = pd.to_datetime(train_df["ds"]).max()
                                else:
                                    # Try to auto-detect
                                    for col in train_df.columns:
                                        try:
                                            ds_series = pd.to_datetime(train_df[col])
                                            last_ds = ds_series.max()
                                            timestamp_col = col
                                            break
                                        except Exception:
                                            continue
                        except Exception as e:
                            log.warning(f"Could not load training dataset: {e}")

                    if last_ds is None:
                        raise JobError(
                            "Cannot auto-generate timestamps: Unable to determine "
                            "the last training date. Please use a dataset instead."
                        )

                    last_training_date = pd.to_datetime(last_ds)

                    # Check if model has exogenous regressors
                    exog_cols = getattr(trained_model, "exog_cols", [])
                    if exog_cols:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=(
                                f"Cannot auto-generate predictions for models with "
                                f"exogenous variables ({exog_cols}). Please upload "
                                f"a dataset with timestamps and exogenous values."
                            ),
                        )

                    # Generate future timestamps
                    try:
                        # Use DateOffset for frequencies that don't work with Timedelta
                        # (like 'M' for months, 'Y' for years)
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

                        # Get the appropriate offset for this frequency
                        first_offset = freq_offset_map.get(frequency)
                        if first_offset is None:
                            # Fallback: try using Timedelta for simple frequencies
                            try:
                                first_offset = pd.Timedelta(1, unit=frequency[0])
                            except ValueError:
                                # If that fails too, default to 1 day
                                log.warning(
                                    "Unknown frequency '%s', defaulting to 1 day",
                                    frequency,
                                )
                                first_offset = pd.DateOffset(days=1)

                        start_date = last_training_date + first_offset

                        # For date_range, also need to handle frequency aliases
                        # Use Month Start (MS) instead of Month End (ME)
                        freq_alias_map = {
                            "M": "MS",  # Month start (more compatible)
                            "Y": "YS",  # Year start
                            "A": "YS",  # Year start (alias)
                            "Q": "QS",  # Quarter start
                            "ME": "MS",  # Convert month end to month start
                            "YE": "YS",  # Convert year end to year start
                            "QE": "QS",  # Convert quarter end to quarter start
                        }
                        safe_freq = freq_alias_map.get(frequency, frequency)

                        future_dates = pd.date_range(
                            start=start_date,
                            periods=forecast_periods,
                            freq=safe_freq,
                        )
                        future_df = pd.DataFrame({timestamp_col: future_dates})
                        available_cols = [
                            timestamp_col
                        ]  # No exog columns in auto-generate mode

                        log.info(
                            f"Generated timestamps from {future_dates[0]} to "
                            f"{future_dates[-1]}"
                        )
                    except Exception as e:
                        log.exception(e)
                        raise JobError(
                            f"Failed to generate timestamps: {str(e)}. "
                            f"Frequency: {frequency}, Last date: {last_training_date}"
                        ) from e

                else:
                    # ============ USE UPLOADED DATASET ============
                    log.info(
                        f"🔮 Running forecasting prediction for "
                        f"{len(loaded_dataset)} timestamps"
                    )

                    # Validate forecasting dataset and get timestamp column name
                    timestamp_col = self._validate_forecasting_dataset(
                        loaded_dataset, exp, trained_model
                    )

                    # Prepare dataset for forecasting (ignore 'y' if present)
                    pred_df = loaded_dataset.to_pandas()

                    # Build future_df with timestamp + exog columns (ignore 'y')
                    exog_cols = getattr(trained_model, "exog_cols", [])
                    future_cols = [timestamp_col] + exog_cols
                    available_cols = [
                        col for col in future_cols if col in pred_df.columns
                    ]

                    if timestamp_col not in available_cols:
                        raise JobError(
                            f"Forecasting prediction requires '{timestamp_col}' column "
                            "in dataset"
                        )

                    future_df = pred_df[available_cols].copy()
                    future_df[timestamp_col] = pd.to_datetime(future_df[timestamp_col])

                log.info(
                    f"Predicting on {len(future_df)} timestamps with "
                    f"columns: {available_cols}"
                )

                # Call model.predict with the future_df
                try:
                    predictions = trained_model.predict(future_df)

                    # Handle different prediction formats
                    if hasattr(predictions, "yhat"):
                        # Prophet-style DataFrame with yhat, yhat_lower, yhat_upper
                        y_pred = predictions["yhat"].to_numpy()

                        # Store full forecast for metadata
                        forecast_metadata = {
                            "ds": predictions["ds"]
                            .dt.strftime("%Y-%m-%d %H:%M:%S")
                            .tolist(),
                            "yhat": predictions["yhat"].tolist(),
                        }
                        if "yhat_lower" in predictions.columns:
                            forecast_metadata["yhat_lower"] = predictions[
                                "yhat_lower"
                            ].tolist()
                        if "yhat_upper" in predictions.columns:
                            forecast_metadata["yhat_upper"] = predictions[
                                "yhat_upper"
                            ].tolist()
                    elif isinstance(predictions, np.ndarray):
                        y_pred = predictions
                        forecast_metadata = None
                    else:
                        y_pred = np.array(predictions)
                        forecast_metadata = None

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Forecasting model prediction failed: {str(e)}"
                    ) from e

            else:
                # ============ STANDARD PREDICTION LOGIC ============
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

                    y_pred = task.process_predictions(
                        train_dataset, y_pred_proba, exp.output_columns[0]
                    )
                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        "Processing predictions failed",
                    ) from e

                forecast_metadata = None

            # ============ SAVE PREDICTIONS ============
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

                # Sanitize predictions for JSON serialization (convert NaN/Inf to None)
                sanitized_predictions = sanitize_for_json(y_pred.tolist())

                json_data = {
                    "metadata": {
                        "id": next_id,
                        "pred_name": json_name,
                        "run_name": run.model_name,
                        "model_name": run.name,
                        "dataset_name": dataset.name
                        if dataset
                        else f"auto_forecast_{forecast_periods}_periods",
                        "task_name": exp.task_name,
                    },
                    "prediction": sanitized_predictions,
                }

                # Add forecast-specific metadata if available
                if forecast_metadata:
                    json_data["forecast"] = sanitize_for_json(forecast_metadata)

                with open(os.path.join(path, json_name), "w") as json_file:
                    json.dump(json_data, json_file, indent=4)

                log.info(f"✅ Prediction saved to {json_name}")

            except Exception as e:
                log.exception(e)
                raise JobError(
                    "Cannot save prediction to json file",
                ) from e
