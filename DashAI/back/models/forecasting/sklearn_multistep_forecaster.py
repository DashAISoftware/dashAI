"""Sklearn-based multi-step forecasting model for DashAI.

This model uses sklearn regressors with a sliding window approach to perform
multi-step-ahead forecasting. It internally creates lag features and can
predict multiple steps into the future.
"""

import os
import pickle
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor as _RandomForestRegressor
from sklearn.linear_model import LinearRegression as _LinearRegression
from sklearn.linear_model import Ridge as _Ridge
from sklearn.multioutput import MultiOutputRegressor

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.models.forecasting.base_forecasting_model import ForecastingModel


class SklearnMultiStepForecasterSchema(BaseSchema):
    """Schema for SklearnMultiStepForecaster configuration."""

    base_estimator: schema_field(
        enum_field(enum=["linear", "ridge", "random_forest"]),
        placeholder="linear",
        description=(
            "Base estimator for forecasting. "
            "'linear': Fast linear regression (best for linear trends). "
            "'ridge': Linear regression with L2 regularization "
            "(prevents overfitting). "
            "'random_forest': Tree-based ensemble (handles non-linear patterns)."
        ),
    ) = "linear"  # type: ignore

    window_size: schema_field(
        int_field(ge=1, le=365),
        placeholder=7,
        description=(
            "Number of past time steps (lags) to use as features. "
            "Larger values capture longer-term patterns but require more data."
        ),
    ) = 7  # type: ignore

    forecast_strategy: schema_field(
        enum_field(enum=["direct", "recursive"]),
        placeholder="direct",
        description=(
            "Multi-step forecasting strategy. "
            "'direct': Train separate model for each horizon "
            "(more accurate, slower). "
            "'recursive': Use predictions as inputs for next step "
            "(faster, error compounds)."
        ),
    ) = "direct"  # type: ignore


