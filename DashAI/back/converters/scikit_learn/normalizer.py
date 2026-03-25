from sklearn.preprocessing import Normalizer as NormalizerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, enum_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class NormalizerSchema(BaseSchema):
    norm: schema_field(
        enum_field(["l1", "l2", "max"]),
        "l2",
        description=MultilingualString(
            en="The norm to use to normalize each non-zero sample.",
            es="La norma a usar para normalizar cada muestra no nula.",
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Set to False to perform inplace row normalization.",
            es="Ponlo en False para normalizar filas in situ.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore


class Normalizer(ScalingAndNormalizationConverter, SklearnWrapper, NormalizerOperation):
    """Scikit-learn's Normalizer wrapper for DashAI."""

    SCHEMA = NormalizerSchema
    DESCRIPTION = MultilingualString(
        en="Normalize samples individually to unit norm.",
        es="Normaliza muestras individualmente a norma unitaria.",
    )
    DISPLAY_NAME = MultilingualString(en="Normalizer", es="Normalizador")
    IMAGE_PREVIEW = "normalizer.png"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for normalized data."""
        import pyarrow as pa

        return Float(arrow_type=pa.float64())
