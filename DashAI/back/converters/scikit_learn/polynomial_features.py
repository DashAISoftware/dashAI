from sklearn.preprocessing import PolynomialFeatures as PolynomialFeaturesOperation

from DashAI.back.converters.category.polynomial_kernel import PolynomialKernelConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class PolynomialFeaturesSchema(BaseSchema):
    """Schema for PolynomialFeatures hyperparameters."""

    degree: schema_field(
        int_field(ge=1),
        2,
        description=MultilingualString(
            en="The degree of the polynomial features.",
            es="El grado de las características polinomiales.",
        ),
    )  # type: ignore
    interaction_only: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en=(
                "If True, only interaction features are produced: features that "
                "are products of at most degree distinct input features."
            ),
            es=(
                "Si es True, solo se producen características de interacción: "
                "productos de hasta 'degree' características de entrada distintas."
            ),
        ),
    )  # type: ignore
    include_bias: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "If True (default), then include a bias column (a column of ones "
                "that act as an intercept term)."
            ),
            es=(
                "Si es True (por defecto), incluye una columna de sesgo (columna "
                "de unos que actúa como término independiente)."
            ),
        ),
    )  # type: ignore
    order: schema_field(
        enum_field(["C", "F"]),
        "C",
        description=MultilingualString(
            en=(
                "Order of output array in the dense case. 'F' order is faster "
                "to compute, but may slow down subsequent estimators."
            ),
            es=(
                "Orden del arreglo de salida en el caso denso. El orden 'F' es "
                "más rápido de calcular, pero puede ralentizar estimadores "
                "posteriores."
            ),
        ),
    )  # type: ignore


class PolynomialFeatures(
    PolynomialKernelConverter, SklearnWrapper, PolynomialFeaturesOperation
):
    """Generate polynomial and interaction features up to a specified degree.

    For each input feature, new columns are added for all polynomial combinations
    up to ``degree``. This enables linear models to learn nonlinear relationships
    in the original feature space without requiring kernel methods.

    Wraps scikit-learn's ``PolynomialFeatures``.
    """

    SCHEMA = PolynomialFeaturesSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Generate polynomial and interaction features. For example, if an "
            "input sample is [a, b], the degree-2 polynomial features are "
            "[1, a, b, a^2, ab, b^2]."
        ),
        es=(
            "Genera características polinomiales e interacciones. Por ejemplo, "
            "si una muestra de entrada es [a, b], las características de grado 2 "
            "son [1, a, b, a^2, ab, b^2]."
        ),
    )
    DISPLAY_NAME = MultilingualString(
        en="Polynomial Features", es="Características Polinomiales"
    )
    IMAGE_PREVIEW = "polynomial_features.png"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for polynomial features."""
        import pyarrow as pa

        return Float(arrow_type=pa.float64())
