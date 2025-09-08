from typing import Tuple, Union

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objs as go
import shap
from datasets import DatasetDict

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.explainability.local_explainer import BaseLocalExplainer
from DashAI.back.models import BaseModel


class KernelShapSchema(BaseSchema):
    """Kernel SHAP is a model-agnostic explainability method for approximating SHAP
    values to explain the output of machine learning model by attributing contributions
    of each feature to the model's prediction.
    """

    link: schema_field(
        enum_field(enum=["identity", "logit"]),
        placeholder="identity",
        description="Link function to connect the feature importance values to the "
        "model's outputs. Options are 'identity' to use identity function or 'logit' "
        "to use log-odds function.",
    )  # type: ignore

    fit_parameter_sample_background_data: schema_field(
        bool_field(),
        placeholder=False,
        description="Parameter to fit the explainer. 'true' if the background "
        "data must be sampled, otherwise the entire train data set is used. "
        "Smaller datasets speed up the algorithm run time.",
    )  # type: ignore

    fit_parameter_n_background_samples: schema_field(
        int_field(ge=1),
        placeholder=1,
        description="Parameter to fit the explainer. If the parameter "
        "'sample_background_data' is 'true', the number of background "
        "data samples to be drawn.",
    )  # type: ignore

    fit_parameter_sampling_method: schema_field(
        enum_field(enum=["shuffle", "kmeans"]),
        placeholder="shuffle",
        description="Parameter to fit the explainer. If the parameter "
        "'sample_background_data' is 'true', whether to sample random "
        "samples with 'shuffle' option or summarize the data set with "
        "'kmeans' option. If 'categorical_features' is 'true', 'shuffle' "
        "options used by default.",
    )  # type: ignore


