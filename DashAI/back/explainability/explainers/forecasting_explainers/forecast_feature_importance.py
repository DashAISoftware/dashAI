"""Feature Importance Explainer for Forecasting Models.

Evaluates the importance of exogenous variables (regressors) in forecasting models
by measuring how model performance degrades when each feature is permuted.

This is the forecasting adaptation of Permutation Feature Importance, using
time series specific metrics (MAE, RMSE, MAPE) instead of classification metrics.

Works with any forecasting model that implements ForecastingModel interface,
which provides get_exogenous_columns() to list external features in their original
format (model-agnostic).

Compatible models:
- Prophet with add_regressor()
- ARIMA/SARIMAX with exog
- Any model inheriting from ForecastingModel
"""

from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly
import plotly.express as px
from datasets import DatasetDict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.explainability.explainers.forecasting_explainers.forecasting_global_explainer import (  # noqa: E501
    ForecastingGlobalExplainer,
)
from DashAI.back.models.base_model import BaseModel


class ForecastFeatureImportanceSchema(BaseSchema):
    """Feature Importance for forecasting models with exogenous variables.

    Measures how much each external variable (weather, holidays, promotions, etc.)
    contributes to forecast accuracy by randomly shuffling each feature and
    measuring performance degradation.
    """

    scoring: schema_field(
        enum_field(enum=["mae", "rmse", "mape"]),
        placeholder="mae",
        description="Metric to evaluate performance degradation. "
        "MAE (Mean Absolute Error) is most interpretable, "
        "RMSE (Root Mean Squared Error) penalizes large errors, "
        "MAPE (Mean Absolute Percentage Error) shows relative error.",
    )  # type: ignore

    n_repeats: schema_field(
        int_field(ge=1, le=50),
        placeholder=10,
        description="Number of times to permute each feature. "
        "More repeats give more stable importance estimates but take longer.",
    )  # type: ignore

    random_state: schema_field(
        int_field(ge=0),
        placeholder=42,
        description="Seed for random number generator to ensure reproducible results.",
    )  # type: ignore


