"""Statsmodels SARIMAX model wrapper for DashAI forecasting.

This model wraps statsmodels SARIMAX for seasonal time series forecasting with
autoregressive integrated moving average modeling and exogenous variables.
"""

import os
import pickle
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.models.forecasting.base_forecasting_model import ForecastingModel


class StatsmodelsSARIMAXModelSchema(BaseSchema):
    """Schema for Statsmodels SARIMAX model configuration.

    SARIMAX (Seasonal AutoRegressive Integrated Moving Average with eXogenous
    regressors) extends ARIMA with seasonal components and external variables:
    - (p,d,q): Non-seasonal AR, differencing, MA orders
    - (P,D,Q,s): Seasonal AR, differencing, MA orders and periodicity
    - Exogenous variables: External predictors
    """

    p: schema_field(
        int_field(ge=0, le=10),
        placeholder=1,
        description="Order of non-seasonal autoregressive (AR) component. "
        "Number of lag observations included in the model.",
    ) = 1  # type: ignore

    d: schema_field(
        int_field(ge=0, le=3),
        placeholder=1,
        description="Degree of non-seasonal differencing. Number of times "
        "to difference the data to make it stationary.",
    ) = 1  # type: ignore

    q: schema_field(
        int_field(ge=0, le=10),
        placeholder=1,
        description="Order of non-seasonal moving average (MA) component. "
        "Size of the moving average window.",
    ) = 1  # type: ignore

    P: schema_field(
        int_field(ge=0, le=5),
        placeholder=0,
        description="Order of seasonal autoregressive component. "
        "Seasonal lag observations. Set to 0 to disable seasonality.",
    ) = 0  # type: ignore

    D: schema_field(
        int_field(ge=0, le=2),
        placeholder=0,
        description="Degree of seasonal differencing. Seasonal differencing order. "
        "Set to 0 to disable seasonal differencing.",
    ) = 0  # type: ignore

    Q: schema_field(
        int_field(ge=0, le=5),
        placeholder=0,
        description="Order of seasonal moving average component. "
        "Seasonal moving average window. Set to 0 to disable.",
    ) = 0  # type: ignore

    s: schema_field(
        int_field(ge=1, le=365),
        placeholder=1,
        description="Seasonal period (observations per cycle). "
        "12=monthly, 4=quarterly, 7=weekly. Set to 1 to disable seasonality.",
    ) = 1  # type: ignore

    trend: schema_field(
        enum_field(enum=["n", "c", "t", "ct"]),
        placeholder="n",
        description=(
            "Deterministic trend to include. 'n'=no trend, 'c'=constant, "
            "'t'=linear trend, 'ct'=constant and linear trend. "
            "Note: When d>0 or D>0, 'c' is not allowed (use 't' instead). "
            "When d+D>1, neither 'c' nor 't' are allowed."
        ),
    ) = "n"  # type: ignore

    enforce_stationarity: schema_field(
        bool_field(),
        placeholder=True,
        description=(
            "Whether to enforce stationarity of the autoregressive parameters."
        ),
    ) = True  # type: ignore

    enforce_invertibility: schema_field(
        bool_field(),
        placeholder=True,
        description=(
            "Whether to enforce invertibility of the moving average parameters."
        ),
    ) = True  # type: ignore


