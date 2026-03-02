"""Prophet model wrapper for DashAI forecasting.

This model wraps Facebook Prophet for native time series forecasting
with automatic seasonality detection and holiday effects.
"""

import os
import pickle
from typing import Any, Optional, Union

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
from DashAI.back.models.forecasting.base_forecasting_model import ForecastingModel


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
        enum_field(enum=["linear", "logistic", "flat"]),
        placeholder="linear",
        description="Growth model. 'linear' for unlimited growth, "
        "'logistic' for growth that saturates at a carrying capacity "
        "(requires cap_multiplier), 'flat' for no trend.",
    ) = "linear"  # type: ignore

    cap_multiplier: schema_field(
        float_field(ge=1.0, le=10.0),
        placeholder=1.5,
        description="For logistic growth: multiplier applied to max(y) to set "
        "the carrying capacity. E.g., 1.5 means cap = 1.5 * max(y). "
        "Only used when growth='logistic'.",
    ) = 1.5  # type: ignore

    floor_ratio: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.0,
        description="For logistic growth: floor as ratio of min(y). "
        "E.g., 0.5 means floor = 0.5 * min(y). "
        "Only used when growth='logistic'.",
    ) = 0.0  # type: ignore

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


class ProphetModel(ForecastingModel):
    """Prophet forecasting model wrapper for DashAI.

    This model implements the ForecastingModel interface, handling all
    column name conversions internally. It maintains exogenous variables in
    their original format and converts to Prophet's 'ds'/'y' convention only
    during internal operations.
    """

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
        cap_multiplier: float = 1.5,
        floor_ratio: float = 0.0,
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        interval_width: float = 0.8,
        uncertainty_samples: int = 1000,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)  # Pass kwargs to ForecastingModel

        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = self._parse_bool_setting(yearly_seasonality)
        self.weekly_seasonality = self._parse_bool_setting(weekly_seasonality)
        self.daily_seasonality = self._parse_bool_setting(daily_seasonality)
        self.growth = growth
        self.cap_multiplier = cap_multiplier
        self.floor_ratio = floor_ratio
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.interval_width = interval_width
        self.uncertainty_samples = uncertainty_samples

        # Store cap/floor for predictions when using logistic growth
        self._cap_value: Optional[float] = None
        self._floor_value: Optional[float] = None

        self.model = None
        # exog_cols, timestamp_col, target_col are inherited from ForecastingModel
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
            Input features (must contain a timestamp column)
        y : DashAIDataset
            Target values (must contain a numeric column)

        Raises
        ------
        ValueError
            If data is not suitable for Prophet
        """
        x_cols = set(x.column_names)
        y_cols = set(y.column_names)

        if len(x_cols) == 0:
            raise ValueError(
                "Prophet requires at least one input column (timestamp). "
                "Received empty dataset."
            )

        if len(y_cols) != 1:
            raise ValueError(
                f"Prophet requires exactly one target column. "
                f"Received {len(y_cols)} columns: {list(y_cols)}"
            )

    def fit(
        self,
        x_train: DashAIDataset,
        y: DashAIDataset,
        temporal_metadata: dict = None,
        **fit_params,
    ) -> "ProphetModel":
        """Train Prophet forecasting model.

        Implements ForecastingModel.fit() interface. Handles all column name
        conversions internally - stores original names in base class attributes,
        converts to Prophet's 'ds'/'y' convention only for internal use.

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
            If not provided, will attempt auto-detection (legacy behavior)
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

        # Get column information from metadata (task-agnostic approach)
        if temporal_metadata:
            timestamp_col = temporal_metadata.get("timestamp_col")
            target_col = temporal_metadata.get("target_col")
            exog_cols_from_task = temporal_metadata.get("exog_cols", [])
            frequency = temporal_metadata.get("frequency", "D")

            print("[ProphetModel] Using temporal metadata from task:")
            print(f"  - Timestamp: '{timestamp_col}'")
            print(f"  - Target: '{target_col}'")
            print(f"  - Frequency: {frequency}")
            if exog_cols_from_task:
                print(f"  - Exogenous variables: {exog_cols_from_task}")
        else:
            # Legacy: auto-detection if no metadata provided
            print(
                "[ProphetModel] ⚠️ No temporal_metadata provided, using auto-detection"
            )

            # Get target column name (should be single column)
            target_col = y_df.columns[0]

            # Auto-detect timestamp column in x_df
            timestamp_col = None
            for col in x_df.columns:
                try:
                    pd.to_datetime(x_df[col])
                    timestamp_col = col
                    print(f"[ProphetModel] Detected timestamp column: '{col}'")
                    break
                except Exception:
                    continue

            if timestamp_col is None:
                raise ValueError(
                    f"No timestamp column found in input data. "
                    f"Available columns: {list(x_df.columns)}"
                )

            exog_cols_from_task = []
            frequency = fit_params.get("frequency", "D")

        # Store original column names in base class attributes
        self.timestamp_col = timestamp_col
        self.target_col = target_col
        self.frequency = frequency

        # Build Prophet dataframe (internal conversion to 'ds'/'y')
        prophet_df = pd.DataFrame()
        prophet_df["ds"] = pd.to_datetime(x_df[timestamp_col])

        # Check if target column is in x_train (user might have included it by mistake)
        target_in_inputs = target_col in x_df.columns

        if target_in_inputs:
            # Target is in inputs - use it from there for consistency
            print(
                "[ProphetModel] ℹ️  Target '{}' found in inputs - using it "
                "from there".format(target_col)
            )
            prophet_df["y"] = x_df[target_col]
        else:
            # Target is only in y - normal case
            prophet_df["y"] = y_df[target_col]

        # Add exogenous variables (columns that are not timestamp and are numeric)
        # Exclude timestamp and target columns, and only include numeric columns
        # Store in ORIGINAL format (as per BaseForecastingModel contract)
        self.exog_cols = []
        for col in x_df.columns:
            if col == timestamp_col:
                continue  # Skip timestamp
            if col == target_col:
                # Skip target - don't use it as exogenous variable
                if target_in_inputs:
                    print(
                        "[ProphetModel] ℹ️  Excluding target '{}' from exogenous "
                        "variables".format(col)
                    )
                continue

            # Only add numeric columns
            if pd.api.types.is_numeric_dtype(x_df[col]):
                self.exog_cols.append(col)  # Store ORIGINAL name
                prophet_df[col] = x_df[col]
            else:
                print(
                    "[ProphetModel] ⚠️  Skipping non-numeric column: '{}' "
                    "(type: {})".format(col, x_df[col].dtype)
                )

        # Handle logistic growth - requires 'cap' (and optionally 'floor') columns
        if self.growth == "logistic":
            y_max = prophet_df["y"].max()
            y_min = prophet_df["y"].min()

            # Calculate cap and floor based on multipliers
            self._cap_value = y_max * self.cap_multiplier
            self._floor_value = y_min * self.floor_ratio

            # Add cap column (required for logistic growth)
            prophet_df["cap"] = self._cap_value

            # Add floor column if floor_ratio > 0
            if self.floor_ratio > 0:
                prophet_df["floor"] = self._floor_value

            print(
                f"[ProphetModel] Logistic growth: cap={self._cap_value:.2f} "
                f"(max*{self.cap_multiplier}), floor={self._floor_value:.2f}"
            )

        # Store additional metadata
        self.last_ds = prophet_df["ds"].max()

        print(f"[ProphetModel] Training with {len(prophet_df)} data points")
        print(
            f"[ProphetModel] Date range: {prophet_df['ds'].min()} to "
            f"{prophet_df['ds'].max()}"
        )
        if self.exog_cols:
            print(f"[ProphetModel] Exogenous variables: {self.exog_cols}")

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

        # Add exogenous regressors to Prophet (using original names)
        for col in self.exog_cols:
            self.model.add_regressor(col)

        self.model.fit(prophet_df)

        print("✅ Prophet model training completed")
        return self

    def _add_cap_floor_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Add cap and floor columns for logistic growth predictions.

        Parameters
        ----------
        dataframe : pd.DataFrame
            DataFrame to add cap/floor columns to

        Returns
        -------
        pd.DataFrame
            DataFrame with cap (and optionally floor) columns added
        """
        if self.growth != "logistic":
            return dataframe

        result_df = dataframe.copy()

        if self._cap_value is not None:
            result_df["cap"] = self._cap_value

        if self._floor_value is not None and self.floor_ratio > 0:
            result_df["floor"] = self._floor_value

        return result_df

    def predict(
        self,
        x_pred: Optional[Any] = None,
        periods: Optional[int] = None,
        horizon: Optional[int] = None,
        exog_future: Optional[pd.DataFrame] = None,
        return_components: bool = False,
        **kwargs,
    ) -> Union[np.ndarray, pd.DataFrame]:
        if self.model is None:
            raise ValueError("Prophet model is not fitted yet. Call fit() first.")

        def _extract_predictions(
            forecast_df: pd.DataFrame, requested_ds: pd.Series
        ) -> Union[np.ndarray, pd.DataFrame]:
            """Extract predictions for requested timestamps.

            For timestamps that don't exist in Prophet's forecast (gaps in data),
            returns NaN. These will be filtered out by prepare_to_metric().
            """
            # Normalize both forecast and requested timestamps to ensure matching
            # Prophet internally normalizes dates, so we need to do the same
            forecast_df = forecast_df.copy()
            forecast_df["ds"] = pd.to_datetime(forecast_df["ds"]).dt.normalize()
            requested_ds_normalized = pd.to_datetime(requested_ds).dt.normalize()

            # Debug: Show sample of dates
            print(
                f"[ProphetModel] _extract_predictions: "
                f"forecast has {len(forecast_df)} rows, "
                f"requested {len(requested_ds_normalized)} timestamps"
            )
            print(
                f"[ProphetModel] Forecast dates range: "
                f"{forecast_df['ds'].min()} to {forecast_df['ds'].max()}"
            )
            print(
                f"[ProphetModel] Requested dates range: "
                f"{requested_ds_normalized.min()} to {requested_ds_normalized.max()}"
            )

            aligned = forecast_df.set_index("ds").reindex(requested_ds_normalized)

            # Check for missing predictions
            missing_mask = aligned["yhat"].isna()
            if missing_mask.any():
                missing_count = missing_mask.sum()
                total_count = len(requested_ds)
                print(
                    f"[ProphetModel] ⚠️  {missing_count}/{total_count} timestamps "
                    f"have no predictions (gaps in data). These will be excluded "
                    f"from metrics calculation."
                )
                # Debug: Show which dates are missing
                if missing_count <= 10:
                    missing_dates = requested_ds_normalized[missing_mask.to_numpy()]
                    print(f"[ProphetModel] Missing dates: {list(missing_dates)}")
                else:
                    missing_dates = requested_ds_normalized[missing_mask.to_numpy()]
                    print(
                        f"[ProphetModel] First 5 missing dates: "
                        f"{list(missing_dates[:5])}"
                    )

            if return_components:
                return aligned.reset_index()
            return aligned["yhat"].to_numpy()

        if x_pred is not None:
            if isinstance(x_pred, (int, np.integer)):
                periods = int(x_pred)
            else:
                if isinstance(x_pred, pd.DataFrame):
                    input_df = x_pred.copy()
                else:
                    input_df = to_dashai_dataset(x_pred).to_pandas()

                # Auto-detect timestamp column (try 'ds' first for compatibility)
                timestamp_col = None
                if "ds" in input_df.columns:
                    timestamp_col = "ds"
                else:
                    # Try to find timestamp column
                    for col in input_df.columns:
                        try:
                            pd.to_datetime(input_df[col])
                            timestamp_col = col
                            break
                        except Exception:
                            continue

                if timestamp_col is None:
                    raise ValueError(
                        "Prophet predict requires a timestamp column. "
                        f"Available columns: {list(input_df.columns)}"
                    )

                input_df = input_df.copy()

                # Rename to 'ds' for Prophet
                if timestamp_col != "ds":
                    input_df = input_df.rename(columns={timestamp_col: "ds"})

                # Normalize timestamps to ensure consistent comparison
                input_df["ds"] = pd.to_datetime(input_df["ds"]).dt.normalize()
                input_df = input_df.sort_values("ds").reset_index(drop=True)

                # Check if we need in-sample predictions (for explainability)
                # If any requested date is <= last training date, we need to include
                # historical dates in the prediction
                # Use Prophet's internal history dataframe to get training date range
                if not hasattr(self.model, "history_dates"):
                    raise ValueError(
                        "Prophet model has no training history. "
                        "Ensure the model was fitted before prediction."
                    )
                # Normalize history dates for consistent comparison
                history_dates = pd.Series(self.model.history_dates)
                history_dates_normalized = history_dates.dt.normalize()
                last_train_date = history_dates_normalized.max()
                has_historical = (input_df["ds"] <= last_train_date).any()

                if has_historical:
                    # For in-sample predictions (explainability use case):
                    # Include both historical and future dates
                    # Create a complete dataframe from first training date to last
                    # requested date. This ensures Prophet generates predictions for
                    # all dates including historical ones
                    max_requested_date = input_df["ds"].max()

                    # Use make_future_dataframe but include historical dates
                    future_df = self.model.make_future_dataframe(
                        periods=0,  # Don't extend beyond training
                        freq=self.frequency or "D",
                        include_history=True,  # Include training dates
                    )

                    # Add any future dates beyond training if needed
                    if max_requested_date > last_train_date:
                        additional_periods = pd.date_range(
                            start=last_train_date + pd.Timedelta(days=1),
                            end=max_requested_date,
                            freq=self.frequency or "D",
                        )
                        additional_df = pd.DataFrame({"ds": additional_periods})
                        future_df = pd.concat(
                            [future_df, additional_df], ignore_index=True
                        )

                    # Add exogenous variables if present
                    if self.exog_cols:
                        missing_cols = [
                            col for col in self.exog_cols if col not in input_df.columns
                        ]
                        if missing_cols:
                            raise ValueError(
                                "Missing exogenous columns for prediction: "
                                f"{missing_cols}."
                            )

                        # Merge exogenous data from input_df with future_df
                        # For historical dates, use the provided values
                        future_df = future_df.merge(
                            input_df[["ds"] + self.exog_cols], on="ds", how="left"
                        )

                        # Check if there are missing exogenous values
                        if future_df[self.exog_cols].isna().any().any():
                            raise ValueError(
                                "Missing exogenous values for some dates. "
                                "All dates in prediction range must have "
                                "exogenous data."
                            )
                else:
                    # Normal future forecasting (original behavior)
                    future_df = input_df[["ds"]].copy()

                    if self.exog_cols:
                        missing_cols = [
                            col for col in self.exog_cols if col not in input_df.columns
                        ]
                        if missing_cols:
                            raise ValueError(
                                "Missing exogenous columns for prediction: "
                                f"{missing_cols}."
                            )
                        future_df = pd.concat(
                            [
                                future_df,
                                input_df[self.exog_cols].reset_index(drop=True),
                            ],
                            axis=1,
                        )

                # Add cap/floor for logistic growth
                future_df = self._add_cap_floor_columns(future_df)

                # Debug: Log what we're predicting
                print(
                    f"[ProphetModel] Predicting for {len(future_df)} dates: "
                    f"{future_df['ds'].min()} to {future_df['ds'].max()}"
                )
                print(f"[ProphetModel] has_historical={has_historical}")

                forecast = self.model.predict(future_df)

                # Debug: Log what Prophet returned
                print(
                    f"[ProphetModel] Prophet returned {len(forecast)} predictions: "
                    f"{forecast['ds'].min()} to {forecast['ds'].max()}"
                )

                return _extract_predictions(forecast, input_df["ds"])

        # Handle periods/horizon compatibility
        if periods is None and horizon is not None:
            periods = horizon

        if periods is None:
            raise ValueError(
                "Prophet predict requires either 'x_pred' data or a 'periods' value."
            )
        if periods <= 0:
            raise ValueError("Prediction horizon must be a positive integer.")

        frequency = self.frequency or "D"

        # If x_pred is provided with periods, use it to determine start date
        start_date = None
        if x_pred is not None:
            if isinstance(x_pred, pd.DataFrame):
                input_df = x_pred.copy()
            else:
                input_df = to_dashai_dataset(x_pred).to_pandas()

            # Find timestamp column
            ts_col = None
            if "ds" in input_df.columns:
                ts_col = "ds"
            elif self.timestamp_col in input_df.columns:
                ts_col = self.timestamp_col

            if ts_col:
                start_date = pd.to_datetime(input_df[ts_col]).max()
                print(f"[ProphetModel] Using input as start date: {start_date}")

                # Also update last_ds for explainers
                self.last_ds = start_date

        if start_date:
            # Generate future dataframe starting after start_date
            future_dates = pd.date_range(
                start=start_date, periods=periods + 1, freq=frequency
            )[1:]
            future_df = pd.DataFrame({"ds": future_dates})
        else:
            # Standard behavior (continue from training)
            future_df = self.model.make_future_dataframe(
                periods=periods, freq=frequency
            )

        if self.exog_cols and exog_future is not None:
            missing_cols = [
                col for col in self.exog_cols if col not in exog_future.columns
            ]
            if missing_cols:
                raise ValueError(
                    f"Missing exogenous columns for future prediction: {missing_cols}."
                )
            if len(exog_future) != periods:
                raise ValueError(
                    "Missing exogenous values must match the prediction horizon length."
                )
            for col in self.exog_cols:
                future_df[col] = exog_future[col].to_numpy()
        elif self.exog_cols:
            raise ValueError(
                f"Future exogenous values required for columns: {self.exog_cols}."
            )

        # Add cap/floor for logistic growth
        future_df = self._add_cap_floor_columns(future_df)
        forecast = self.model.predict(future_df)
        print(f"[ProphetModel] Generated forecast for {periods} periods")
        print(
            "[ProphetModel] Forecast range: "
            f"{forecast['ds'].iloc[-periods:].min()} to "
            f"{forecast['ds'].iloc[-periods:].max()}"
        )

        if return_components:
            return forecast.tail(periods)
        return forecast["yhat"].tail(periods).to_numpy()

    def get_forecast_components(self, horizon: int) -> pd.DataFrame:
        """Get forecast decomposition (trend, seasonality, etc.).

        Note: This method requires making future predictions. If the model
        was trained with exogenous variables, this will fail unless future
        values for those variables are provided.

        Parameters
        ----------
        horizon : int
            Number of periods to forecast

        Returns
        -------
        pd.DataFrame
            Forecast components (trend, seasonal, etc.)

        Raises
        ------
        ValueError
            If model was trained with exogenous variables (cannot forecast
            without future exogenous values)
        """
        if self.model is None:
            raise ValueError("Model must be fitted before getting components")

        if self.exog_cols:
            # Model uses exogenous variables - cannot make valid forecast
            raise ValueError(
                f"Cannot generate forecast components: model was trained with "
                f"exogenous variables {self.exog_cols}.\n"
                f"Future forecasting requires known future values for these variables, "
                f"which are not available.\n"
                f"Recommendation: For models with exogenous variables, use "
                f"ForecastFeatureImportance explainer instead."
            )

        # No exogenous variables - can make simple forecast
        future_df = self.model.make_future_dataframe(
            periods=horizon, freq=self.frequency or "D"
        )
        # Add cap/floor for logistic growth
        future_df = self._add_cap_floor_columns(future_df)
        forecast = self.model.predict(future_df)

        # Return components for the forecast period
        component_cols = ["ds", "trend", "seasonal", "weekly", "yearly"]
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
            # Base class attributes (original column names)
            "exog_cols": self.exog_cols,
            "timestamp_col": self.timestamp_col,
            "target_col": self.target_col,
            # Prophet-specific metadata
            "last_ds": self.last_ds,
            "frequency": self.frequency,
            # Logistic growth parameters
            "_cap_value": self._cap_value,
            "_floor_value": self._floor_value,
            "cap_multiplier": self.cap_multiplier,
            "floor_ratio": self.floor_ratio,
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

        # Restore base class attributes (original column names)
        self.exog_cols = model_state["exog_cols"]
        self.timestamp_col = model_state.get(
            "timestamp_col"
        )  # May not exist in old models
        self.target_col = model_state.get("target_col")  # May not exist in old models

        # Restore Prophet-specific metadata
        self.last_ds = model_state["last_ds"]
        self.frequency = model_state["frequency"]

        # Restore logistic growth parameters (may not exist in old models)
        self._cap_value = model_state.get("_cap_value")
        self._floor_value = model_state.get("_floor_value")
        self.cap_multiplier = model_state.get("cap_multiplier", 1.5)
        self.floor_ratio = model_state.get("floor_ratio", 0.0)

        # Restore configuration
        config = model_state["config"]
        for key, value in config.items():
            setattr(self, key, value)

        print(f"✅ Prophet model loaded from {filename}")
        return self