class ForecastFeatureImportance(ForecastingGlobalExplainer):
    """Feature importance explainer for forecasting models with exogenous variables.

    Identifies which external variables (regressors) are most important for
    accurate forecasts by measuring performance degradation when each is permuted.
    """

    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    SCHEMA = ForecastFeatureImportanceSchema

    def __init__(
        self,
        model: BaseModel,
        scoring: str = "mae",
        n_repeats: int = 10,
        random_state: int = 42,
    ):
        """Initialize ForecastFeatureImportance explainer.

        Parameters
        ----------
        model : BaseModel
            Trained forecasting model to explain
        scoring : str
            Metric to use: 'mae', 'rmse', or 'mape' (default: 'mae')
        n_repeats : int
            Number of permutation repeats (default: 10)
        random_state : int
            Random seed for reproducibility (default: 42)
        """
        super().__init__(model)

        # Define scoring functions
        self.scoring_functions = {
            "mae": self._mean_absolute_error,
            "rmse": self._root_mean_squared_error,
            "mape": self._mean_absolute_percentage_error,
        }

        if scoring not in self.scoring_functions:
            raise ValueError(
                f"Unknown scoring metric: {scoring}. "
                f"Choose from: {list(self.scoring_functions.keys())}"
            )

        self.scoring = scoring
        self.score_func = self.scoring_functions[scoring]
        self.n_repeats = n_repeats
        self.random_state = random_state

    def _mean_absolute_error(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate Mean Absolute Error."""
        return np.mean(np.abs(y_true - y_pred))

    def _root_mean_squared_error(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate Root Mean Squared Error."""
        return np.sqrt(np.mean((y_true - y_pred) ** 2))

    def _mean_absolute_percentage_error(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> float:
        """Calculate Mean Absolute Percentage Error."""
        # Avoid division by zero
        mask = y_true != 0
        if not np.any(mask):
            return np.inf
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

    def explain(self, dataset: Tuple[DatasetDict, DatasetDict]) -> dict:
        """Calculate feature importance using permutation.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            Tuple with (full_prepared_dataset, targets)
            For forecasting: first element contains timestamp + exog vars + target

        Returns
        -------
        dict
            Dictionary with:
            - features: List of feature names
            - importances_mean: Average importance for each feature
            - importances_std: Standard deviation of importance
            - baseline_score: Model performance without permutation
            - scoring_metric: Metric used (mae, rmse, mape)
        """
        x, y = dataset

        # Use test set for evaluation
        x_test = x["test"]
        y_test = y["test"]

        # Get exogenous features from model (using base class method)
        exog_features = self._get_exogenous_columns()

        if len(exog_features) == 0:
            return {
                "error": "No exogenous features found",
                "message": (
                    "This model does not use exogenous variables. "
                    "Feature importance is only available for models with "
                    "external regressors."
                ),
                "features": [],
                "importances_mean": [],
                "importances_std": [],
            }

        print(
            "[ForecastFeatureImportance] Evaluating "
            f"{len(exog_features)} exogenous variables"
        )

        # Convert to pandas - x_test now has ALL columns including timestamp
        x_df = x_test.to_pandas()
        y_true = y_test.to_pandas().to_numpy().ravel()

        timestamp_col = self._get_timestamp_column()
        target_col = self._get_target_column()

        print(
            f"[ForecastFeatureImportance] Using timestamp: {timestamp_col}, "
            f"target: {target_col}"
        )
        print(f"[ForecastFeatureImportance] Test set size: {len(x_df)} rows")
        print(f"[ForecastFeatureImportance] Columns in x_df: {x_df.columns.tolist()}")

        # Calculate baseline score (without permutation)
        try:
            # Use ForecastingModel interface: predict(x_pred=DataFrame)
            # The model's predict() method expects a DataFrame with:
            # - Timestamp column (original name)
            # - Exogenous variables (original names)
            # This is model-agnostic - works for Prophet, ARIMA, LSTM, etc.

            # Prepare input DataFrame for model's predict method
            input_df = x_df.copy()

            # Call the model's predict method using ForecastingModel interface
            predictions = self.model.predict(x_pred=input_df)  # type: ignore

            # Extract predictions from result
            # ForecastingModel.predict() returns DataFrame with target column
            if isinstance(predictions, pd.DataFrame):
                # Try to get the target column
                if target_col and target_col in predictions.columns:
                    y_pred_baseline = predictions[target_col].to_numpy()
                elif "yhat" in predictions.columns:
                    # Fallback to 'yhat' (Prophet style)
                    y_pred_baseline = predictions["yhat"].to_numpy()
                else:
                    # Take first numeric column
                    numeric_cols = predictions.select_dtypes(
                        include=[np.number]
                    ).columns
                    if len(numeric_cols) > 0:
                        y_pred_baseline = predictions[numeric_cols[0]].to_numpy()
                    else:
                        raise ValueError("No numeric columns found in predictions")
            elif isinstance(predictions, np.ndarray):
                y_pred_baseline = predictions
            else:
                y_pred_baseline = np.array(predictions)

            baseline_score = self.score_func(y_true, y_pred_baseline)
            print(
                "[ForecastFeatureImportance] Baseline score "
                f"({self.scoring}): {baseline_score:.4f}"
            )
        except Exception as e:
            print("[ForecastFeatureImportance] ERROR in baseline prediction:")
            print(f"  - x_df shape: {x_df.shape}")
            print(f"  - x_df columns: {x_df.columns.tolist()}")
            print(f"  - Error: {str(e)}")
            raise RuntimeError(f"Failed to get baseline predictions: {str(e)}") from e

        # Calculate importance for each feature
        importances = {feature: [] for feature in exog_features}

        rng = np.random.RandomState(self.random_state)

        for feature in exog_features:
            print(f"[ForecastFeatureImportance] Permuting feature: {feature}")
            for repeat in range(self.n_repeats):
                # Copy dataframe and permute the feature
                x_permuted = x_df.copy()
                x_permuted[feature] = rng.permutation(x_permuted[feature].to_numpy())

                # Get predictions with permuted feature using ForecastingModel interface
                try:
                    # Use same interface as baseline
                    predictions_perm = self.model.predict(x_pred=x_permuted)  # type: ignore

                    # Extract predictions (same logic as baseline)
                    if isinstance(predictions_perm, pd.DataFrame):
                        if target_col and target_col in predictions_perm.columns:
                            y_pred_permuted = predictions_perm[target_col].to_numpy()
                        elif "yhat" in predictions_perm.columns:
                            y_pred_permuted = predictions_perm["yhat"].to_numpy()
                        else:
                            numeric_cols = predictions_perm.select_dtypes(
                                include=[np.number]
                            ).columns
                            if len(numeric_cols) > 0:
                                y_pred_permuted = predictions_perm[
                                    numeric_cols[0]
                                ].to_numpy()
                            else:
                                raise ValueError(
                                    "No numeric columns in permuted predictions"
                                )
                    elif isinstance(predictions_perm, np.ndarray):
                        y_pred_permuted = predictions_perm
                    else:
                        y_pred_permuted = np.array(predictions_perm)

                    permuted_score = self.score_func(y_true, y_pred_permuted)

                    # For error metrics (lower is better), importance is positive
                    # when permutation increases error
                    importance = permuted_score - baseline_score
                    importances[feature].append(importance)

                except Exception as e:
                    print(
                        f"  Warning: Failed repeat {repeat + 1} for {feature}: {str(e)}"
                    )
                    importances[feature].append(0.0)

        # Calculate statistics
        features = list(importances.keys())
        importances_mean = [np.mean(importances[f]) for f in features]
        importances_std = [np.std(importances[f]) for f in features]

        return {
            "features": features,
            "importances_mean": np.round(importances_mean, 4).tolist(),
            "importances_std": np.round(importances_std, 4).tolist(),
            "baseline_score": round(baseline_score, 4),
            "scoring_metric": self.scoring,
        }

    def _create_plot(
        self, data: pd.DataFrame, explanation: dict
    ) -> plotly.graph_objs.Figure:
        """Create horizontal bar plot showing feature importances.

        Parameters
        ----------
        data : pd.DataFrame
            Dataframe with features and importances
        explanation : dict
            Full explanation dictionary

        Returns
        -------
        plotly.graph_objs.Figure
            Interactive bar chart
        """
        # Sort by importance
        data = data.sort_values(by="importances_mean", ascending=True)

        fig = px.bar(
            data,
            x="importances_mean",
            y="features",
            error_x="importances_std",
            orientation="h",
            title=f"Feature Importance ({explanation['scoring_metric'].upper()})",
            labels={
                "importances_mean": (
                    f"Importance (Δ{explanation['scoring_metric'].upper()})"
                ),
                "features": "Feature",
            },
        )

        # Add baseline info
        baseline_text = (
            f"Baseline {explanation['scoring_metric'].upper()}: "
            f"{explanation['baseline_score']:.4f}"
        )

        fig.add_annotation(
            text=baseline_text,
            xref="paper",
            yref="paper",
            x=0.98,
            y=0.98,
            showarrow=False,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1,
        )

        # Add explanation note
        note_text = (
            f"Higher values = more important feature<br>"
            f"Measured as increase in {explanation['scoring_metric'].upper()} "
            f"when feature is randomly shuffled"
        )

        fig.add_annotation(
            text=note_text,
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0.15,
            showarrow=False,
            font={"size": 10},
            xanchor="center",
        )

        fig.update_layout(
            height=max(400, len(data) * 40),
            margin={"b": 100},
        )

        return fig

    def plot(self, explanation: dict) -> List[dict]:
        """Create visualization of feature importances.

        Parameters
        ----------
        explanation : dict
            Explanation dictionary from explain()

        Returns
        -------
        List[dict]
            List with single plotly JSON figure
        """
        # Check for errors
        if "error" in explanation:
            # Return empty plot with error message
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_annotation(
                text=explanation["message"],
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 14},
            )
            fig.update_layout(
                title="Feature Importance - No Exogenous Variables",
                xaxis={"visible": False},
                yaxis={"visible": False},
            )
            return [plotly.io.to_json(fig)]

        # Create dataframe
        data = pd.DataFrame(
            {
                "features": explanation["features"],
                "importances_mean": explanation["importances_mean"],
                "importances_std": explanation["importances_std"],
            }
        )

        # Clean feature names for display
        # Remove 'exog_' prefix if present, then format for readability
        data["features"] = (
            data["features"]
            .str.replace("exog_", "", regex=False)
            .str.replace("_", " ")
            .str.title()
        )

        fig = self._create_plot(data, explanation)

        return [plotly.io.to_json(fig)]
