import pyarrow as pa
from sklearn.kernel_approximation import SkewedChi2Sampler as SkewedChi2SamplerOperation

from DashAI.back.api.utils import create_random_state
from DashAI.back.converters.category.polynomial_kernel import PolynomialKernelConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SkewedChi2SamplerSchema(BaseSchema):
    skewedness: schema_field(
        float_field(gt=0),
        1.0,
        description=MultilingualString(
            en="The skewedness parameter of the chi-squared kernel.",
            es="El parámetro de sesgo del kernel chi-cuadrado.",
        ),
    )  # type: ignore
    n_components: schema_field(
        int_field(ge=1),
        100,
        description=MultilingualString(
            en=(
                "Number of Monte Carlo samples per original feature. Equals the "
                "dimensionality of the computed feature space."
            ),
            es=(
                "Número de muestras de Monte Carlo por característica original. "
                "Equivale a la dimensionalidad del espacio de características "
                "calculado."
            ),
        ),
    )  # type: ignore
    random_state: schema_field(
        none_type(union_type(int_field(), enum_field(["RandomState"]))),
        None,
        description=MultilingualString(
            en=(
                "Pseudo-random number generator to control the generation of the "
                "random weights and random offset when fitting the training data. "
                "Pass an int for reproducible output across multiple function calls."
            ),
            es=(
                "Generador pseudoaleatorio para controlar la generación de pesos y "
                "desplazamientos aleatorios al ajustar los datos. Pasa un entero "
                "para obtener resultados reproducibles."
            ),
        ),
    )  # type: ignore


class SkewedChi2Sampler(
    PolynomialKernelConverter, SklearnWrapper, SkewedChi2SamplerOperation
):
    """Scikit-learn's SkewedChi2Sampler wrapper for DashAI."""

    SCHEMA = SkewedChi2SamplerSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Approximates the feature map of a chi-squared kernel by Monte Carlo "
            "approximation of its Fourier transform."
        ),
        es=(
            "Aproxima el mapa de características de un kernel chi-cuadrado "
            "mediante la aproximación de Monte Carlo de su transformada de Fourier."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Skewed Chi² Sampler", es="Muestreador Chi²")
    IMAGE_PREVIEW = "skewed_chi_2_sampler.png"

    def __init__(self, **kwargs):
        self.random_state = kwargs.pop("random_state", None)
        if self.random_state == "RandomState":
            self.random_state = create_random_state()
        kwargs["random_state"] = self.random_state

        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for transformed data."""
        return Float(arrow_type=pa.float64())
