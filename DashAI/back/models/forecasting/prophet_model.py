"""Prophet model wrapper for DashAI forecasting.

This model wraps Facebook Prophet for native time series forecasting
with automatic seasonality detection and holiday effects.
"""

import os
import pickle
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.models.base_model import BaseModel


class ProphetModelSchema(BaseSchema):
    """Schema for Prophet model configuration.

    Prophet is a forecasting procedure designed for business time series data.
    It works best with time series that have strong seasonal effects and several
    seasons of historical data. Prophet is robust to missing data and shifts in
    the trend, and typically handles outliers well.
    """

    seasonality_mode: schema_field(
        enum_field(enum=["additive", "multiplicative"]),
        placeholder="additive",
        description="Type of seasonality. 'additive' assumes seasonal effects are "
        "added to the trend. 'multiplicative' assumes seasonal effects are "
        "multiplied by the trend.",
    ) = "additive"  # type: ignore

    yearly_seasonality: schema_field(
        enum_field(enum=["auto", "true", "false"]),
        placeholder="auto",
        description="Yearly seasonality. 'auto' detects automatically, "
        "'true' forces yearly seasonality, 'false' disables it.",
    ) = "auto"  # type: ignore

    weekly_seasonality: schema_field(
        enum_field(enum=["auto", "true", "false"]),
        placeholder="auto",
        description="Weekly seasonality. 'auto' detects automatically, "
        "'true' forces weekly seasonality, 'false' disables it.",
    ) = "auto"  # type: ignore

    daily_seasonality: schema_field(
        enum_field(enum=["auto", "true", "false"]),
        placeholder="auto",
        description="Daily seasonality. 'auto' detects automatically, "
        "'true' forces daily seasonality, 'false' disables it.",
    ) = "auto"  # type: ignore

    growth: schema_field(
        enum_field(enum=["linear", "logistic"]),
        placeholder="linear",
        description="Growth model. 'linear' for unlimited growth, "
        "'logistic' for growth that saturates at a carrying capacity.",
    ) = "linear"  # type: ignore

    changepoint_prior_scale: schema_field(
        float_field(ge=0.001, le=1.0),
        placeholder=0.05,
        description="Controls flexibility of automatic changepoint selection. "
        "Higher values allow more changepoints (more flexible trend). "
        "Lower values result in fewer changepoints (more conservative trend).",
    ) = 0.05  # type: ignore

    seasonality_prior_scale: schema_field(
        float_field(ge=0.01, le=100.0),
        placeholder=10.0,
        description="Controls flexibility of seasonality. Higher values allow "
        "more seasonal variation. Lower values result in smoother seasonality.",
    ) = 10.0  # type: ignore

    holidays_prior_scale: schema_field(
        float_field(ge=0.01, le=100.0),
        placeholder=10.0,
        description="Controls flexibility of holiday effects. Higher values "
        "allow larger holiday effects.",
    ) = 10.0  # type: ignore

    interval_width: schema_field(
        float_field(ge=0.5, le=0.99),
        placeholder=0.8,
        description="Width of prediction intervals. 0.8 means 80% confidence "
        "intervals. Prophet will generate yhat_lower and yhat_upper bounds.",
    ) = 0.8  # type: ignore

    uncertainty_samples: schema_field(
        int_field(ge=100, le=10000),
        placeholder=1000,
        description="Number of samples to draw for uncertainty estimation. "
        "More samples give smoother intervals but slower prediction.",
    ) = 1000  # type: ignore


