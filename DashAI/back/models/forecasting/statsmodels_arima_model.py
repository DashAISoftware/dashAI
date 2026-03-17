"""Statsmodels ARIMA model wrapper for DashAI forecasting.

This model wraps statsmodels ARIMA for time series forecasting with
autoregressive integrated moving average modeling.
"""

import os
import pickle
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.models.forecasting.base_forecasting_model import ForecastingModel


class StatsmodelsARIMAModelSchema(BaseSchema):
    """Schema for Statsmodels ARIMA model configuration.

    ARIMA (AutoRegressive Integrated Moving Average) is a forecasting method
    that captures different aspects of time series:
    - AR (p): Autoregression - uses past values
    - I (d): Integration - differencing to make series stationary
    - MA (q): Moving Average - uses past forecast errors
    """

    p: schema_field(
        int_field(ge=0, le=10),
        placeholder=1,
        description="Order of autoregressive (AR) component. Number of lag "
        "observations included in the model (how many past values to use).",
    ) = 1  # type: ignore

    d: schema_field(
        int_field(ge=0, le=3),
        placeholder=1,
        description="Degree of differencing (I component). Number of times "
        "to difference the data to make it stationary. 0=stationary, "
        "1=first difference, 2=second difference.",
    ) = 1  # type: ignore

    q: schema_field(
        int_field(ge=0, le=10),
        placeholder=1,
        description="Order of moving average (MA) component. Size of the "
        "moving average window (how many past forecast errors to use).",
    ) = 1  # type: ignore

    trend: schema_field(
        enum_field(enum=["n", "c", "t", "ct"]),
        placeholder="n",
        description=(
            "Deterministic trend to include. 'n'=no trend, 'c'=constant "
            "(level), 't'=linear trend, 'ct'=constant and linear trend. "
            "Note: When d>0, 'c' is not allowed (use 't' instead). "
            "When d>1, neither 'c' nor 't' are allowed."
        ),
    ) = "n"  # type: ignore


