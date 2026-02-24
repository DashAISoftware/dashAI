import pyarrow as pa
from sklearn.kernel_approximation import (
    AdditiveChi2Sampler as AdditiveChi2SamplerOperation,
)

from DashAI.back.converters.category.polynomial_kernel import PolynomialKernelConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    float_field,
    int_field,
    none_type,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class AdditiveChi2SamplerSchema(BaseSchema):
    sample_steps: schema_field(
        int_field(ge=1),
        2,
        description=MultilingualString(
            en="The number of sample steps (shuffling) to perform.",
            es="Número de pasos de muestreo (mezcla) a realizar.",
        ),
    )  # type: ignore
    sample_interval: schema_field(
        none_type(float_field(ge=1.0)),
        None,
        description=MultilingualString(
            en="The number of samples generated between each original sample.",
            es="Número de muestras generadas entre cada muestra original.",
        ),
    )  # type: ignore


class AdditiveChi2Sampler(
    PolynomialKernelConverter, SklearnWrapper, AdditiveChi2SamplerOperation
):
    """Scikit-learn's AdditiveChi2Sampler wrapper for DashAI."""

    SCHEMA = AdditiveChi2SamplerSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Uses sampling the Fourier transform of the kernel characteristic "
            "at regular intervals."
        ),
        es=(
            "Utiliza muestreo de la transformada de Fourier de la función kernel "
            "a intervalos regulares."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Additive Chi² Sampler", es="Muestreador Chi²")
    IMAGE_PREVIEW = "additive_chi2_sampler.png"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for transformed data."""
        return Float(arrow_type=pa.float64())