class ProphetModel(BaseModel):
    """Prophet forecasting model wrapper for DashAI."""

    SCHEMA = ProphetModelSchema
    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    _task_type = "ForecastingTask"

    def __init__(
        self,
        seasonality_mode: str = "additive",
        yearly_seasonality: str = "auto",
        weekly_seasonality: str = "auto",
        daily_seasonality: str = "auto",
        growth: str = "linear",
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        interval_width: float = 0.8,
        uncertainty_samples: int = 1000,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = self._parse_bool_setting(yearly_seasonality)
        self.weekly_seasonality = self._parse_bool_setting(weekly_seasonality)
        self.daily_seasonality = self._parse_bool_setting(daily_seasonality)
        self.growth = growth
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.interval_width = interval_width
        self.uncertainty_samples = uncertainty_samples

        self.model = None
        self.exog_cols: List[str] = []
        self.last_ds: Optional[pd.Timestamp] = None
        self.frequency: Optional[str] = None

    def _parse_bool_setting(self, setting: str) -> Union[bool, str]:
        if setting.lower() == "true":
            return True
        if setting.lower() == "false":
            return False
        return "auto"

    def _validate_forecasting_data(self, x: DashAIDataset, y: DashAIDataset) -> None:
        """Validate that data is suitable for Prophet.

        Parameters
        ----------
        X : DashAIDataset
            Input features (should contain 'ds' column)
        y : DashAIDataset
            Target values (should contain 'y' column)

        Raises
        ------
        ValueError
            If data is not suitable for Prophet
        """
        x_cols = set(x.column_names)
        y_cols = set(y.column_names)

        if "ds" not in x_cols:
            raise ValueError(
                "Prophet requires 'ds' (timestamp) column in input features. "
                f"Available columns: {list(x_cols)}. "
                "Use ForecastingTask.prepare_for_task() to standardize column names."
            )

        if "y" not in y_cols:
            raise ValueError(
                "Prophet requires 'y' (target) column in target data. "
                f"Available columns: {list(y_cols)}. "
                "Use ForecastingTask.prepare_for_task() to standardize column names."
            )

    def fit(
        self, x_train: DashAIDataset, y: DashAIDataset, **fit_params
    ) -> "ProphetModel":
        """Fit Prophet model to time series data.

        Parameters
        ----------
        x_train : DashAIDataset
            Input features containing 'ds' (datetime) and optional exogenous
            variables
        y : DashAIDataset
            Target time series containing 'y' column
        **fit_params
            Additional fitting parameters

        Returns
        -------
        ProphetModel
            Fitted model instance
        """
        try:
            from prophet import Prophet
        except ImportError as e:
            raise ImportError(
                "Prophet is required for ProphetModel. "
                "Install with: pip install prophet"
            ) from e

        # Validate data format
        self._validate_forecasting_data(x_train, y)

        # Convert to pandas DataFrames
        x_df = x_train.to_pandas()
        y_df = y.to_pandas()

        # Combine x and y for Prophet format
        # Prophet expects DataFrame with 'ds', 'y', and optional regressors
        prophet_df = pd.DataFrame()
        prophet_df["ds"] = pd.to_datetime(x_df["ds"])
        prophet_df["y"] = y_df["y"]

        # Add exogenous variables (additional regressors)
        self.exog_cols = [col for col in x_df.columns if col.startswith("exog_")]
        for col in self.exog_cols:
            prophet_df[col] = x_df[col]

        # Store metadata
        self.last_ds = prophet_df["ds"].max()
        self.frequency = fit_params.get("frequency", "D")

        print(f"[ProphetModel] Training with {len(prophet_df)} data points")
        print(
            f"[ProphetModel] Date range: {prophet_df['ds'].min()} to "
            f"{prophet_df['ds'].max()}"
        )
        print(f"[ProphetModel] Exogenous variables: {len(self.exog_cols)}")

        # Initialize Prophet model
        self.model = Prophet(
            seasonality_mode=self.seasonality_mode,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            growth=self.growth,
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            holidays_prior_scale=self.holidays_prior_scale,
            interval_width=self.interval_width,
            uncertainty_samples=self.uncertainty_samples,
        )

        for col in self.exog_cols:
            self.model.add_regressor(col)

        self.model.fit(prophet_df)

        print("✅ Prophet model training completed")
        return self

    def predict(
        self,
        x_pred: Optional[Any] = None,
        horizon: Optional[int] = None,
        exog_future: Optional[pd.DataFrame] = None,
        return_components: bool = False,
    ) -> Union[np.ndarray, pd.DataFrame]:
        if self.model is None:
            raise ValueError("Prophet model is not fitted yet. Call fit() first.")

        def _extract_predictions(
            forecast_df: pd.DataFrame, requested_ds: pd.Series
        ) -> Union[np.ndarray, pd.DataFrame]:
            aligned = forecast_df.set_index("ds").reindex(requested_ds)
            missing_mask = aligned["yhat"].isna()
            if missing_mask.any():
                missing_dates = aligned.index[missing_mask].unique().tolist()
                raise ValueError(
                    "Unable to obtain predictions for requested timestamps. "
                    f"Missing dates: {missing_dates}"
                )
            if return_components:
                return aligned.reset_index()
            return aligned["yhat"].to_numpy()

        if x_pred is not None:
            if isinstance(x_pred, (int, np.integer)):
                horizon = int(x_pred)
            else:
                if isinstance(x_pred, pd.DataFrame):
                    input_df = x_pred.copy()
                else:
                    input_df = to_dashai_dataset(x_pred).to_pandas()

                if "ds" not in input_df.columns:
                    raise ValueError(
                        "Prophet predict requires a 'ds' column with timestamps."
                    )

                input_df = input_df.copy()
                input_df["ds"] = pd.to_datetime(input_df["ds"])
                input_df = input_df.sort_values("ds").reset_index(drop=True)

                future_df = input_df[["ds"]].copy()

                if self.exog_cols:
                    missing_cols = [
                        col for col in self.exog_cols if col not in input_df.columns
                    ]
                    if missing_cols:
                        raise ValueError(
                            f"Missing exogenous columns for prediction: {missing_cols}."
                        )
                    future_df = pd.concat(
                        [future_df, input_df[self.exog_cols].reset_index(drop=True)],
                        axis=1,
                    )

                forecast = self.model.predict(future_df)
                return _extract_predictions(forecast, future_df["ds"])

        if horizon is None:
            raise ValueError(
                "Prophet predict requires either 'x_pred' data or a 'horizon' value."
            )
        if horizon <= 0:
            raise ValueError("Prediction horizon must be a positive integer.")

        frequency = self.frequency or "D"
        future_df = self.model.make_future_dataframe(periods=horizon, freq=frequency)

        if self.exog_cols and exog_future is not None:
            missing_cols = [
                col for col in self.exog_cols if col not in exog_future.columns
            ]
            if missing_cols:
                raise ValueError(
                    f"Missing exogenous columns for future prediction: {missing_cols}."
                )
            if len(exog_future) != horizon:
                raise ValueError(
                    "Missing exogenous values must match the prediction horizon length."
                )
            for col in self.exog_cols:
                future_df[col] = exog_future[col].to_numpy()
        elif self.exog_cols:
            raise ValueError(
                f"Future exogenous values required for columns: {self.exog_cols}."
            )

        forecast = self.model.predict(future_df)
        print(f"[ProphetModel] Generated forecast for {horizon} periods")
        print(
            "[ProphetModel] Forecast range: "
            f"{forecast['ds'].iloc[-horizon:].min()} to "
            f"{forecast['ds'].iloc[-horizon:].max()}"
        )

        if return_components:
            return forecast.tail(horizon)
        return forecast["yhat"].tail(horizon).to_numpy()

    def get_forecast_components(self, horizon: int) -> pd.DataFrame:
        """Get forecast decomposition (trend, seasonality, etc.).

        Parameters
        ----------
        horizon : int
            Number of periods to forecast

        Returns
        -------
        pd.DataFrame
            Forecast components (trend, seasonal, etc.)
        """
        if self.model is None:
            raise ValueError("Model must be fitted before getting components")

        future_df = self.model.make_future_dataframe(
            periods=horizon, freq=self.frequency
        )
        forecast = self.model.predict(future_df)

        # Return components for the forecast period
        component_cols = ["ds", "trend", "seasonal", "weekly", "yearly"]
        if self.exog_cols:
            component_cols.extend(self.exog_cols)

        available_cols = [col for col in component_cols if col in forecast.columns]
        return forecast[available_cols].iloc[-horizon:]

    def save(self, filename: str) -> None:
        """Save Prophet model to file.

        Parameters
        ----------
        filename : str
            Path to save the model
        """
        model_state = {
            "model": self.model,
            "exog_cols": self.exog_cols,
            "last_ds": self.last_ds,
            "frequency": self.frequency,
            "config": {
                "seasonality_mode": self.seasonality_mode,
                "yearly_seasonality": self.yearly_seasonality,
                "weekly_seasonality": self.weekly_seasonality,
                "daily_seasonality": self.daily_seasonality,
                "growth": self.growth,
                "changepoint_prior_scale": self.changepoint_prior_scale,
                "seasonality_prior_scale": self.seasonality_prior_scale,
                "holidays_prior_scale": self.holidays_prior_scale,
                "interval_width": self.interval_width,
                "uncertainty_samples": self.uncertainty_samples,
            },
        }

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            pickle.dump(model_state, f)

        print(f"✅ Prophet model saved to {filename}")

    def load(self, filename: str) -> "ProphetModel":
        """Load Prophet model from file.

        Parameters
        ----------
        filename : str
            Path to load the model from

        Returns
        -------
        ProphetModel
            Loaded model instance
        """
        with open(filename, "rb") as f:
            model_state = pickle.load(f)

        self.model = model_state["model"]
        self.exog_cols = model_state["exog_cols"]
        self.last_ds = model_state["last_ds"]
        self.frequency = model_state["frequency"]

        # Restore configuration
        config = model_state["config"]
        for key, value in config.items():
            setattr(self, key, value)

        print(f"✅ Prophet model loaded from {filename}")
        return self
