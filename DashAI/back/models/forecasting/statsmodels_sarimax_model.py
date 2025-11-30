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
        placeholder=1,
        description="Order of seasonal autoregressive component. "
        "Seasonal lag observations.",
    ) = 1  # type: ignore

    D: schema_field(
        int_field(ge=0, le=2),
        placeholder=1,
        description="Degree of seasonal differencing. Seasonal differencing order.",
    ) = 1  # type: ignore

    Q: schema_field(
        int_field(ge=0, le=5),
        placeholder=1,
        description="Order of seasonal moving average component. "
        "Seasonal moving average window.",
    ) = 1  # type: ignore

    s: schema_field(
        int_field(ge=1, le=365),
        placeholder=12,
        description="Seasonal period (number of observations per cycle). "
        "12=monthly, 4=quarterly, 7=weekly, 365=daily with yearly seasonality.",
    ) = 12  # type: ignore

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
        P: int = 1,  # noqa: N803
        D: int = 1,  # noqa: N803
        Q: int = 1,  # noqa: N803
        s: int = 12,
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

        # Fit SARIMAX model
        self.model = SARIMAX(
            endog=endog_series,
            exog=exog,
            order=self.order,
            seasonal_order=self.seasonal_order,
            trend=self.trend,
            enforce_stationarity=self.enforce_stationarity,
            enforce_invertibility=self.enforce_invertibility,
        )

        self.model_fit = self.model.fit(disp=False)

        print("✅ SARIMAX model training completed")
        print(f"[StatsmodelsSARIMAXModel] AIC: {self.model_fit.aic:.2f}")
        print(f"[StatsmodelsSARIMAXModel] BIC: {self.model_fit.bic:.2f}")

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

            # Get in-sample predictions
            start_idx = 0
            end_idx = len(dates) - 1

            predictions = self.model_fit.predict(
                start=start_idx, end=end_idx, exog=exog
            )

            return predictions.to_numpy()

        raise ValueError(
            "SARIMAX predict requires either 'x_pred' data or a 'periods' value."
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
