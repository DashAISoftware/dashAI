from sklearn.dummy import DummyClassifier as _DummyClassifier

from DashAI.back.core.schema_fields import BaseSchema, enum_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class DummyClassifierSchema(BaseSchema):
    "DummyClassifier makes predictions that ignore the input features."

    strategy: schema_field(
        enum_field(enum=["most_frequent", "prior", "stratified", "uniform"]),
        placeholder="prior",
        description=MultilingualString(
            en="Strategy to use to generate predictions.",
            es="Estrategia a utilizar para generar predicciones.",
        ),
        alias=MultilingualString(en="strategy", es="estrategia"),
    )  # type: ignore


class DummyClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _DummyClassifier
):
    """Scikit-learn's DummyClassifier wrapper for DashAI."""

    SCHEMA = DummyClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Dummy Classifier",
        es="Clasificador Dummy",
    )
    DESCRIPTION: str = MultilingualString(
        en="Baseline classifier using simple rules for comparison.",
        es=("Clasificador base que utiliza reglas simples para comparación."),
    )
    COLOR: str = "#4DB6AC"
    ICON: str = "Science"

    def __init__(self, **kwargs) -> None:
        kwargs = self.validate_and_transform(kwargs)
        super().__init__(**kwargs)