class KernelShap(BaseLocalExplainer):
    """Kernel SHAP is a model-agnostic explainability method for approximating SHAP
    values to explain the output of machine learning model by attributing contributions
    of each feature to the model's prediction.
    """

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = KernelShapSchema

    def __init__(
        self,
        model: BaseModel,
        link: str = "identity",
    ):
        """Initialize a new instance of a KernelShap explainer.

        Parameters
        ----------
        model: BaseModel
                Model to be explained.
        link: str
            String indicating the link function to connect the feature importance
            values to the model's outputs. Options are 'identity' to use identity
            function or 'logit'to use log-odds function.
        """
        super().__init__(model)
        self.link = link

    def _sample_background_data(
        self,
        background_data: np.array,
        n_background_samples: int,
        sampling_method: str = "shuffle",
        categorical_features: bool = False,
    ):
        """Method to sample the background dataset used to fit the explainer.


        Parameters
        ----------
        background_data: np.array
            Data used to estimate feature attributions and establish a baseline for
            the calculation of SHAP values.
        n_background_samples: int
            Number of background data samples used to estimate of SHAP values. By
            default, the entire train dataset is used, but this option limits the
            samples to reduce run times.
        sampling_method: str
            Sampling method used to select the background samples. Options are
            'shuffle' to select random samples or 'kmeans' to summarise the data
            set. 'kmeans' option can only be used if there are no categorical
            features.
        categorical_features: bool
            Bool indicating whether some features are categorical.

        Returns
        -------
        pd.DataFrame
            pandas DataFrame with the background data used to fit the
            explainer.
        """

        samplers = {"shuffle": shap.sample, "kmeans": shap.kmeans}

        if categorical_features:
            data = samplers["shuffle"](background_data, n_background_samples)
        else:
            data = samplers[sampling_method](background_data, n_background_samples)

        return data

    def fit(
        self,
        background_dataset: Tuple[DatasetDict, DatasetDict],
        sample_background_data: str = "false",
        n_background_samples: Union[int, None] = None,
        sampling_method: Union[str, None] = None,
    ):
        """Method to train the KernelShap explainer.

        Parameters
        ----------
        background_data: Tuple[DatasetDict, DatasetDict]
            Tuple with (input_samples, targets). Input samples are used to estimate
            feature attributions and establish a baseline for the calculation of
            SHAP values.
        sample_background_data: bool
            True if the background data must be sampled. Smaller data sets speed up
            the algorithm run time. False by default.
        n_background_samples: int
            Number of background data samples used to estimate of SHAP values if
            ``sample_background_data=True``.
        sampling_method: str
            Sampling method used to select the background samples if
            ``sample_background_data=True``. Options are 'shuffle' to select random
            samples or 'kmeans' to summarise the data set. 'kmeans' option can only
            be used if there are no categorical features.

        Returns
        -------
        KernelShap object
        """
        sample_background_data = bool(sample_background_data)

        x, y = background_dataset

        background_data = x["train"].to_pandas()
        features = x["train"].features
        feature_names = list(features)

        categorical_features = False
        for feature in features:
            if features[feature]._type == "ClassLabel":
                categorical_features = True

        if sample_background_data:
            background_data = self._sample_background_data(
                background_data.to_numpy(),
                n_background_samples,
                sampling_method,
                categorical_features,
            )

        # TODO: consider the case where the predictor is not a Sklearn model
        self.explainer = shap.KernelExplainer(
            model=self.model.predict,
            data=background_data,
            feature_names=feature_names,
            link=self.link,
        )

        # Metadata
        output_column = list(y["train"].features)[0]
        target_names = y["train"].features[output_column].names
        self.metadata = {"feature_names": feature_names, "target_names": target_names}

        return self

    def explain_instance(
        self,
        instances: DatasetDict,
    ):
        """Method for explaining the model prediciton of an instance using the Kernel
        Shap method.

        Parameters
        ----------
        instances: DatasetDict
            Instances to be explained.

        Returns
        -------
        dict
            dictionary with the shap values for each instance.
        """

        dataset_dashai = to_dashai_dataset(instances)
        X = dataset_dashai.to_pandas()

        predictions = self.model.predict(x_pred=X)

        # TODO: evaluate args nsamples y l1_reg
        shap_values = self.explainer.shap_values(X=X)

        # shap_values has size (n_clases, n_instances, n_features)
        # Reorder shap values: (n_instances, n_clases, n_features)
        shap_values = np.array(shap_values).swapaxes(1, 0)

        explanation = {
            "metadata": self.metadata,
            "base_values": np.round(self.explainer.expected_value, 3).tolist(),
        }

        for i, (instance, prediction, contribution_values) in enumerate(
            zip(X.to_numpy(), predictions, shap_values)  # noqa B905
        ):
            explanation[i] = {
                "instance_values": instance.tolist(),
                "model_prediction": prediction.tolist(),
                "shap_values": np.round(contribution_values, 3).tolist(),
            }

        return explanation

    def _create_plot(
        self, data: pd.DataFrame, base_value: float, y_pred_pbb: float, y_pred_name: str
    ):
        """Helper method to create the explanation plot using plotly.

        Parameters
        ----------
        data: pd.DataFrame
            dataframe containing the data to be plotted.
        base_value: float
            value to set where the bar base is drawn.
        y_pred_pbb: float
            predicted probability.
        y_pred_name
            name of the predicted class.

        Returns:
        JSON
            JSON containing the information of the explanation plot
            to be rendered.
        """
        x = data["shap_values"].to_numpy()
        y = data["label"].to_numpy()
        measure = np.repeat("relative", len(y))
        texts = data["shap_values"].to_numpy()

        fig = go.Figure(
            go.Waterfall(
                x=x,
                y=y,
                base=base_value,
                name="20",
                orientation="h",
                measure=measure,
                text=texts,
                textposition="auto",
                constraintext="inside",
                decreasing={"marker": {"color": "rgb(47,138,196)"}},
                increasing={"marker": {"color": "rgb(231,63,116)"}},
            )
        )

        fig.update_layout(
            margin={"pad": 20, "l": 100, "r": 130, "t": 60, "b": 10},
            xaxis={
                "tickangle": -90,
                "tickwidth": 100,
                "title_text": "",
            },
            yaxis={"showgrid": True, "tickwidth": 150},
        )

        fig.update_xaxes(
            gridcolor="#1B2631",
            gridwidth=1,
            tickmode="array",
            nticks=2,
            tickvals=[base_value, y_pred_pbb],
            ticktext=[f"E[f(x)]={base_value}", f"f(x)={y_pred_pbb}"],
            tickangle=0,
            showgrid=True,
        )

        plot_note = (
            f"The predicted class was {y_pred_name} with probability f(x)={y_pred_pbb}."
        )

        fig.add_annotation(
            align="center",
            arrowsize=0.3,
            arrowwidth=0.1,
            font={"size": 12},
            showarrow=False,
            text=plot_note,
            xanchor="center",
            yanchor="bottom",
            xref="paper",
            yref="paper",
            y=-0.27,
        )

        return plotly.io.to_json(fig)

    def plot(self, explanation: list[dict]):
        """Method to create the explanation plot using plotly.

        Parameters
        ----------
        explanation: dict
            dictionary with the explanation generated by the explainer.

        Returns:
        List[dict]
            list of JSONs containing the information of the explanation plot
            to be rendered.
        """

        exp = explanation.copy()

        max_features = 8
        metadata = exp.pop("metadata")
        base_values = exp.pop("base_values")
        feature_names = metadata["feature_names"]
        target_names = metadata["target_names"]

        # Normaliza feature_names a 1D
        feats = np.asarray(feature_names, dtype=str).reshape(-1)

        plots = []
        for i in exp:
            instance_values = exp[i]["instance_values"]
            model_prediction = exp[i]["model_prediction"]
            y_pred_class = int(np.argmax(model_prediction))
            y_pred_name = target_names[y_pred_class]
            y_pred_pbb = float(np.round(model_prediction[y_pred_class], 2))

            # --- Normaliza valores de la instancia a 1D
            vals = np.asarray(instance_values).reshape(-1)

            # --- Normaliza shap_values a 1D alineado con feats
            sv = exp[i]["shap_values"]
            # 1) Si viene como lista (típico multiclass: una entrada por clase)
            if isinstance(sv, list):
                sv_raw = np.asarray(sv[y_pred_class])
            else:
                sv_raw = np.asarray(sv)

            # 2) Intenta extraer del objeto shap.Explanation si aplica
            try:
                from shap._explanation import Explanation

                if isinstance(sv, Explanation):
                    sv_raw = np.asarray(sv.values)
            except Exception:
                pass

            # 3) Resolver formas 2D con eje de clases/características
            if sv_raw.ndim == 2:
                if sv_raw.shape[0] == feats.size and sv_raw.shape[1] != feats.size:
                    # n_features, n_classes
                    sv_raw = sv_raw[:, y_pred_class]
                elif sv_raw.shape[1] == feats.size and sv_raw.shape[0] != feats.size:
                    # n_classes n_features
                    sv_raw = sv_raw[y_pred_class, :]
                elif (
                    sv_raw.shape[0] == 1
                    and sv_raw.shape[1] == feats.size
                    or sv_raw.shape[1] == 1
                    and sv_raw.shape[0] == feats.size
                ):
                    sv_raw = sv_raw.reshape(-1)
                else:
                    raise ValueError(
                        f"shap_values {sv_raw.shape} n_features={feats.size}"
                    )
            else:
                sv_raw = sv_raw.reshape(-1)

            # 4) Asegura mismas longitudes (recorte defensivo si algo llegó desalineado)
            n = min(vals.size, feats.size, sv_raw.size)
            if not (vals.size == feats.size == sv_raw.size):
                # Puedes cambiar este print por un logger si lo prefieres
                print(
                    f"[WARN] Desalineado: len(values)={vals.size}, "
                    f"len(features)={feats.size}, len(shap_values)={sv_raw.size}. "
                    f"Se recorta a {n}."
                )
                vals = vals[:n]
                feats = feats[:n]
                sv_raw = sv_raw[:n]

            # --- Construcción del DataFrame ya normalizado
            data = pd.DataFrame(
                {
                    "values": vals,
                    "shap_values": sv_raw,
                    "features": feats,
                }
            )

            # --- Resto de tu pipeline
            data["shap_values_abs"] = np.abs(data["shap_values"])
            data = data.sort_values(by="shap_values_abs", ascending=True)

            if len(data) > max_features:
                data_1 = data.iloc[-max_features:, :]
                data_2 = data.iloc[:-max_features, :]
                others = pd.DataFrame.from_dict(
                    {
                        "values": [None],
                        "shap_values": [
                            float(np.round(data_2["shap_values"].sum(), 3))
                        ],
                        "shap_values_abs": [None],
                        "features": ["Others"],
                    }
                )
                data = pd.concat([others, data_1], ignore_index=True)

            data["label"] = data["features"] + "=" + data["values"].map(str)

            # base_values puede ser escalar o vector por clase
            base_arr = np.asarray(base_values)
            if base_arr.ndim == 0:
                base_value = float(base_arr)
            else:
                base_value = float(base_arr[y_pred_class])

            plot = self._create_plot(data, base_value, y_pred_pbb, y_pred_name)
            plots.append(plot)

        return plots
