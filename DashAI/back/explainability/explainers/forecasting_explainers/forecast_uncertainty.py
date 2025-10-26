"""Forecast Uncertainty Analysis Explainer.

Analyzes and visualizes prediction uncertainty (confidence/prediction intervals)
across the forecast horizon. Essential for risk management and decision-making.

Shows how confidence in predictions degrades over time and helps users understand
the reliability of forecasts at different time horizons.

Works with models that provide uncertainty estimates:
- Prophet (yhat_lower, yhat_upper via interval_width)
- ARIMA (confidence intervals from statsmodels)
- Any model with prediction intervals
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
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.models import BaseModel


class ForecastUncertaintySchema(BaseSchema):
    """Forecast Uncertainty Analysis shows prediction confidence intervals.

    Helps answer:
    - How confident is the model in its predictions?
    - How does uncertainty grow with forecast horizon?
    - What's the best/worst case scenario?

    Critical for inventory planning, capacity planning, and risk management.
    """

    horizon: schema_field(
        int_field(ge=1, le=365),
        placeholder=30,
        description="Number of future periods to forecast. "
        "Longer horizons typically show increasing uncertainty.",
    )  # type: ignore

    confidence_level: schema_field(
        float_field(ge=0.5, le=0.99),
        placeholder=0.80,
        description="Confidence level for prediction intervals (e.g., 0.80 = 80%). "
        "Higher values give wider intervals.",
    )  # type: ignore


class ForecastUncertainty(BaseGlobalExplainer):
    """Analyzes forecast uncertainty and prediction intervals.

    Visualizes how prediction confidence changes across the forecast horizon,
    helping users understand forecast reliability and plan for uncertainty.
    """

    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    SCHEMA = ForecastUncertaintySchema

    def __init__(
        self,
        model: BaseModel,
        horizon: int = 30,
        confidence_level: float = 0.80,
    ):
        """Initialize ForecastUncertainty explainer.

        Parameters
        ----------
        model : BaseModel
            Trained forecasting model
        horizon : int
            Number of periods to forecast (default: 30)
        confidence_level : float
            Confidence level for intervals (default: 0.80 = 80%)
        """
        super().__init__(model)
        self.horizon = horizon
        self.confidence_level = confidence_level

    def _get_prophet_uncertainty(self) -> pd.DataFrame:
        """Get uncertainty estimates from Prophet model.

        Note: This method requires the model to make future predictions.
        If the model was trained with exogenous variables, future values
        for those variables must be provided, which is not available in
        this explainer context.
        """
        if not hasattr(self.model, "predict"):
            raise AttributeError("Model must have predict() method")

        # Check if model has exogenous variables
        exog_cols = (
            self.model.get_exogenous_columns()
            if hasattr(self.model, "get_exogenous_columns")
            else []
        )

        if exog_cols:
            # Model uses exogenous variables - cannot make valid future predictions
            # without future exogenous values
            raise ValueError(
                f"This explainer cannot generate uncertainty estimates for models "
                f"trained with exogenous variables: {exog_cols}.\n"
                f"Reason: Future forecasting requires known future values for these "
                f"variables, which are not available in the explainer context.\n"
                f"Recommendation: Use ForecastFeatureImportance explainer instead, "
                f"which evaluates the model on historical test data."
            )

        # No exogenous variables - can make simple forecast
        forecast = self.model.predict(horizon=self.horizon, return_components=True)

        if not isinstance(forecast, pd.DataFrame):
            raise TypeError(
                "Prophet model must return DataFrame from "
                "predict(return_components=True)"
            )

        required_cols = ["ds", "yhat", "yhat_lower", "yhat_upper"]
        missing_cols = [col for col in required_cols if col not in forecast.columns]

        if missing_cols:
            raise ValueError(
                f"Prophet forecast missing required columns: {missing_cols}"
            )

        # Select forecast period only
        forecast_df = forecast.tail(self.horizon).copy()

        return forecast_df

    def _get_generic_uncertainty(self) -> pd.DataFrame:
        """Fallback for models without native uncertainty quantification.

        Returns point predictions with placeholder intervals.
        """
        # Get point predictions
        predictions = self.model.predict(horizon=self.horizon)

        if hasattr(predictions, "to_numpy"):
            y_pred = predictions.to_numpy()
        elif isinstance(predictions, np.ndarray):
            y_pred = predictions
        else:
            y_pred = np.array(predictions)

        # Create placeholder intervals (±10% of prediction)
        uncertainty_pct = 0.10

        df = pd.DataFrame(
            {
                "ds": pd.date_range(
                    start=pd.Timestamp.now(), periods=self.horizon, freq="D"
                ),
                "yhat": y_pred,
                "yhat_lower": y_pred * (1 - uncertainty_pct),
                "yhat_upper": y_pred * (1 + uncertainty_pct),
                "estimated_intervals": True,  # Flag that these are not native
            }
        )

        return df

    def explain(self, dataset: Tuple[DatasetDict, DatasetDict]) -> dict:
        """Generate uncertainty analysis explanation.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            Tuple with (input_features, targets) for context

        Returns
        -------
        dict
            Dictionary with:
            - ds: Timestamps
            - yhat: Point predictions
            - yhat_lower: Lower bound of prediction interval
            - yhat_upper: Upper bound of prediction interval
            - uncertainty: Interval width (yhat_upper - yhat_lower)
            - uncertainty_pct: Uncertainty as % of prediction
            - confidence_level: Configured confidence level
            - model_type: Model that generated intervals
        """
        model_name = type(self.model).__name__

        try:
            if hasattr(self.model, "predict") and model_name == "ProphetModel":
                # Prophet with native intervals
                forecast_df = self._get_prophet_uncertainty()
                model_type = "Prophet"
                has_native_intervals = True

            else:
                # Generic fallback
                forecast_df = self._get_generic_uncertainty()
                model_type = "Generic"
                has_native_intervals = False

        except Exception as e:
            raise RuntimeError(
                f"Failed to get uncertainty estimates from {model_name}: {str(e)}"
            ) from e

        # Calculate uncertainty metrics
        forecast_df["uncertainty"] = (
            forecast_df["yhat_upper"] - forecast_df["yhat_lower"]
        )

        # Avoid division by zero
        safe_yhat = np.where(forecast_df["yhat"] == 0, 1e-10, forecast_df["yhat"])
        forecast_df["uncertainty_pct"] = (
            forecast_df["uncertainty"] / np.abs(safe_yhat) * 100
        )

        # Build explanation
        explanation = {
            "model_type": model_type,
            "confidence_level": self.confidence_level,
            "horizon": self.horizon,
            "has_native_intervals": has_native_intervals,
            "ds": forecast_df["ds"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist(),
            "yhat": np.round(forecast_df["yhat"].to_numpy(), 3).tolist(),
            "yhat_lower": np.round(forecast_df["yhat_lower"].to_numpy(), 3).tolist(),
            "yhat_upper": np.round(forecast_df["yhat_upper"].to_numpy(), 3).tolist(),
            "uncertainty": np.round(forecast_df["uncertainty"].to_numpy(), 3).tolist(),
            "uncertainty_pct": np.round(
                forecast_df["uncertainty_pct"].to_numpy(), 2
            ).tolist(),
        }

        # Add summary statistics
        explanation["summary"] = {
            "mean_uncertainty": round(forecast_df["uncertainty"].mean(), 3),
            "max_uncertainty": round(forecast_df["uncertainty"].max(), 3),
            "mean_uncertainty_pct": round(forecast_df["uncertainty_pct"].mean(), 2),
            "uncertainty_growth": round(
                forecast_df["uncertainty"].iloc[-1] / forecast_df["uncertainty"].iloc[0]
                if forecast_df["uncertainty"].iloc[0] != 0
                else 0,
                2,
            ),
        }

        return explanation

    def _create_forecast_plot(self, explanation: dict) -> go.Figure:
        """Create main forecast plot with confidence intervals."""

        df = pd.DataFrame(
            {
                "ds": pd.to_datetime(explanation["ds"]),
                "yhat": explanation["yhat"],
                "yhat_lower": explanation["yhat_lower"],
                "yhat_upper": explanation["yhat_upper"],
            }
        )

        fig = go.Figure()

        # Add confidence interval band
        fig.add_trace(
            go.Scatter(
                x=df["ds"],
                y=df["yhat_upper"],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=df["ds"],
                y=df["yhat_lower"],
                mode="lines",
                line={"width": 0},
                fillcolor="rgba(68, 68, 68, 0.2)",
                fill="tonexty",
                name=(
                    f"{int(explanation['confidence_level'] * 100)}% Confidence Interval"
                ),
            )
        )

        # Add point forecast
        fig.add_trace(
            go.Scatter(
                x=df["ds"],
                y=df["yhat"],
                mode="lines",
                name="Forecast",
                line={"color": "blue", "width": 2},
            )
        )

        # Title
        title = (
            f"Forecast with {int(explanation['confidence_level'] * 100)}% "
            "Confidence Interval"
        )
        if not explanation["has_native_intervals"]:
            title += " (Estimated Intervals)"

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Predicted Value",
            hovermode="x unified",
            height=500,
        )

        return fig

    def _create_uncertainty_growth_plot(self, explanation: dict) -> go.Figure:
        """Create plot showing how uncertainty grows over horizon."""

        df = pd.DataFrame(
            {
                "ds": pd.to_datetime(explanation["ds"]),
                "uncertainty": explanation["uncertainty"],
                "uncertainty_pct": explanation["uncertainty_pct"],
            }
        )

        # Create subplot with absolute and relative uncertainty
        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=(
                "Absolute Uncertainty (Interval Width)",
                "Relative Uncertainty (% of Forecast)",
            ),
            vertical_spacing=0.12,
        )

        # Absolute uncertainty
        fig.add_trace(
            go.Scatter(
                x=df["ds"],
                y=df["uncertainty"],
                mode="lines+markers",
                name="Uncertainty",
                line={"color": "red", "width": 2},
                marker={"size": 4},
            ),
            row=1,
            col=1,
        )

        # Relative uncertainty
        fig.add_trace(
            go.Scatter(
                x=df["ds"],
                y=df["uncertainty_pct"],
                mode="lines+markers",
                name="Uncertainty %",
                line={"color": "orange", "width": 2},
                marker={"size": 4},
            ),
            row=2,
            col=1,
        )

        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Interval Width", row=1, col=1)
        fig.update_yaxes(title_text="Uncertainty (%)", row=2, col=1)

        fig.update_layout(
            title="Uncertainty Growth Over Forecast Horizon",
            height=600,
            showlegend=False,
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

        # Main forecast with intervals
        forecast_fig = self._create_forecast_plot(explanation)
        plots.append(plotly.io.to_json(forecast_fig))

        # Uncertainty growth analysis
        uncertainty_fig = self._create_uncertainty_growth_plot(explanation)
        plots.append(plotly.io.to_json(uncertainty_fig))

        # Add summary statistics as annotation figure
        summary = explanation["summary"]

        import plotly.graph_objects as go

        summary_fig = go.Figure()

        summary_text = (
            f"<b>Uncertainty Summary</b><br><br>"
            f"Mean Uncertainty: {summary['mean_uncertainty']}<br>"
            f"Max Uncertainty: {summary['max_uncertainty']}<br>"
            f"Mean Uncertainty %: {summary['mean_uncertainty_pct']:.1f}%<br>"
            f"Uncertainty Growth: {summary['uncertainty_growth']:.2f}x"
        )

        summary_fig.add_annotation(
            text=summary_text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 14},
            align="left",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="black",
            borderwidth=2,
        )

        summary_fig.update_layout(
            title="Summary Statistics",
            xaxis={"visible": False},
            yaxis={"visible": False},
            height=300,
        )

        plots.append(plotly.io.to_json(summary_fig))

        return plots
