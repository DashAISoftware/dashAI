"""Forecast Decomposition Explainer for time series models.

This explainer decomposes forecasts into interpretable components (trend,
seasonality, residual) for any forecasting model that implements
``get_forecast_components()``.

Works with:
- Prophet       → trend, weekly, yearly (native structural decomposition)
- ARIMA         → trend, weekly/yearly, residual  (STL on fitted + forecast)
- SARIMAX       → trend, weekly/yearly, residual  (STL with explicit period s)
- SklearnMultiStep → trend, weekly/yearly, residual (STL on history + forecast)

Any future model that implements ``get_forecast_components(horizon)`` and
returns a DataFrame with at least a ``ds`` column and one component column
will be automatically supported.
"""

from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go
from datasets import DatasetDict
from plotly.subplots import make_subplots

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    int_field,
    schema_field,
)
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.models import BaseModel


class ForecastDecompositionSchema(BaseSchema):
    """Forecast Decomposition breaks down predictions into interpretable components.

    This helps understand what drives the forecast:
    - Trend: Long-term direction
    - Seasonality: Repeating patterns (weekly, yearly, etc.)
    - External factors: Effect of exogenous variables
    - Residuals: Unexplained variation
    """

    horizon: schema_field(
        int_field(ge=1, le=365),
        placeholder=30,
        description="Number of future periods to forecast and decompose. "
        "Longer horizons show how components evolve over time.",
    )  # type: ignore

    include_historical: schema_field(
        bool_field(),
        placeholder=False,
        description="If True, includes historical component decomposition "
        "to show how the model understood past data.",
    )  # type: ignore


