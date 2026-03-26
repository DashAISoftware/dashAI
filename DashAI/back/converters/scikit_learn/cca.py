from sklearn.cross_decomposition import CCA as CCAOPERATION

from DashAI.back.converters.category.advanced_preprocessing import (
    AdvancedPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class CCASchema(BaseSchema):
    n_components: schema_field(
        int_field(ge=1),
        2,
        description=MultilingualString(
            en="Number of components to keep.",
            es="Número de componentes a conservar.",
        ),
    )  # type: ignore
    scale: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Whether to scale the data.",
            es="Si se deben escalar los datos.",
        ),
    )  # type: ignore
    max_iter: schema_field(
        int_field(ge=1),
        500,
        description=MultilingualString(
            en="Maximum number of iterations to perform.",
            es="Número máximo de iteraciones a realizar.",
        ),
    )  # type: ignore
    tol: schema_field(
        float_field(ge=0.0),
        1e-6,
        description=MultilingualString(
            en="Tolerance for the stopping condition.",
            es="Tolerancia para la condición de parada.",
        ),
    )  # type: ignore
    copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Whether to copy X and Y or perform in-place normalization.",
            es="Si copiar X e Y o normalizar in situ.",
        ),
    )  # type: ignore


class CCA(AdvancedPreprocessingConverter, SklearnWrapper, CCAOPERATION):
    """Scikit-learn's CCA wrapper for DashAI."""

    SCHEMA = CCASchema
    DESCRIPTION = MultilingualString(
        en="Canonical Correlation Analysis, also known as 'Mode B' PLS.",
        es="Análisis de Correlación Canónica, también conocido como PLS 'Modo B'.",
    )
    DISPLAY_NAME = MultilingualString(en="CCA", es="CCA")

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for transformed data."""
        import pyarrow as pa

        return Float(arrow_type=pa.float64())
