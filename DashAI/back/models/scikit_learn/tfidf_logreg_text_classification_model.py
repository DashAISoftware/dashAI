"""DashAI TF-IDF + Logistic Regression text classification model."""

from typing import TYPE_CHECKING, Union

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.text_classification_model import TextClassificationModel

if TYPE_CHECKING:
    from pathlib import Path

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TfIdfLogRegTextClassificationModelSchema(BaseSchema):
    """Configuration schema for TF-IDF + Logistic Regression text classifier."""

    ngram_min_n: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en="Minimum n-gram size for the TF-IDF vectorizer (≥ 1).",
            es="Tamaño mínimo de n-grama para el vectorizador TF-IDF (≥ 1).",
        ),
        alias=MultilingualString(en="Min n-gram", es="N-grama mínimo"),
    )  # type: ignore
    ngram_max_n: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en="Maximum n-gram size for the TF-IDF vectorizer (≥ 1).",
            es="Tamaño máximo de n-grama para el vectorizador TF-IDF (≥ 1).",
        ),
        alias=MultilingualString(en="Max n-gram", es="N-grama máximo"),
    )  # type: ignore
    use_idf: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Enable inverse-document-frequency re-weighting.",
            es="Activar re-ponderación por frecuencia inversa de documento.",
        ),
        alias=MultilingualString(en="Use IDF", es="Usar IDF"),
    )  # type: ignore
    sublinear_tf: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en=("Apply sublinear TF scaling (replace TF with 1 + log(TF))."),
            es=("Aplicar escalado sublineal de TF (reemplazar TF con 1 + log(TF))."),
        ),
        alias=MultilingualString(en="Sublinear TF", es="TF sublineal"),
    )  # type: ignore
    C: schema_field(
        float_field(gt=0.0),
        placeholder=1.0,
        description=MultilingualString(
            en=(
                "Regularization parameter for logistic regression. "
                "Smaller values mean stronger regularization."
            ),
            es=(
                "Parámetro de regularización para regresión logística. "
                "Valores más pequeños significan mayor regularización."
            ),
        ),
        alias=MultilingualString(en="C (Regularization)", es="C (Regularización)"),
    )  # type: ignore
    max_iter: schema_field(
        int_field(ge=100),
        placeholder=1000,
        description=MultilingualString(
            en="Maximum number of iterations for the logistic regression solver.",
            es=("Número máximo de iteraciones para el solver de regresión logística."),
        ),
        alias=MultilingualString(en="Max iterations", es="Iteraciones máximas"),
    )  # type: ignore
    solver: schema_field(
        enum_field(["lbfgs", "liblinear", "saga"]),
        placeholder="lbfgs",
        description=MultilingualString(
            en="Optimization algorithm for logistic regression.",
            es="Algoritmo de optimización para regresión logística.",
        ),
        alias=MultilingualString(en="Solver", es="Solver"),
    )  # type: ignore


class TfIdfLogRegTextClassificationModel(TextClassificationModel):
    """TF-IDF vectorizer combined with Logistic Regression for text classification.

    This model converts raw text into TF-IDF feature vectors using scikit-learn's
    ``TfidfVectorizer`` with a configurable n-gram range and IDF weighting, then
    trains a ``LogisticRegression`` classifier on the resulting sparse matrix.
    It is a strong baseline for text classification tasks, particularly when
    training data is limited or computational resources are constrained.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
    """

    DISPLAY_NAME: str = MultilingualString(
        en="TF-IDF + Logistic Regression",
        es="TF-IDF + Regresión Logística",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "TF-IDF vectorizer combined with logistic regression "
            "for text classification."
        ),
        es=(
            "Vectorizador TF-IDF combinado con regresión logística "
            "para clasificación de texto."
        ),
    )
    COLOR: str = "#00695C"
    ICON: str = "Article"
    SCHEMA = TfIdfLogRegTextClassificationModelSchema

    def __init__(self, **kwargs) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import LabelEncoder

        self.vectorizer = TfidfVectorizer(
            ngram_range=(kwargs["ngram_min_n"], kwargs["ngram_max_n"]),
            use_idf=kwargs["use_idf"],
            sublinear_tf=kwargs["sublinear_tf"],
        )
        self.classifier = LogisticRegression(
            C=kwargs["C"],
            max_iter=kwargs["max_iter"],
            solver=kwargs["solver"],
        )
        self.label_encoder = LabelEncoder()

    def train(
        self,
        x,
        y,
        x_validation=None,
        y_validation=None,
    ):
        input_col = x.column_names[0]
        output_col = y.column_names[0]

        X_tfidf = self.vectorizer.fit_transform(x[input_col])
        y_enc = self.label_encoder.fit_transform(y[output_col])
        self.classifier.fit(X_tfidf, y_enc)

    def predict(self, x):
        input_col = x.column_names[0]
        X_tfidf = self.vectorizer.transform(x[input_col])
        return self.classifier.predict_proba(X_tfidf)

    def prepare_output(self, dataset: "DashAIDataset", is_fit: bool = False):
        from datasets import Dataset as HFDataset

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        col = dataset.column_names[0]
        if is_fit:
            encoded = self.label_encoder.fit_transform(dataset[col]).tolist()
        else:
            encoded = self.label_encoder.transform(dataset[col]).tolist()
        return to_dashai_dataset(HFDataset.from_dict({col: encoded}))

    def save(self, filename: Union[str, "Path"]) -> None:
        import joblib

        joblib.dump(self, filename)

    @staticmethod
    def load(filename: Union[str, "Path"]):
        import joblib

        return joblib.load(filename)
