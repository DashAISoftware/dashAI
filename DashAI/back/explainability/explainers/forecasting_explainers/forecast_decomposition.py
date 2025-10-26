"""Forecast Decomposition Explainer for time series models.

This explainer decomposes forecasts into interpretable components (trend,
seasonality, external regressors) for any forecasting model that supports
component extraction.

Works with:
- Prophet (trend, weekly, yearly, holidays, regressors)
- ARIMA/SARIMA (trend, seasonal, residual)
- ETS (error, trend, seasonal)
- Any future model implementing _get_components()
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

    def _get_prophet_components(self) -> pd.DataFrame:
        """Extract components from Prophet model."""
        if not hasattr(self.model, "get_forecast_components"):
            raise AttributeError(
                "Prophet model must have get_forecast_components() method"
            )

        components_df = self.model.get_forecast_components(self.horizon)
        return components_df

    def _get_arima_components(self, dataset: DatasetDict) -> pd.DataFrame:
        """Extract components from ARIMA/SARIMA model.

        Note: This is a placeholder for future ARIMA implementation.
        ARIMA models typically decompose into trend, seasonal, and residual.
        """
        # TODO: Implement when ARIMA model is added
        raise NotImplementedError(
            "ARIMA decomposition will be available when ARIMA models are implemented"
        )

    def _get_generic_components(self, dataset: DatasetDict) -> pd.DataFrame:
        """Fallback for models without native decomposition.

        Uses simple predictions as "trend" component.
        """
        x, _ = dataset

        # Get predictions
        predictions = self.model.predict(horizon=self.horizon)

        # Create simple dataframe with predictions as "trend"
        df = pd.DataFrame(
            {
                "ds": pd.date_range(
                    start=pd.Timestamp.now(), periods=self.horizon, freq="D"
                ),
                "trend": predictions
                if isinstance(predictions, np.ndarray)
                else predictions.to_numpy(),
                "seasonal": np.zeros(self.horizon),
                "residual": np.zeros(self.horizon),
            }
        )

        return df

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

        try:
            if hasattr(self.model, "get_forecast_components"):
                # Prophet or compatible
                components_df = self._get_prophet_components()
                model_type = "Prophet"

            elif hasattr(self.model, "model") and hasattr(
                self.model.model, "decompose"
            ):
                # ARIMA/SARIMA model type
                components_df = self._get_arima_components(dataset)
                model_type = "ARIMA"

            else:
                # Generic fallback
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

        df = pd.DataFrame(explanation)

        # Components to stack (exclude residuals/noise)
        stack_components = [
            col
            for col in df.columns
            if col not in ["ds", "model_type", "horizon", "residual", "noise"]
            and not col.startswith("yhat")
        ]

        fig = go.Figure()

        for component in stack_components:
            fig.add_trace(
                go.Scatter(
                    x=df["ds"],
                    y=df[component],
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