class SklearnMultiStepForecaster(ForecastingModel):
    """Sklearn-based multi-step forecasting model.

    This model transforms time series forecasting into a supervised learning problem
    by creating lag features automatically. It supports:
    - Multiple sklearn base estimators (linear, ridge, random_forest)
    - Direct multi-step strategy (separate model per horizon)
    - Recursive strategy (iterative predictions)
    - Exogenous variables

    Example usage in ForecastingTask:
    1. User uploads time series with columns: [timestamp, value, exog1, exog2]
    2. Task identifies timestamp, target, exogenous variables
    3. Model internally creates lags and trains
    4. Prediction works exactly like Prophet/ARIMA

    The key advantage is that users can leverage sklearn's powerful regression
    models for forecasting without manually creating lag features.
    """

    SCHEMA = SklearnMultiStepForecasterSchema
    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    _task_type = "ForecastingTask"

    def __init__(
        self,
        base_estimator: str = "linear",
        window_size: int = 7,
        forecast_strategy: str = "direct",
        **kwargs,
    ) -> None:
        """Initialize SklearnMultiStepForecaster.

        Parameters
        ----------
        base_estimator : str
            Base sklearn estimator to use ('linear', 'ridge', 'random_forest')
        window_size : int
            Number of past time steps to use as lag features
        forecast_strategy : str
            Strategy for multi-step forecasting ('direct' or 'recursive')
        **kwargs
            Additional arguments passed to ForecastingModel
        """
        super().__init__(**kwargs)

        self.base_estimator = base_estimator
        self.window_size = window_size
        self.forecast_strategy = forecast_strategy

        # Internal state
        self.models: List[Any] = []
        self.training_history: Optional[pd.Series] = None
        self.training_exog_history: Optional[pd.DataFrame] = None
        self.max_horizon: int = 1

    def _get_base_estimator(self):
        """Get instance of base estimator."""
        estimators = {
            "linear": _LinearRegression,
            "ridge": _Ridge,
            "random_forest": _RandomForestRegressor,
        }

        if self.base_estimator not in estimators:
            raise ValueError(
                f"Unknown base_estimator '{self.base_estimator}'. "
                f"Supported: {list(estimators.keys())}"
            )

        return estimators[self.base_estimator]()

    def _create_lag_features(
        self, series: pd.Series, exog_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Create lag features from time series.

        Parameters
        ----------
        series : pd.Series
            Time series values
        exog_df : pd.DataFrame, optional
            Exogenous variables (must have same index as series)

        Returns
        -------
        pd.DataFrame
            DataFrame with lag features and optional exogenous variables
        """
        result = pd.DataFrame(index=series.index)

        # Create lags (lag_1 is t-1, lag_2 is t-2, etc.)
        for lag in range(1, self.window_size + 1):
            result[f"lag_{lag}"] = series.shift(lag)

        # Add exogenous variables if present
        if exog_df is not None:
            for col in exog_df.columns:
                result[col] = exog_df[col]

        return result

    def fit(
        self,
        x_train: DashAIDataset,
        y: DashAIDataset,
        temporal_metadata: dict = None,
        **fit_params,
    ) -> "SklearnMultiStepForecaster":
        """Train the multi-step forecasting model.

        Parameters
        ----------
        x_train : DashAIDataset
            Input features (timestamp + optional exogenous variables)
        y : DashAIDataset
            Target time series
        temporal_metadata : dict
            Metadata from ForecastingTask with timestamp_col, target_col, etc.
        **fit_params
            Additional fitting parameters (can include 'horizon')

        Returns
        -------
        SklearnMultiStepForecaster
            Fitted model
        """
        if temporal_metadata is None:
            raise ValueError(
                "temporal_metadata is required for SklearnMultiStepForecaster"
            )

        # Get metadata
        self.timestamp_col = temporal_metadata.get("timestamp_col")
        self.target_col = temporal_metadata.get("target_col")
        self.exog_cols = temporal_metadata.get("exog_cols", [])
        self.frequency = temporal_metadata.get("frequency", "D")

        print("[SklearnMultiStepForecaster] Using temporal metadata from task:")
        print(f"  - Timestamp: '{self.timestamp_col}'")
        print(f"  - Target: '{self.target_col}'")
        print(f"  - Exogenous: {self.exog_cols}")
        print(f"  - Frequency: {self.frequency}")

        # Convert to pandas
        x_df = x_train.to_pandas()
        y_df = y.to_pandas()

        # Get target series
        target_in_inputs = self.target_col in x_df.columns
        if target_in_inputs:
            print(
                f"[SklearnMultiStepForecaster] ℹ️  Target '{self.target_col}' "
                "found in inputs - using it from there"
            )
            target_series = x_df[self.target_col]
        else:
            target_series = y_df[self.target_col]

        # Extract exogenous variables if present
        exog_df = None
        if self.exog_cols:
            exog_df = x_df[self.exog_cols]
            print(f"[SklearnMultiStepForecaster] Exogenous variables: {self.exog_cols}")

        # Create lag features
        X_with_lags = self._create_lag_features(target_series, exog_df)

        # Get horizon from fit_params (default to 1)
        horizon = fit_params.get("horizon", 1)
        self.max_horizon = horizon

        print(f"[SklearnMultiStepForecaster] Training for horizon: {horizon}")
        print(f"[SklearnMultiStepForecaster] Window size: {self.window_size}")
        print(f"[SklearnMultiStepForecaster] Strategy: {self.forecast_strategy}")

        # For direct strategy: train one model per horizon
        if self.forecast_strategy == "direct":
            self.models = []
            for h in range(1, horizon + 1):
                # Create target: y shifted h steps ahead
                y_h = target_series.shift(-h)

                # Remove NaN rows
                mask = X_with_lags.notna().all(axis=1) & y_h.notna()
                X_clean = X_with_lags[mask]
                y_clean = y_h[mask]

                if len(X_clean) == 0:
                    raise ValueError(
                        f"No valid samples after creating lags and horizon {h}. "
                        f"Try reducing window_size or using more data."
                    )

                # Train model for this horizon
                model = MultiOutputRegressor(self._get_base_estimator())
                model.fit(X_clean.to_numpy(), y_clean.to_numpy().reshape(-1, 1))
                self.models.append(model)

            print(
                f"[SklearnMultiStepForecaster] Trained {len(self.models)} models "
                "(direct strategy)"
            )

        # For recursive strategy: train single model for 1-step ahead
        else:  # recursive
            y_1 = target_series.shift(-1)
            mask = X_with_lags.notna().all(axis=1) & y_1.notna()
            X_clean = X_with_lags[mask]
            y_clean = y_1[mask]

            if len(X_clean) == 0:
                raise ValueError(
                    "No valid samples after creating lags. "
                    "Try reducing window_size or using more data."
                )

            model = MultiOutputRegressor(self._get_base_estimator())
            model.fit(X_clean.to_numpy(), y_clean.to_numpy().reshape(-1, 1))
            self.models = [model]

            print("[SklearnMultiStepForecaster] Trained 1 model (recursive strategy)")

        # Store last window_size values for predictions
        self.training_history = target_series.iloc[-self.window_size :]
        if self.exog_cols and exog_df is not None:
            self.training_exog_history = exog_df.iloc[-self.window_size :]

        print("[SklearnMultiStepForecaster] ✅ Training completed")

        return self

    def predict(
        self,
        x_pred: Optional[Any] = None,
        periods: Optional[int] = None,
        exog_future: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> Union[np.ndarray, pd.DataFrame]:
        """Generate forecasts.

        Parameters
        ----------
        x_pred : Any, optional
            Input data for in-sample predictions (not yet supported)
        periods : int, optional
            Number of steps to forecast into the future
        exog_future : pd.DataFrame, optional
            Future exogenous variable values
        **kwargs
            Additional parameters

        Returns
        -------
        np.ndarray
            Predictions array
        """
        if not self.models:
            raise ValueError("Model not fitted. Call fit() first.")

        # Handle different input types (compatibility with ForecastingTask)
        if x_pred is not None and isinstance(x_pred, (int, np.integer)):
            periods = int(x_pred)
            x_pred = None

        # Out-of-sample forecast
        if periods is not None:
            if periods <= 0:
                raise ValueError("Prediction horizon must be a positive integer.")

            # Validate exogenous variables if needed
            if self.exog_cols:
                if exog_future is None:
                    raise ValueError(
                        f"Future exogenous values required for columns: "
                        f"{self.exog_cols}"
                    )

                missing_cols = [
                    col for col in self.exog_cols if col not in exog_future.columns
                ]
                if missing_cols:
                    raise ValueError(
                        f"Missing exogenous columns for prediction: {missing_cols}"
                    )

                if len(exog_future) < periods:
                    raise ValueError(
                        f"Exogenous data length ({len(exog_future)}) must be at "
                        f"least {periods} for the requested forecast horizon."
                    )

            # Direct strategy: use pre-trained models
            if self.forecast_strategy == "direct":
                predictions = []
                num_models = min(len(self.models), periods)

                for h in range(num_models):
                    # Create features from training history
                    lags = self.training_history.iloc[-self.window_size :].to_numpy()

                    # Add exog if needed
                    if self.exog_cols and exog_future is not None:
                        exog_h = exog_future.iloc[h][self.exog_cols].to_numpy()
                        features = np.concatenate([lags, exog_h])
                    else:
                        features = lags

                    pred = self.models[h].predict(features.reshape(1, -1))[0, 0]
                    predictions.append(pred)

                # If more periods requested than trained models, warn user
                if periods > num_models:
                    print(
                        f"⚠️  Warning: Requested {periods} periods but only "
                        f"{num_models} models trained. Returning {num_models} "
                        "predictions."
                    )

                return np.array(predictions)

            # Recursive strategy: iterative predictions
            else:
                predictions = []
                current_window = list(self.training_history.to_numpy())

                for h in range(periods):
                    # Create features
                    lags = np.array(current_window[-self.window_size :])

                    # Add exog if needed
                    if self.exog_cols and exog_future is not None:
                        exog_h = exog_future.iloc[h][self.exog_cols].to_numpy()
                        features = np.concatenate([lags, exog_h])
                    else:
                        features = lags

                    # Predict next step
                    pred = self.models[0].predict(features.reshape(1, -1))[0, 0]
                    predictions.append(pred)

                    # Update window with prediction
                    current_window.append(pred)

                return np.array(predictions)

        # In-sample predictions not yet supported
        if x_pred is not None:
            raise NotImplementedError(
                "In-sample predictions not yet supported for "
                "SklearnMultiStepForecaster. Use periods parameter for "
                "out-of-sample forecasting."
            )

        raise ValueError(
            "Either x_pred or periods parameter must be provided for prediction."
        )

    def save(self, filename: str) -> None:
        """Save model to file.

        Parameters
        ----------
        filename : str
            Path to save the model
        """
        if not self.models:
            raise ValueError("Cannot save model before fitting.")

        model_state = {
            "models": self.models,
            "training_history": self.training_history,
            "training_exog_history": self.training_exog_history,
            "exog_cols": self.exog_cols,
            "timestamp_col": self.timestamp_col,
            "target_col": self.target_col,
            "frequency": self.frequency,
            "max_horizon": self.max_horizon,
            "config": {
                "base_estimator": self.base_estimator,
                "window_size": self.window_size,
                "forecast_strategy": self.forecast_strategy,
            },
        }

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            pickle.dump(model_state, f)

        print(f"✅ SklearnMultiStepForecaster saved to {filename}")

    def load(self, filename: str) -> "SklearnMultiStepForecaster":
        """Load model from file.

        Parameters
        ----------
        filename : str
            Path to load the model from

        Returns
        -------
        SklearnMultiStepForecaster
            Loaded model instance
        """
        with open(filename, "rb") as f:
            model_state = pickle.load(f)

        self.models = model_state["models"]
        self.training_history = model_state["training_history"]
        self.training_exog_history = model_state.get("training_exog_history")
        self.exog_cols = model_state["exog_cols"]
        self.timestamp_col = model_state.get("timestamp_col")
        self.target_col = model_state.get("target_col")
        self.frequency = model_state.get("frequency")
        self.max_horizon = model_state.get("max_horizon", 1)

        config = model_state["config"]
        for key, value in config.items():
            setattr(self, key, value)

        print(f"✅ SklearnMultiStepForecaster loaded from {filename}")
        return self
