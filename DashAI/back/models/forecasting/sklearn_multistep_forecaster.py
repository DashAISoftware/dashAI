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
        placeholder=3,
        description=(
            "Number of past time steps (lags) to use as features. "
            "Smaller values work better for small datasets. "
            "Will be auto-adjusted if dataset is too small."
        ),
    ) = 3  # type: ignore

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
        window_size: int = 3,
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
        self.training_full_series: Optional[pd.Series] = None
        self.training_full_exog: Optional[pd.DataFrame] = None
        self.training_full_exog: Optional[pd.DataFrame] = None
        self.max_horizon: int = 1
        self.last_timestamp: Optional[pd.Timestamp] = None

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

        # Get horizon from fit_params (default to 1)
        horizon = fit_params.get("horizon", 1)
        self.max_horizon = horizon

        # Store last timestamp and full date sequence for future predictions
        if self.timestamp_col in x_df.columns:
            parsed_dates = pd.to_datetime(x_df[self.timestamp_col])
            self.last_timestamp = parsed_dates.max()
            self.training_dates = parsed_dates.to_numpy()
            print(f"[SklearnMultiStepForecaster] Last timestamp: {self.last_timestamp}")
        else:
            self.last_timestamp = pd.Timestamp.now()
            self.training_dates = None
            print("[SklearnMultiStepForecaster] ⚠️ No timestamp col, default to now()")

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

        n_target_samples = len(target_series)

        # Auto-adjust window_size for small datasets
        # Need: window_size lags + horizon shifts + at least 2 samples to train
        min_required = self.window_size + horizon + 2

        if n_target_samples < min_required:
            # Try to fit within constraints by reducing window size
            # The available space for window is samples minus horizon minus margin
            available_for_window = n_target_samples - horizon - 2

            if available_for_window < 1:
                # Even with window_size=1, we can't fit. Reduce horizon too.
                # Minimum setup: window=1, horizon=1, need at least 4 samples
                if n_target_samples >= 4:
                    self.window_size = 1
                    horizon = max(1, n_target_samples - 3)
                    print(
                        f"[SklearnMultiStepForecaster] ⚠️  Very small dataset "
                        f"({n_target_samples} samples). "
                        f"Forced window_size=1, horizon={horizon}"
                    )
                else:
                    raise ValueError(
                        f"Dataset too small for forecasting. Need at least 4 samples, "
                        f"got {n_target_samples}. Please use more training data."
                    )
            else:
                old_window = self.window_size
                self.window_size = max(1, available_for_window)
                print(
                    f"[SklearnMultiStepForecaster] ⚠️  Auto-adjusted window_size: "
                    f"{old_window} → {self.window_size} "
                    f"(target series has {n_target_samples} samples)"
                )

        self.max_horizon = horizon

        print(f"[SklearnMultiStepForecaster] Training for horizon: {horizon}")
        print(f"[SklearnMultiStepForecaster] Window size: {self.window_size}")
        print(f"[SklearnMultiStepForecaster] Strategy: {self.forecast_strategy}")

        # Create lag features
        X_with_lags = self._create_lag_features(target_series, exog_df)

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

        # Store FULL training series and exog for in-sample predictions
        # We need the complete history to create lags for any subset
        self.training_full_series = target_series.copy()
        self.training_history = target_series.iloc[-self.window_size :]
        if self.exog_cols and exog_df is not None:
            self.training_full_exog = exog_df.copy()
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
            Input data for in-sample predictions containing timestamp and
            optional exogenous variables. Can also be an integer for compatibility.
        periods : int, optional
            Number of steps to forecast into the future
        exog_future : pd.DataFrame, optional
            Future exogenous variable values
        **kwargs
            Additional parameters (can include 'horizon' as alias for 'periods')

        Returns
        -------
        np.ndarray
            Predictions array
        """
        if not self.models:
            raise ValueError("Model not fitted. Call fit() first.")

        # Handle horizon alias
        if periods is None and "horizon" in kwargs:
            periods = kwargs["horizon"]

        # Handle different input types (compatibility with ForecastingTask)
        if x_pred is not None and isinstance(x_pred, (int, np.integer)):
            periods = int(x_pred)
            x_pred = None

        # Note: If x_pred is provided with periods, use x_pred as history context

        # In-sample predictions (for metrics calculation)
        if x_pred is not None and periods is None:
            from DashAI.back.dataloaders.classes.dashai_dataset import (
                to_dashai_dataset,
            )

            if isinstance(x_pred, pd.DataFrame):
                input_df = x_pred.copy()
            else:
                input_df = to_dashai_dataset(x_pred).to_pandas()

            print(
                f"[SklearnMultiStepForecaster] In-sample prediction for "
                f"{len(input_df)} time steps"
            )

            # For in-sample predictions, we need the full training data
            # because we create lags from historical values
            if not hasattr(self, "training_full_series"):
                raise ValueError(
                    "No training history available. Model may not be fitted properly."
                )

            # Detect whether timestamps are within training range or beyond.
            # val/test splits reset their pandas index to 0-based, so index lookup
            # in training lag features would return wrong rows. Use timestamp
            # comparison to choose the correct prediction strategy.
            is_within_training = True
            if self.timestamp_col and self.timestamp_col in input_df.columns:
                input_ts = pd.to_datetime(input_df[self.timestamp_col])
                is_within_training = input_ts.max() <= self.last_timestamp

            if is_within_training:
                # True in-sample: build lag features from training data and look
                # up the matching row positions.
                exog_df = None
                if self.exog_cols:
                    missing_cols = [
                        col for col in self.exog_cols if col not in input_df.columns
                    ]
                    if missing_cols:
                        raise ValueError(
                            f"Missing exogenous columns for prediction: {missing_cols}"
                        )
                    exog_df = input_df[self.exog_cols]

                target_series = self.training_full_series
                full_exog_df = (
                    self.training_full_exog
                    if hasattr(self, "training_full_exog")
                    else None
                )

                X_with_lags = self._create_lag_features(target_series, full_exog_df)

                if self.exog_cols and exog_df is not None:
                    for col in self.exog_cols:
                        X_with_lags.loc[input_df.index, col] = exog_df[col].to_numpy()

                X_subset = X_with_lags.loc[input_df.index]
                mask = X_subset.notna().all(axis=1)
                X_clean = X_subset[mask]

                if len(X_clean) == 0:
                    print(
                        f"[SklearnMultiStepForecaster] ⚠️  No valid samples for "
                        f"in-sample prediction (need {self.window_size} historical "
                        f"values). Returning NaN predictions for "
                        f"{len(input_df)} points."
                    )
                    return np.full(len(input_df), np.nan)

                predictions_full = np.full(len(input_df), np.nan)
                predictions = self.models[0].predict(X_clean.to_numpy())
                predictions_full[mask] = predictions.flatten()

                print(
                    f"[SklearnMultiStepForecaster] Generated {mask.sum()} in-sample "
                    f"predictions (first {(~mask).sum()} skipped due to lag window)"
                )
                return predictions_full

            else:
                # Out-of-training (val/test): recursive 1-step-ahead forecast
                # seeded from the last window_size training values.
                n_steps = len(input_df)
                history = list(self.training_history.to_numpy())
                results = []
                for _ in range(n_steps):
                    features = np.array(history[-self.window_size :]).reshape(1, -1)
                    pred = float(self.models[0].predict(features).flatten()[0])
                    results.append(pred)
                    history.append(pred)

                print(
                    f"[SklearnMultiStepForecaster] Generated {n_steps} recursive "
                    f"out-of-training predictions"
                )
                return np.array(results)

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

            # Prepare history for prediction
            # If x_pred is provided, use it as history (context)
            # Otherwise, use training history
            history_series = self.training_history

            if x_pred is not None:
                # Convert x_pred to pandas if needed
                if isinstance(x_pred, pd.DataFrame):
                    input_df = x_pred.copy()
                else:
                    from DashAI.back.dataloaders.classes.dashai_dataset import (
                        to_dashai_dataset,
                    )

                    input_df = to_dashai_dataset(x_pred).to_pandas()

                # Check if target column is present
                if self.target_col in input_df.columns:
                    print(
                        f"[SklearnMultiStepForecaster] Using input as context "
                        f"({len(input_df)} rows)"
                    )
                    history_series = input_df[self.target_col]

                    # Also update last_timestamp if available
                    if self.timestamp_col in input_df.columns:
                        self.last_timestamp = pd.to_datetime(
                            input_df[self.timestamp_col]
                        ).max()
                else:
                    print(
                        f"[SklearnMultiStepForecaster] ⚠️ No target col "
                        f"'{self.target_col}', using training history"
                    )

            # Ensure we have enough history
            if history_series is None or len(history_series) < self.window_size:
                history_len = 0 if history_series is None else len(history_series)
                print(
                    f"[SklearnMultiStepForecaster] ⚠️  History length ({history_len}) "
                    f"is less than window size ({self.window_size}). "
                    f"Returning NaN predictions for {periods} periods."
                )
                return np.full(periods, np.nan)

            # Direct strategy: use pre-trained models
            if self.forecast_strategy == "direct":
                predictions = []

                # We need to maintain current_window for recursive fallback
                # Initialize with history
                current_window = list(history_series.to_numpy())

                # Determine how many steps we can predict directly
                max_direct_horizon = len(self.models)

                for h in range(periods):
                    # Step h is 0-indexed (0 = 1st step, 1 = 2nd step, etc.)

                    # Case 1: Within direct horizon - use specific model
                    if h < max_direct_horizon:
                        # Create features from history
                        lags = history_series.iloc[-self.window_size :].to_numpy()

                        # Add exog if needed
                        if self.exog_cols and exog_future is not None:
                            exog_h = exog_future.iloc[h][self.exog_cols].to_numpy()
                            features = np.concatenate([lags, exog_h])
                        else:
                            features = lags

                        # Predict using the specific model for this horizon
                        pred = self.models[h].predict(features.reshape(1, -1))[0, 0]

                    # Case 2: Beyond direct horizon - fallback to recursive
                    else:
                        # Use the first model (1-step ahead) recursively
                        # Create features from CURRENT window (updated with predictions)
                        lags = np.array(current_window[-self.window_size :])

                        # Add exog if needed
                        if self.exog_cols and exog_future is not None:
                            exog_h = exog_future.iloc[h][self.exog_cols].to_numpy()
                            features = np.concatenate([lags, exog_h])
                        else:
                            features = lags

                        # Predict next step using model[0]
                        pred = self.models[0].predict(features.reshape(1, -1))[0, 0]

                    predictions.append(pred)
                    current_window.append(pred)

                return np.array(predictions)

            # Recursive strategy: iterative predictions
            else:
                predictions = []
                current_window = list(history_series.to_numpy())

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

        raise ValueError(
            "Either x_pred or periods parameter must be provided for prediction."
        )

    def get_forecast_uncertainty(
        self, horizon: int, confidence_level: float = 0.80
    ) -> pd.DataFrame:
        """Get forecast with residual-based prediction intervals.

        Because sklearn regression models have no parametric error distribution,
        this method estimates prediction uncertainty empirically:

        1. Compute in-sample residuals on the training data using the 1-step
           ahead model (``models[0]``).
        2. Use the residual standard deviation as the base prediction error.
        3. Scale the half-interval by ``sqrt(h)`` for horizon step ``h`` to
           simulate how uncertainty accumulates over time.
        4. Apply a z-score corresponding to the requested confidence level.

        The resulting intervals are wider for longer horizons and reflect the
        actual in-sample accuracy of the model.

        Parameters
        ----------
        horizon : int
            Number of future periods to forecast.
        confidence_level : float
            Confidence level (e.g., 0.80 for 80% intervals).

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.

        Raises
        ------
        ValueError
            If the model was trained with exogenous variables.
        """
        if not self.models:
            raise ValueError("Model must be fitted before getting uncertainty.")

        if self.exog_cols:
            raise ValueError(
                f"Cannot generate forecast uncertainty: model was trained with "
                f"exogenous variables {self.exog_cols}. Future exogenous values "
                f"are required but not available. "
                f"Use ForecastFeatureImportance instead."
            )

        # --- Estimate residual std from in-sample 1-step predictions ---
        X_with_lags = self._create_lag_features(self.training_full_series)
        mask = X_with_lags.notna().all(axis=1)
        X_clean = X_with_lags[mask]
        actual_clean = self.training_full_series[mask].to_numpy()

        if len(X_clean) > 0:
            in_sample_preds = self.models[0].predict(X_clean.to_numpy()).flatten()
            residuals = actual_clean - in_sample_preds
            residual_std = float(np.std(residuals))
        else:
            residual_std = 0.0

        # Guard against zero or near-zero std (perfect in-sample fit)
        if residual_std < 1e-10:
            # Fall back to 5% of the mean absolute value of the training series
            residual_std = float(
                np.abs(self.training_full_series.to_numpy()).mean() * 0.05
            )
            residual_std = max(residual_std, 1e-6)

        # --- z-score for the requested confidence level ---
        try:
            from scipy.stats import norm as _norm

            z = float(_norm.ppf(0.5 + confidence_level / 2.0))
        except ImportError:
            # Hardcoded fallback for common levels
            _z_table = {
                0.80: 1.282,
                0.85: 1.440,
                0.90: 1.645,
                0.95: 1.960,
                0.99: 2.576,
            }
            z = _z_table.get(round(confidence_level, 2), 1.645)

        # --- Point forecast ---
        predictions = self.predict(periods=horizon)

        # --- Growing intervals: half-width = z * std * sqrt(h) ---
        horizon_steps = np.arange(1, horizon + 1)
        half_width = z * residual_std * np.sqrt(horizon_steps)

        freq = self.frequency or "D"
        future_dates = pd.date_range(
            start=self.last_timestamp, periods=horizon + 1, freq=freq
        )[1:]

        return pd.DataFrame(
            {
                "ds": future_dates,
                "yhat": predictions,
                "yhat_lower": predictions - half_width,
                "yhat_upper": predictions + half_width,
            }
        )

    def get_forecast_components(self, horizon: int) -> pd.DataFrame:
        """Decompose forecast into trend, seasonal, and residual components.

        Because SklearnMultiStepForecaster is a regression-based model with
        no intrinsic structural decomposition, this method applies STL
        (Seasonal-Trend decomposition using LOESS) to the concatenation of
        the historical training series and the out-of-sample forecast.

        The resulting trend, seasonal, and residual components describe the
        statistical structure of the full series (history + forecast horizon),
        and only the forecast portion is returned.

        Parameters
        ----------
        horizon : int
            Number of future periods to forecast and decompose.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``trend``, ``<seasonality_name>``, ``residual``.

        Raises
        ------
        ValueError
            If the model was trained with exogenous variables.
        """
        if not self.models:
            raise ValueError("Model must be fitted before getting components.")

        if self.exog_cols:
            raise ValueError(
                f"Cannot generate forecast components: model was trained with "
                f"exogenous variables {self.exog_cols}. Future exogenous values "
                f"are required but not available for decomposition. "
                f"Use ForecastFeatureImportance instead."
            )

        try:
            from statsmodels.tsa.seasonal import STL
        except ImportError as exc:
            raise ImportError(
                "statsmodels is required for STL decomposition. "
                "Install with: pip install statsmodels"
            ) from exc

        # Build historical series with a proper DatetimeIndex
        freq = self.frequency or "D"
        historical_values = self.training_full_series.to_numpy()
        n_hist = len(historical_values)

        if self.training_dates is not None:
            historical_index = pd.DatetimeIndex(self.training_dates)
        else:
            # Reconstruct dates ending at last_timestamp
            historical_index = pd.date_range(
                end=self.last_timestamp, periods=n_hist, freq=freq
            )

        historical_series = pd.Series(historical_values, index=historical_index)

        # Out-of-sample forecast
        predictions = self.predict(periods=horizon)
        future_dates = pd.date_range(
            start=self.last_timestamp, periods=horizon + 1, freq=freq
        )[1:]
        future_series = pd.Series(predictions, index=future_dates)

        # Combine history + forecast
        combined = pd.concat([historical_series, future_series])

        # Determine period and run STL decomposition
        period = self._get_seasonal_period()
        component_name = self._period_to_seasonality_name(period)

        n = len(combined)
        if period >= 2 and n >= 2 * period:
            try:
                stl = STL(combined, period=period, robust=True)
                result = stl.fit()
                trend_vals = result.trend
                seasonal_vals = result.seasonal
                residual_vals = result.resid
            except Exception:
                window = min(period, max(2, n // 2))
                trend_vals = combined.rolling(
                    window=window, center=True, min_periods=1
                ).mean()
                seasonal_vals = pd.Series(np.zeros(n), index=combined.index)
                residual_vals = combined - trend_vals
        else:
            window = max(2, min(period, n // 2))
            trend_vals = combined.rolling(
                window=window, center=True, min_periods=1
            ).mean()
            seasonal_vals = pd.Series(np.zeros(n), index=combined.index)
            residual_vals = combined - trend_vals

        return pd.DataFrame(
            {
                "ds": combined.index[-horizon:],
                "trend": trend_vals.to_numpy()[-horizon:],
                component_name: seasonal_vals.to_numpy()[-horizon:],
                "residual": residual_vals.to_numpy()[-horizon:],
            }
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
            "training_full_series": self.training_full_series,
            "training_full_exog": self.training_full_exog,
            "training_dates": getattr(self, "training_dates", None),
            "exog_cols": self.exog_cols,
            "timestamp_col": self.timestamp_col,
            "target_col": self.target_col,
            "frequency": self.frequency,
            "max_horizon": self.max_horizon,
            "last_timestamp": self.last_timestamp,
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
        self.training_full_series = model_state.get("training_full_series")
        self.training_full_exog = model_state.get("training_full_exog")
        self.training_dates = model_state.get("training_dates")
        self.exog_cols = model_state["exog_cols"]
        self.timestamp_col = model_state.get("timestamp_col")
        self.target_col = model_state.get("target_col")
        self.frequency = model_state.get("frequency")
        self.max_horizon = model_state.get("max_horizon", 1)
        self.last_timestamp = model_state.get("last_timestamp")

        config = model_state["config"]
        for key, value in config.items():
            setattr(self, key, value)

        print(f"✅ SklearnMultiStepForecaster loaded from {filename}")
        return self