class ForecastDecomposition(BaseGlobalExplainer):
    """Universal forecast decomposition explainer.

    Decomposes time series forecasts into interpretable components,
    adapting to different model types automatically.
    """

    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    SCHEMA = ForecastDecompositionSchema

    def __init__(
        self,
        model: BaseModel,
        horizon: int = 30,
        include_historical: bool = False,
    ):
        """Initialize ForecastDecomposition explainer.

        Parameters
        ----------
        model : BaseModel
            Trained forecasting model to explain
        horizon : int
            Number of periods to forecast (default: 30)
        include_historical : bool
            Whether to include historical decomposition (default: False)
        """
        super().__init__(model)
        self.horizon = horizon
        self.include_historical = include_historical

    def _get_native_components(self) -> pd.DataFrame:
        """Extract components from any model that implements get_forecast_components().

        This covers Prophet, ARIMA, SARIMAX, and SklearnMultiStepForecaster.
        """
        if not hasattr(self.model, "get_forecast_components"):
            raise AttributeError(
                f"{type(self.model).__name__} must implement "
                "get_forecast_components(horizon) to use this path."
            )
        return self.model.get_forecast_components(self.horizon)

    def _get_generic_components(self, dataset: DatasetDict) -> pd.DataFrame:
        """Fallback for models without native decomposition.

        Uses simple predictions as "trend" component.
        """
        x, y = dataset

        # Construct history dataframe from dataset (x and y)
        # This allows the model to predict continuing from this dataset
        try:
            # Convert to pandas with error handling
            try:
                x_df = x.to_pandas() if hasattr(x, "to_pandas") else pd.DataFrame(x)
            except Exception as e:
                print(f"Warning: Failed to convert x to DataFrame: {e}")
                x_df = None

            try:
                y_df = y.to_pandas() if hasattr(y, "to_pandas") else pd.DataFrame(y)
            except Exception as e:
                print(f"Warning: Failed to convert y to DataFrame: {e}")
                y_df = None

            # Combine if possible
            if x_df is not None and y_df is not None and len(x_df) == len(y_df):
                history_df = x_df.copy()
                for col in y_df.columns:
                    history_df[col] = y_df[col].to_numpy()

                # Get predictions using history context
                predictions = self.model.predict(
                    x_pred=history_df, periods=self.horizon
                )
            else:
                if x_df is not None and y_df is not None:
                    print(f"Warning: lengths differ (x={len(x_df)}, y={len(y_df)}).")
                    history_df = x_df.copy()
                    predictions = self.model.predict(
                        x_pred=history_df, periods=self.horizon
                    )
                elif x_df is not None:
                    print("Warning: Only x dataset available. Using x as history.")
                    history_df = x_df.copy()
                    predictions = self.model.predict(
                        x_pred=history_df, periods=self.horizon
                    )
                else:
                    print("Warning: Could not create history. Using standard predict.")
                    predictions = self.model.predict(periods=self.horizon)

        except Exception as e:
            print(f"Warning: Could not use dataset as history context: {e}")
            # Fallback to standard prediction
            predictions = self.model.predict(periods=self.horizon)

        # Handle case where model returns fewer predictions than requested
        # (e.g. SklearnMultiStepForecaster with direct strategy)
        actual_horizon = len(predictions)

        # Determine start date
        start_date = pd.Timestamp.now()
        if (
            hasattr(self.model, "last_timestamp")
            and self.model.last_timestamp is not None
        ):
            start_date = self.model.last_timestamp
        elif hasattr(self.model, "last_ds") and self.model.last_ds is not None:
            start_date = self.model.last_ds

        # Determine frequency
        freq = "D"
        if hasattr(self.model, "frequency") and self.model.frequency:
            freq = self.model.frequency

        # Generate dates (start from next period after last timestamp)
        dates = pd.date_range(start=start_date, periods=actual_horizon + 1, freq=freq)[
            1:
        ]

        # Create simple dataframe with predictions as "trend"
        components_df = pd.DataFrame(
            {
                "ds": dates,
                "trend": predictions
                if isinstance(predictions, np.ndarray)
                else predictions.to_numpy(),
                "seasonal": np.zeros(actual_horizon),
                "residual": np.zeros(actual_horizon),
            }
        )

        return components_df

    def explain(self, dataset: Tuple[DatasetDict, DatasetDict]) -> dict:
        """Generate component decomposition explanation.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            Tuple with (input_samples, targets) used for context

        Returns
        -------
        dict
            Dictionary with:
            - ds: Timestamps
            - trend: Trend component
            - seasonal: Seasonal component (if applicable)
            - weekly/yearly: Specific seasonality (if applicable)
            - exog_*: External regressor effects (if applicable)
            - model_type: Type of model decomposed
        """
        # Detect model type and extract components
        model_name = type(self.model).__name__

        # Friendly display names for known model classes
        _display_names = {
            "ProphetModel": "Prophet",
            "StatsmodelsARIMAModel": "ARIMA",
            "StatsmodelsSARIMAXModel": "SARIMAX",
            "SklearnMultiStepForecaster": "Sklearn MultiStep",
        }

        try:
            if hasattr(self.model, "get_forecast_components"):
                # Prophet, ARIMA, SARIMAX, SklearnMultiStepForecaster
                components_df = self._get_native_components()
                model_type = _display_names.get(model_name, model_name)

            else:
                # Generic fallback for unknown model types
                components_df = self._get_generic_components(dataset)
                model_type = "Generic"

        except Exception as e:
            raise RuntimeError(
                f"Failed to extract components from {model_name}: {str(e)}"
            ) from e

        # Convert to serializable format
        explanation = {
            "model_type": model_type,
            "horizon": self.horizon,
            "ds": components_df["ds"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist()
            if "ds" in components_df.columns
            else list(range(len(components_df))),
        }

        # Add all available components
        for col in components_df.columns:
            if col != "ds":
                explanation[col] = np.round(components_df[col].values, 3).tolist()

        return explanation

    def _create_decomposition_plot(self, explanation: dict) -> go.Figure:
        """Create multi-panel decomposition plot."""

        # Identify available components
        component_cols = [
            k for k in explanation if k not in ["ds", "model_type", "horizon"]
        ]

        # Prioritize component order for better visualization
        priority_order = ["trend", "seasonal", "yearly", "weekly", "daily"]
        ordered_components = []

        for comp in priority_order:
            if comp in component_cols:
                ordered_components.append(comp)

        # Add remaining components (e.g., exog_*)
        for comp in component_cols:
            if comp not in ordered_components:
                ordered_components.append(comp)

        n_components = len(ordered_components)

        # Create subplots
        fig = make_subplots(
            rows=n_components,
            cols=1,
            subplot_titles=[
                comp.replace("_", " ").title() for comp in ordered_components
            ],
            vertical_spacing=0.05,
        )

        # Add trace for each component
        for i, component in enumerate(ordered_components, 1):
            fig.add_trace(
                go.Scatter(
                    x=explanation["ds"],
                    y=explanation[component],
                    name=component.replace("_", " ").title(),
                    line={"width": 2},
                    mode="lines",
                ),
                row=i,
                col=1,
            )

        # Update layout
        fig.update_layout(
            height=250 * n_components,
            title_text=f"Forecast Decomposition ({explanation['model_type']} Model)",
            showlegend=False,
            hovermode="x unified",
        )

        fig.update_xaxes(title_text="Date", row=n_components, col=1)

        return fig

    def _create_stacked_plot(self, explanation: dict) -> go.Figure:
        """Create stacked area plot showing component contributions."""

        explanation_df = pd.DataFrame(explanation)

        # Components to stack (exclude residuals/noise)
        stack_components = [
            col
            for col in explanation_df.columns
            if col not in ["ds", "model_type", "horizon", "residual", "noise"]
            and not col.startswith("yhat")
        ]

        fig = go.Figure()

        for component in stack_components:
            fig.add_trace(
                go.Scatter(
                    x=explanation_df["ds"],
                    y=explanation_df[component],
                    name=component.replace("_", " ").title(),
                    mode="lines",
                    stackgroup="one",
                    fillcolor="rgba(0,0,0,0.1)",
                )
            )

        fig.update_layout(
            title="Component Contribution Over Time",
            xaxis_title="Date",
            yaxis_title="Contribution",
            hovermode="x unified",
        )

        return fig

    def plot(self, explanation: dict) -> List[dict]:
        """Create visualization plots.

        Parameters
        ----------
        explanation : dict
            Explanation dictionary from explain()

        Returns
        -------
        List[dict]
            List of plotly JSON figures
        """
        plots = []

        # Main decomposition plot
        decomp_fig = self._create_decomposition_plot(explanation)
        plots.append(plotly.io.to_json(decomp_fig))

        # Stacked contribution plot (if multiple components)
        component_cols = [
            k for k in explanation if k not in ["ds", "model_type", "horizon"]
        ]

        if len(component_cols) > 1:
            stacked_fig = self._create_stacked_plot(explanation)
            plots.append(plotly.io.to_json(stacked_fig))

        return plots