class StatsmodelsSARIMAXModel(ForecastingModel):
    """Statsmodels SARIMAX forecasting model wrapper for DashAI.

    This model implements the ForecastingModel interface using statsmodels SARIMAX.
    It handles seasonal patterns, exogenous variables, and column name conversions.
    """

    SCHEMA = StatsmodelsSARIMAXModelSchema
    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    _task_type = "ForecastingTask"

    def __init__(
        self,
        p: int = 1,
        d: int = 1,
        q: int = 1,
        P: int = 0,  # noqa: N803
        D: int = 0,  # noqa: N803
        Q: int = 0,  # noqa: N803
        s: int = 1,
        trend: str = "n",
        enforce_stationarity: bool = True,
        enforce_invertibility: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.p = p
        self.d = d
        self.q = q
        self.P = P
        self.D = D
        self.Q = Q
        self.s = s
        self.trend = trend
        self.enforce_stationarity = enforce_stationarity
        self.enforce_invertibility = enforce_invertibility

        self.order = (p, d, q)
        self.seasonal_order = (P, D, Q, s)

        self.model = None
        self.model_fit = None
        self.frequency: Optional[str] = None

    def _validate_forecasting_data(self, x: DashAIDataset, y: DashAIDataset) -> None:
        """Validate that data is suitable for SARIMAX.

        Parameters
        ----------
        x : DashAIDataset
            Input features (must contain a timestamp column)
        y : DashAIDataset
            Target values (must contain a numeric column)

        Raises
        ------
        ValueError
            If data is not suitable for SARIMAX
        """
        x_cols = set(x.column_names)
        y_cols = set(y.column_names)

        if len(x_cols) == 0:
            raise ValueError(
                "SARIMAX requires at least one input column (timestamp). "
                "Received empty dataset."
            )

        if len(y_cols) != 1:
            raise ValueError(
                f"SARIMAX requires exactly one target column. "
                f"Received {len(y_cols)} columns: {list(y_cols)}"
            )

    def fit(
        self,
        x_train: DashAIDataset,
        y: DashAIDataset,
        temporal_metadata: dict = None,
        **fit_params,
    ) -> "StatsmodelsSARIMAXModel":
        """Train SARIMAX forecasting model.

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
        StatsmodelsSARIMAXModel
            Fitted model instance
        """
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
        except ImportError as e:
            raise ImportError(
                "Statsmodels is required for StatsmodelsSARIMAXModel. "
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

            print("[StatsmodelsSARIMAXModel] Using temporal metadata from task:")
            print(f"  - Timestamp: '{timestamp_col}'")
            print(f"  - Target: '{target_col}'")
            print(f"  - Frequency: {frequency}")
            if exog_cols_from_task:
                print(f"  - Exogenous variables: {exog_cols_from_task}")
        else:
            # Auto-detection if no metadata provided
            print(
                "[StatsmodelsSARIMAXModel] ⚠️ No temporal_metadata provided, "
                "using auto-detection"
            )

            target_col = y_df.columns[0]

            # Auto-detect timestamp column
            timestamp_col = None
            for col in x_df.columns:
                try:
                    pd.to_datetime(x_df[col])
                    timestamp_col = col
                    print(
                        f"[StatsmodelsSARIMAXModel] Detected timestamp column: '{col}'"
                    )
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

        # Prepare data for SARIMAX
        # Create datetime index
        dates = pd.to_datetime(x_df[timestamp_col])

        # Store last training date for forecast generation
        self.last_ds = dates.max()

        # Get target series
        target_in_inputs = target_col in x_df.columns
        if target_in_inputs:
            print(
                "[StatsmodelsSARIMAXModel] ℹ️  Target '{}' found in inputs - "
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
                        "[StatsmodelsSARIMAXModel] ℹ️  Excluding target '{}' from "
                        "exogenous variables".format(col)
                    )
                continue

            # Only add numeric columns
            if pd.api.types.is_numeric_dtype(x_df[col]):
                self.exog_cols.append(col)
            else:
                print(
                    "[StatsmodelsSARIMAXModel] ⚠️  Skipping non-numeric column: '{}' "
                    "(type: {})".format(col, x_df[col].dtype)
                )

        if self.exog_cols:
            exog = x_df[self.exog_cols].to_numpy()
            print(f"[StatsmodelsSARIMAXModel] Exogenous variables: {self.exog_cols}")

        print(
            f"[StatsmodelsSARIMAXModel] Training "
            f"SARIMAX{self.order}x{self.seasonal_order} model"
        )
        print(
            f"[StatsmodelsSARIMAXModel] Training with {len(endog_series)} data points"
        )
        print(f"[StatsmodelsSARIMAXModel] Date range: {dates.min()} to {dates.max()}")

        # Auto-adjust parameters for small datasets
        n_samples = len(endog_series)

        # Check if seasonality is enabled (s>1 and any seasonal param > 0)
        has_seasonality = self.s > 1 and (self.P > 0 or self.D > 0 or self.Q > 0)

        if has_seasonality:
            # SARIMAX needs: s + d + D + max(p, P) + max(q, Q) samples
            min_required = (
                self.s + self.d + self.D + max(self.p, self.P) + max(self.q, self.Q) + 2
            )

            if n_samples < min_required:
                print(
                    f"[StatsmodelsSARIMAXModel] ⚠️  Dataset too small "
                    f"({n_samples} samples) for seasonal params "
                    f"(need {min_required}). Disabling seasonality..."
                )
                # Disable seasonality entirely for small datasets
                self.P = 0
                self.D = 0
                self.Q = 0
                self.s = 1
                has_seasonality = False

        # For non-seasonal ARIMA, check basic requirements
        min_arima_samples = self.p + self.d + self.q + 3
        if n_samples < min_arima_samples:
            print("[StatsmodelsSARIMAXModel] ⚠️  Adjusting ARIMA orders...")
            # Reduce AR/MA orders if needed
            max_order = max(1, (n_samples - self.d - 2) // 2)
            if self.p > max_order:
                old_p = self.p
                self.p = max(0, max_order)
                print(f"  - Reduced p (AR order): {old_p} → {self.p}")
            if self.q > max_order:
                old_q = self.q
                self.q = max(0, max_order)
                print(f"  - Reduced q (MA order): {old_q} → {self.q}")
            if self.d > 1 and n_samples < 10:
                old_d = self.d
                self.d = min(1, self.d)
                print(f"  - Reduced d (differencing): {old_d} → {self.d}")

        self.order = (self.p, self.d, self.q)

        # Set seasonal_order: None if no seasonality, otherwise tuple
        if has_seasonality:
            self.seasonal_order = (self.P, self.D, self.Q, self.s)
            print(
                f"[StatsmodelsSARIMAXModel] Final parameters: "
                f"SARIMAX{self.order}x{self.seasonal_order}"
            )
        else:
            self.seasonal_order = (0, 0, 0, 0)  # Disable seasonality
            print(
                f"[StatsmodelsSARIMAXModel] Final parameters: "
                f"ARIMA{self.order} (no seasonality)"
            )

        # Fit SARIMAX model (use ARIMA when no seasonality for stability)
        try:
            if has_seasonality:
                self.model = SARIMAX(
                    endog=endog_series,
                    exog=exog,
                    order=self.order,
                    seasonal_order=self.seasonal_order,
                    trend=self.trend,
                    enforce_stationarity=self.enforce_stationarity,
                    enforce_invertibility=self.enforce_invertibility,
                )
                self.model_fit = self.model.fit()
            else:
                # Use ARIMA (no seasonal component) for small datasets or when s <= 1
                # SARIMAX doesn't accept seasonal_order with s <= 1
                from statsmodels.tsa.arima.model import ARIMA

                print("[StatsmodelsSARIMAXModel] Using ARIMA (no seasonal component)")
                self.model = ARIMA(
                    endog=endog_series,
                    exog=exog,
                    order=self.order,
                    trend=self.trend,
                    enforce_stationarity=self.enforce_stationarity,
                    enforce_invertibility=self.enforce_invertibility,
                )
                self.model_fit = self.model.fit()

            print("✅ SARIMAX model training completed")
            print(f"[StatsmodelsSARIMAXModel] AIC: {self.model_fit.aic:.2f}")
            print(f"[StatsmodelsSARIMAXModel] BIC: {self.model_fit.bic:.2f}")
        except ValueError as e:
            # Fallback: if SARIMAX fails due to seasonality issues, try ARIMA
            if "Seasonal periodicity" in str(e) or "seasonal" in str(e).lower():
                print(f"[StatsmodelsSARIMAXModel] ⚠️  SARIMAX seasonality error: {e}")
                print("[StatsmodelsSARIMAXModel] Falling back to ARIMA")
                from statsmodels.tsa.arima.model import ARIMA

                self.model = ARIMA(
                    endog=endog_series,
                    exog=exog,
                    order=self.order,
                    trend=self.trend,
                    enforce_stationarity=self.enforce_stationarity,
                    enforce_invertibility=self.enforce_invertibility,
                )
                self.model_fit = self.model.fit()
                self.seasonal_order = (0, 0, 0, 0)
                print("✅ ARIMA model training completed (fallback)")
                print(f"[StatsmodelsSARIMAXModel] AIC: {self.model_fit.aic:.2f}")
                print(f"[StatsmodelsSARIMAXModel] BIC: {self.model_fit.bic:.2f}")
            else:
                print(f"[StatsmodelsSARIMAXModel] ❌ Training failed: {e}")
                raise
        except Exception as e:
            print(f"[StatsmodelsSARIMAXModel] ❌ Training failed: {e}")
            raise

        return self

    def predict(
        self,
        x_pred: Optional[Any] = None,
        periods: Optional[int] = None,
        exog_future: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> Union[np.ndarray, pd.DataFrame]:
        """Generate forecasts using SARIMAX model.

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
            raise ValueError("SARIMAX model is not fitted yet. Call fit() first.")

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

            print(f"[StatsmodelsSARIMAXModel] Generated forecast for {periods} periods")
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
                    "SARIMAX predict requires a timestamp column. "
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
            print(
                f"[StatsmodelsSARIMAXModel] In-sample prediction: {len(dates)} points "
                f"({dates.min()} to {dates.max()})"
            )

            predictions = self.model_fit.predict(
                start=dates.iloc[0], end=dates.iloc[-1], exog=exog
            )

            print(f"[StatsmodelsSARIMAXModel] Generated {len(predictions)} predictions")

            return predictions.to_numpy()

        raise ValueError(
            "SARIMAX predict requires either 'x_pred' data or a 'periods' value."
        )

    def get_forecast_uncertainty(
        self, horizon: int, confidence_level: float = 0.80
    ) -> pd.DataFrame:
        """Get forecast with parametric confidence intervals from SARIMAX.

        Uses statsmodels ``get_forecast().summary_frame()`` to compute
        analytical confidence intervals derived from the model's error
        distribution. These are true parametric intervals that reflect both
        the non-seasonal and seasonal uncertainty of the model.

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

        When a seasonal order was configured (``s > 1``), the explicit
        seasonal period ``s`` is used for STL so the decomposition reflects
        the model's actual seasonal structure. Otherwise the period is
        inferred from the stored frequency.

        Parameters
        ----------
        horizon : int
            Number of future periods to forecast and decompose.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``trend``, ``<seasonality_name>``, ``residual``.
            The seasonality column name depends on the period (e.g. ``weekly``
            for s=7, ``yearly`` for s=12).

        Raises
        ------
        ValueError
            If the model was trained with exogenous variables.
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

        # Combine history + forecast
        combined = pd.concat([fitted, future_series])

        # Use explicit seasonal period s when seasonality is active;
        # otherwise infer from frequency
        explicit_s = (
            self.seasonal_order[3]
            if hasattr(self, "seasonal_order") and self.seasonal_order[3] > 1
            else None
        )
        period = explicit_s if explicit_s else self._get_seasonal_period()
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
        """Save SARIMAX model to file.

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
                "P": self.P,
                "D": self.D,
                "Q": self.Q,
                "s": self.s,
                "trend": self.trend,
                "order": self.order,
                "seasonal_order": self.seasonal_order,
                "enforce_stationarity": self.enforce_stationarity,
                "enforce_invertibility": self.enforce_invertibility,
            },
        }

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            pickle.dump(model_state, f)

        print(f"✅ SARIMAX model saved to {filename}")

    def load(self, filename: str) -> "StatsmodelsSARIMAXModel":
        """Load SARIMAX model from file.

        Parameters
        ----------
        filename : str
            Path to load the model from

        Returns
        -------
        StatsmodelsSARIMAXModel
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

        print(f"✅ SARIMAX model loaded from {filename}")
        return self