class StatsmodelsARIMAModel(ForecastingModel):
    """Statsmodels ARIMA forecasting model wrapper for DashAI.

    This model implements the ForecastingModel interface using statsmodels ARIMA.
    It handles column name conversions internally and supports exogenous variables.
    """

    SCHEMA = StatsmodelsARIMAModelSchema
    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    _task_type = "ForecastingTask"

    def __init__(
        self,
        p: int = 1,
        d: int = 1,
        q: int = 1,
        trend: str = "n",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.p = p
        self.d = d
        self.q = q
        self.trend = trend
        self.order = (p, d, q)

        self.model = None
        self.model_fit = None
        self.frequency: Optional[str] = None

    def _validate_forecasting_data(self, x: DashAIDataset, y: DashAIDataset) -> None:
        """Validate that data is suitable for ARIMA.

        Parameters
        ----------
        x : DashAIDataset
            Input features (must contain a timestamp column)
        y : DashAIDataset
            Target values (must contain a numeric column)

        Raises
        ------
        ValueError
            If data is not suitable for ARIMA
        """
        x_cols = set(x.column_names)
        y_cols = set(y.column_names)

        if len(x_cols) == 0:
            raise ValueError(
                "ARIMA requires at least one input column (timestamp). "
                "Received empty dataset."
            )

        if len(y_cols) != 1:
            raise ValueError(
                f"ARIMA requires exactly one target column. "
                f"Received {len(y_cols)} columns: {list(y_cols)}"
            )

    def fit(
        self,
        x_train: DashAIDataset,
        y: DashAIDataset,
        temporal_metadata: dict = None,
        **fit_params,
    ) -> "StatsmodelsARIMAModel":
        """Train ARIMA forecasting model.

        Parameters
        ----------
        x_train : DashAIDataset
            Input features containing timestamp and optional exogenous variables
        y : DashAIDataset
            Target time series (single column)
        temporal_metadata : dict, optional
            Metadata from ForecastingTask containing:
            - timestamp_col: name of timestamp column
            - target_col: name of target column
            - exog_cols: list of exogenous variable column names
            - frequency: time series frequency
        **fit_params
            Additional fitting parameters

        Returns
        -------
        StatsmodelsARIMAModel
            Fitted model instance
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
        except ImportError as e:
            raise ImportError(
                "Statsmodels is required for StatsmodelsARIMAModel. "
                "Install with: pip install statsmodels"
            ) from e

        # Validate data format
        self._validate_forecasting_data(x_train, y)

        # Convert to pandas DataFrames
        x_df = x_train.to_pandas()
        y_df = y.to_pandas()

        # Get column information from metadata
        if temporal_metadata:
            timestamp_col = temporal_metadata.get("timestamp_col")
            target_col = temporal_metadata.get("target_col")
            exog_cols_from_task = temporal_metadata.get("exog_cols", [])
            frequency = temporal_metadata.get("frequency")

            print("[StatsmodelsARIMAModel] Using temporal metadata from task:")
            print(f"  - Timestamp: '{timestamp_col}'")
            print(f"  - Target: '{target_col}'")
            print(f"  - Frequency: {frequency}")
            if exog_cols_from_task:
                print(f"  - Exogenous variables: {exog_cols_from_task}")
        else:
            # Auto-detection if no metadata provided
            print(
                "[StatsmodelsARIMAModel] ⚠️ No temporal_metadata provided, "
                "using auto-detection"
            )

            target_col = y_df.columns[0]

            # Auto-detect timestamp column
            timestamp_col = None
            for col in x_df.columns:
                try:
                    pd.to_datetime(x_df[col])
                    timestamp_col = col
                    print(f"[StatsmodelsARIMAModel] Detected timestamp column: '{col}'")
                    break
                except Exception:
                    continue

            if timestamp_col is None:
                raise ValueError(
                    f"No timestamp column found in input data. "
                    f"Available columns: {list(x_df.columns)}"
                )

            exog_cols_from_task = []
            frequency = fit_params.get("frequency")

        # Store original column names
        self.timestamp_col = timestamp_col
        self.target_col = target_col
        self.frequency = frequency

        # Prepare data for ARIMA
        # Create datetime index
        dates = pd.to_datetime(x_df[timestamp_col])

        # Store last training date for forecast generation
        self.last_ds = dates.max()

        # Get target series
        target_in_inputs = target_col in x_df.columns
        if target_in_inputs:
            print(
                "[StatsmodelsARIMAModel] ℹ️  Target '{}' found in inputs - "
                "using it from there".format(target_col)
            )
            endog = x_df[target_col].to_numpy()
        else:
            endog = y_df[target_col].to_numpy()

        # Create time series with datetime index
        endog_series = pd.Series(endog, index=dates)

        # Prepare exogenous variables
        self.exog_cols = []
        exog = None

        for col in x_df.columns:
            if col == timestamp_col:
                continue
            if col == target_col:
                if target_in_inputs:
                    print(
                        "[StatsmodelsARIMAModel] ℹ️  Excluding target '{}' from "
                        "exogenous variables".format(col)
                    )
                continue

            # Only add numeric columns
            if pd.api.types.is_numeric_dtype(x_df[col]):
                self.exog_cols.append(col)
            else:
                print(
                    "[StatsmodelsARIMAModel] ⚠️  Skipping non-numeric column: '{}' "
                    "(type: {})".format(col, x_df[col].dtype)
                )

        if self.exog_cols:
            exog = x_df[self.exog_cols].to_numpy()
            print(f"[StatsmodelsARIMAModel] Exogenous variables: {self.exog_cols}")

        print(f"[StatsmodelsARIMAModel] Training ARIMA{self.order} model")
        print(f"[StatsmodelsARIMAModel] Training with {len(endog_series)} data points")
        print(f"[StatsmodelsARIMAModel] Date range: {dates.min()} to {dates.max()}")

        # Fit ARIMA model
        self.model = ARIMA(
            endog=endog_series,
            exog=exog,
            order=self.order,
            trend=self.trend,
        )

        self.model_fit = self.model.fit()

        print("✅ ARIMA model training completed")
        print(f"[StatsmodelsARIMAModel] AIC: {self.model_fit.aic:.2f}")
        print(f"[StatsmodelsARIMAModel] BIC: {self.model_fit.bic:.2f}")

        return self

    def predict(
        self,
        x_pred: Optional[Any] = None,
        periods: Optional[int] = None,
        exog_future: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> Union[np.ndarray, pd.DataFrame]:
        """Generate forecasts using ARIMA model.

        Parameters
        ----------
        x_pred : pd.DataFrame, optional
            Input data for in-sample predictions containing timestamp and
            exogenous variables (if model uses them)
        periods : int, optional
            Number of future periods to forecast (out-of-sample mode)
        exog_future : pd.DataFrame, optional
            Future values of exogenous variables for out-of-sample forecasting
        **kwargs
            Additional parameters

        Returns
        -------
        np.ndarray or pd.DataFrame
            Predictions array
        """
        if self.model_fit is None:
            raise ValueError("ARIMA model is not fitted yet. Call fit() first.")

        # Handle different input types
        if x_pred is not None and isinstance(x_pred, (int, np.integer)):
            periods = int(x_pred)
            x_pred = None

        # Out-of-sample forecasting
        if periods is not None and x_pred is None:
            if periods <= 0:
                raise ValueError("Prediction horizon must be a positive integer.")

            # Prepare exogenous variables for forecast
            exog = None
            if self.exog_cols:
                if exog_future is None:
                    raise ValueError(
                        f"Future exogenous values required for columns: "
                        f"{self.exog_cols}."
                    )

                missing_cols = [
                    col for col in self.exog_cols if col not in exog_future.columns
                ]
                if missing_cols:
                    raise ValueError(
                        f"Missing exogenous columns for prediction: {missing_cols}."
                    )

                if len(exog_future) != periods:
                    raise ValueError(
                        f"Exogenous data length ({len(exog_future)}) must match "
                        f"prediction horizon ({periods})."
                    )

                exog = exog_future[self.exog_cols].to_numpy()

            # Generate forecast
            forecast = self.model_fit.forecast(steps=periods, exog=exog)

            print(f"[StatsmodelsARIMAModel] Generated forecast for {periods} periods")
            return forecast.to_numpy()

        # In-sample predictions
        if x_pred is not None:
            if isinstance(x_pred, pd.DataFrame):
                input_df = x_pred.copy()
            else:
                input_df = to_dashai_dataset(x_pred).to_pandas()

            # Auto-detect timestamp column
            timestamp_col = None
            for col in input_df.columns:
                try:
                    pd.to_datetime(input_df[col])
                    timestamp_col = col
                    break
                except Exception:
                    continue

            if timestamp_col is None:
                raise ValueError(
                    "ARIMA predict requires a timestamp column. "
                    f"Available columns: {list(input_df.columns)}"
                )

            dates = pd.to_datetime(input_df[timestamp_col])

            # Prepare exogenous variables
            exog = None
            if self.exog_cols:
                missing_cols = [
                    col for col in self.exog_cols if col not in input_df.columns
                ]
                if missing_cols:
                    raise ValueError(
                        f"Missing exogenous columns for prediction: {missing_cols}."
                    )
                exog = input_df[self.exog_cols].to_numpy()

            # Use actual dates so statsmodels predicts the correct period
            # (works for both in-sample and out-of-sample dates)
            predictions = self.model_fit.predict(
                start=dates.iloc[0], end=dates.iloc[-1], exog=exog
            )

            return predictions.to_numpy()

        raise ValueError(
            "ARIMA predict requires either 'x_pred' data or a 'periods' value."
        )

    def get_forecast_uncertainty(
        self, horizon: int, confidence_level: float = 0.80
    ) -> pd.DataFrame:
        """Get forecast with parametric confidence intervals from ARIMA.

        Uses statsmodels ``get_forecast().summary_frame()`` to compute
        analytical confidence intervals derived from the model's error
        distribution. These are true parametric intervals, not estimates.

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
        if self.model_fit is None:
            raise ValueError("Model must be fitted before getting uncertainty.")

        if self.exog_cols:
            raise ValueError(
                f"Cannot generate forecast uncertainty: model was trained with "
                f"exogenous variables {self.exog_cols}. Future exogenous values "
                f"are required but not available. "
                f"Use ForecastFeatureImportance instead."
            )

        alpha = 1.0 - confidence_level
        forecast_obj = self.model_fit.get_forecast(steps=horizon)
        summary = forecast_obj.summary_frame(alpha=alpha)
        # summary columns: mean, mean_se, mean_ci_lower, mean_ci_upper

        freq = self.frequency or "D"
        future_dates = pd.date_range(
            start=self.last_ds, periods=horizon + 1, freq=freq
        )[1:]

        return pd.DataFrame(
            {
                "ds": future_dates,
                "yhat": summary["mean"].to_numpy(),
                "yhat_lower": summary["mean_ci_lower"].to_numpy(),
                "yhat_upper": summary["mean_ci_upper"].to_numpy(),
            }
        )

    def get_forecast_components(self, horizon: int) -> pd.DataFrame:
        """Decompose forecast into trend, seasonal, and residual components.

        Applies STL (Seasonal-Trend decomposition using LOESS) to the
        combination of in-sample fitted values and out-of-sample forecast.
        When there is insufficient data for STL, falls back to a centered
        moving-average trend.

        ARIMA does not model seasonality explicitly, so the seasonal component
        reflects the cyclical pattern extracted from the data by STL.

        Parameters
        ----------
        horizon : int
            Number of future periods to forecast and decompose.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``trend``, ``<seasonality_name>``, ``residual``.
            The seasonality column name is derived from the stored frequency
            (e.g. ``weekly`` for daily data, ``yearly`` for monthly data).

        Raises
        ------
        ValueError
            If the model was trained with exogenous variables (future values
            would be required but are unavailable here).
        """
        if self.model_fit is None:
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
            raise ImportError("statsmodels is required for STL decomposition.") from exc

        # In-sample fitted values (DatetimeIndex from training)
        fitted = self.model_fit.fittedvalues.dropna()

        # Out-of-sample forecast
        freq = self.frequency or "D"
        forecast_result = self.model_fit.forecast(steps=horizon)
        future_dates = pd.date_range(
            start=self.last_ds, periods=horizon + 1, freq=freq
        )[1:]
        future_series = pd.Series(forecast_result.to_numpy(), index=future_dates)

        # Combine history + forecast into one series
        combined = pd.concat([fitted, future_series])

        # Determine period for STL
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
                # Fallback to moving-average trend if STL fails
                window = min(period, max(2, n // 2))
                trend_vals = combined.rolling(
                    window=window, center=True, min_periods=1
                ).mean()
                seasonal_vals = pd.Series(np.zeros(n), index=combined.index)
                residual_vals = combined - trend_vals
        else:
            # Not enough data for STL — use simple moving-average trend
            window = max(2, min(period, n // 2))
            trend_vals = combined.rolling(
                window=window, center=True, min_periods=1
            ).mean()
            seasonal_vals = pd.Series(np.zeros(n), index=combined.index)
            residual_vals = combined - trend_vals

        # Return only the forecast horizon (the future portion)
        return pd.DataFrame(
            {
                "ds": combined.index[-horizon:],
                "trend": trend_vals.to_numpy()[-horizon:],
                component_name: seasonal_vals.to_numpy()[-horizon:],
                "residual": residual_vals.to_numpy()[-horizon:],
            }
        )

    def save(self, filename: str) -> None:
        """Save ARIMA model to file.

        Parameters
        ----------
        filename : str
            Path to save the model
        """
        if self.model_fit is None:
            raise ValueError("Cannot save model before fitting.")

        model_state = {
            "model_fit": self.model_fit,
            "exog_cols": self.exog_cols,
            "timestamp_col": self.timestamp_col,
            "target_col": self.target_col,
            "frequency": self.frequency,
            "last_ds": getattr(self, "last_ds", None),
            "config": {
                "p": self.p,
                "d": self.d,
                "q": self.q,
                "trend": self.trend,
                "order": self.order,
            },
        }

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            pickle.dump(model_state, f)

        print(f"✅ ARIMA model saved to {filename}")

    def load(self, filename: str) -> "StatsmodelsARIMAModel":
        """Load ARIMA model from file.

        Parameters
        ----------
        filename : str
            Path to load the model from

        Returns
        -------
        StatsmodelsARIMAModel
            Loaded model instance
        """
        with open(filename, "rb") as f:
            model_state = pickle.load(f)

        self.model_fit = model_state["model_fit"]
        self.exog_cols = model_state["exog_cols"]
        self.timestamp_col = model_state.get("timestamp_col")
        self.target_col = model_state.get("target_col")
        self.frequency = model_state.get("frequency")
        self.last_ds = model_state.get("last_ds")

        config = model_state["config"]
        for key, value in config.items():
            setattr(self, key, value)

        print(f"✅ ARIMA model loaded from {filename}")
        return self
