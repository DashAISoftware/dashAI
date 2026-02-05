from typing import Dict, List, Union

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.models import BaseModel


class PermutationFeatureImportanceSchema(BaseSchema):
    """
    Permutation Feature Importance is an explanation method to assess the
    importance of each feature in a model by evaluating how much the model's
    performance decreases when the values of a specific feature are randomly
    shuffled.
    """

    scoring: schema_field(
        enum_field(enum=["accuracy", "balanced_accuracy"]),
        placeholder="accuracy",
        description=MultilingualString(
            en=(
                "Metric used to evaluate how the model's performance changes when "
                "a particular feature is shuffled."
            ),
            es=(
                "Métrica utilizada para evaluar cómo cambia el rendimiento del "
                "modelo cuando se baraja una característica particular."
            ),
        ),
        alias=MultilingualString(en="Scoring metric", es="Métrica de evaluación"),
    )  # type: ignore

    n_repeats: schema_field(
        int_field(ge=1),
        placeholder=20,
        description=MultilingualString(
            en=("Number of times to permute a feature."),
            es=("Número de veces que se permuta una característica."),
        ),
        alias=MultilingualString(en="Number of repeats", es="Número de repeticiones"),
    )  # type: ignore

    random_state: schema_field(
        int_field(),
        placeholder=0,
        description=MultilingualString(
            en=(
                "Seed for the random number generator to control permutations of "
                "each feature."
            ),
            es=(
                "Semilla del generador aleatorio para controlar las permutaciones "
                "de cada característica."
            ),
        ),
        alias=MultilingualString(en="Random state", es="Semilla aleatoria"),
    )  # type: ignore

    max_samples_fraction: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=1.0,
        description=MultilingualString(
            en=(
                "Fraction of samples to draw from the test set to calculate "
                "feature importance at each repetition."
            ),
            es=(
                "Fracción de muestras a extraer del conjunto de prueba para "
                "calcular la importancia en cada repetición."
            ),
        ),
        alias=MultilingualString(
            en="Max samples fraction",
            es="Fracción máxima de muestras",
        ),
    )  # type: ignore


class PermutationFeatureImportance(BaseGlobalExplainer):
    """Permutation Feature Importance is a explanation method to asses the importance
    of each feature in a model by evaluating how much the model's performance
    decreases when the values of a specific feature are randomly shuffled.
    """

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    DISPLAY_NAME = MultilingualString(
        en="Permutation Feature Importance",
        es="Importancia por Permutación",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Assesses feature importance by measuring the drop in model "
            "performance when a feature's values are randomly shuffled."
        ),
        es=(
            "Evalúa la importancia de las características midiendo la caída en el "
            "rendimiento del modelo cuando los valores de una característica se "
            "barajan aleatoriamente."
        ),
    )
    COLOR = "#800080"
    SCHEMA = PermutationFeatureImportanceSchema

    def __init__(
        self,
        model: BaseModel,
        scoring: Union[str, List[str], None] = None,
        n_repeats: int = 5,
        random_state: Union[int, None] = None,
        max_samples_fraction: float = 0.5,
    ):
        super().__init__(model)

        # Lazy import metrics only during initialization
        from sklearn.metrics import accuracy_score, balanced_accuracy_score

        metrics = {
            "accuracy": accuracy_score,
            "balanced_accuracy": balanced_accuracy_score,
        }

        self.scoring = metrics[scoring]
        self.n_repeats = n_repeats
        self.random_state = random_state
        self.max_samples_fraction = max_samples_fraction

    def _get_feature_groups(self, columns: List[str]) -> Dict[str, List[int]]:
        """Group one-hot encoded columns back to their original feature."""
        feature_groups = {}

        if (
            hasattr(self.model, "one_hot_encoder")
            and self.model.one_hot_encoder is not None
            and hasattr(self.model, "categorical_columns")
            and self.model.categorical_columns
        ):
            encoder = self.model.one_hot_encoder
            original_cat_cols = self.model.categorical_columns

            encoded_feature_names = list(
                encoder.get_feature_names_out(original_cat_cols)
            )

            for orig_col in original_cat_cols:
                prefix = f"{orig_col}_"
                indices = [
                    columns.index(enc_col)
                    for enc_col in encoded_feature_names
                    if enc_col.startswith(prefix) and enc_col in columns
                ]
                if indices:
                    feature_groups[orig_col] = indices

            # Add non-categorical columns
            for idx, col in enumerate(columns):
                if col not in encoded_feature_names:
                    feature_groups[col] = [idx]
        else:
            for idx, col in enumerate(columns):
                feature_groups[col] = [idx]

        return feature_groups

    def _calculate_grouped_importance(
        self,
        x_data,
        y,
        feature_groups: Dict[str, List[int]],
        max_samples: int,
    ):
        """Calculate permutation importance for grouped features."""
        # Lazy imports
        import numpy as np

        rng = np.random.RandomState(self.random_state)

        n_samples = min(max_samples, len(x_data))
        sample_indices = rng.choice(len(x_data), size=n_samples, replace=False)
        x_sample = x_data.iloc[sample_indices].copy().reset_index(drop=True)
        y_sample = y.iloc[sample_indices].copy().reset_index(drop=True)

        y_array = y_sample.to_numpy().ravel()
        column_names = list(x_sample.columns)

        # Access the underlying sklearn model
        sklearn_model = self.model

        def get_predictions(data):
            # Keep as DataFrame to preserve column names
            return sklearn_model.predict_proba(data)

        def calc_score(y_true, y_pred_probas):
            y_pred = np.argmax(y_pred_probas, axis=1)
            return self.scoring(y_true, y_pred)

        baseline_predictions = get_predictions(x_sample)
        baseline_score = calc_score(y_array, baseline_predictions)

        results = {"features": [], "importances_mean": [], "importances_std": []}

        for feature_name, col_indices in feature_groups.items():
            importances = []

            # Get column names for this group
            group_cols = [column_names[i] for i in col_indices]

            for _ in range(self.n_repeats):
                # Work with DataFrame to preserve column names
                x_permuted = x_sample.copy()

                # Permute rows for this group of columns
                permutation = rng.permutation(n_samples)

                # Get the block of columns, permute rows, put back
                original_block = x_sample[group_cols].to_numpy()
                permuted_block = original_block[permutation, :]
                x_permuted[group_cols] = permuted_block

                permuted_predictions = get_predictions(x_permuted)
                permuted_score = calc_score(y_array, permuted_predictions)

                importance = baseline_score - permuted_score
                importances.append(importance)

            results["features"].append(feature_name)
            results["importances_mean"].append(np.mean(importances))
            results["importances_std"].append(np.std(importances))

        return results

    def explain(self, dataset):
        """Method for calculating the importance of features in the model."""
        # Lazy imports
        import numpy as np
        import pandas as pd
        from sklearn.inspection import permutation_importance
        from sklearn.metrics import make_scorer
        from sklearn.preprocessing import LabelEncoder

        x, y = dataset

        x_test = x["test"]
        y_test = y["test"]

        X_df = x_test.to_pandas()
        y_df = y_test.to_pandas()

        y_values = y_df.to_numpy().ravel()
        if y_values.dtype == object or y_values.dtype.kind in ("U", "S"):
            if (
                hasattr(self.model, "label_encoder")
                and self.model.label_encoder is not None
            ):
                y_encoded = self.model.label_encoder.transform(y_values)
            else:
                le = LabelEncoder()
                y_encoded = le.fit_transform(y_values)
            y_df = pd.DataFrame(y_encoded, columns=y_df.columns)

        input_columns = list(X_df.columns)

        feature_groups = self._get_feature_groups(input_columns)

        max_samples = max(int(len(x_test) * self.max_samples_fraction), 1)

        has_grouped_features = any(
            len(indices) > 1 for indices in feature_groups.values()
        )

        if has_grouped_features:
            results = self._calculate_grouped_importance(
                X_df, y_df, feature_groups, max_samples
            )
            return {
                "features": results["features"],
                "importances_mean": np.round(results["importances_mean"], 3).tolist(),
                "importances_std": np.round(results["importances_std"], 3).tolist(),
            }
        else:

            def patched_metric(y_true, y_pred_probas):
                return self.scoring(y_true, np.argmax(y_pred_probas, axis=1))

            pfi = permutation_importance(
                estimator=self.model,
                X=X_df,
                y=y_df,
                scoring=make_scorer(patched_metric),
                n_repeats=self.n_repeats,
                random_state=self.random_state,
                max_samples=max_samples,
            )

            return {
                "features": input_columns,
                "importances_mean": np.round(pfi["importances_mean"], 3).tolist(),
                "importances_std": np.round(pfi["importances_std"], 3).tolist(),
            }

    def _create_plot(self, data, n_features: int):
        """Helper method to create the explanation plot using plotly."""
        # Lazy imports
        import plotly
        import plotly.express as px

        fig = px.bar(
            data.iloc[-n_features:],
            x=data.iloc[-n_features:]["importances_mean"],
            y=data.iloc[-n_features:]["features"],
            error_x=data.iloc[-n_features:]["importances_std"],
        )

        fig.update_layout(
            xaxis_title="Importance",
            yaxis_title=None,
            annotations=[
                {
                    "text": "",
                    "showarrow": False,
                    "x": 0,
                    "y": 1.15,
                    "xanchor": "left",
                    "xref": "paper",
                    "yref": "paper",
                    "yanchor": "top",
                }
            ],
            updatemenus=[
                {
                    "x": 0,
                    "xanchor": "left",
                    "y": 1.2,
                    "yanchor": "top",
                    "buttons": [
                        {
                            "label": f"N° features: {len(data.iloc[-c:,])}",
                            "method": "restyle",
                            "args": [
                                {
                                    "x": [data.iloc[-c:]["importances_mean"]],
                                    "y": [data.iloc[-c:]["features"]],
                                    "error_x": [data.iloc[-c:]["importances_std"]],
                                },
                            ],
                        }
                        for c in range(len(data))
                    ],
                }
            ],
        )

        return [plotly.io.to_json(fig)]

    def plot(self, explanation: dict) -> List[dict]:
        """Method to create the explanation plot."""
        n_features = 10
        # Lazy import
        import pandas as pd

        data = pd.DataFrame.from_dict(explanation)
        data = data.sort_values(by=["importances_mean"], ascending=True)

        if n_features > len(data):
            n_features = len(data)

        return self._create_plot(data, n_features)
