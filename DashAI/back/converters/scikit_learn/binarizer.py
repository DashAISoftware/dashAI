from sklearn.preprocessing import Binarizer as BinarizerOperation

from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class BinarizerSchema(BaseSchema):
    threshold: schema_field(
        float_field(),
        0.0,
        description=MultilingualString(
            en=(
                "Feature values below or equal to this are replaced by 0, "
                "above it by 1."
            ),
            es=(
                "Los valores por debajo o igual al umbral se reemplazan por 0; "
                "los superiores por 1."
            ),
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Set to False to perform inplace binarization.",
            es="Ponlo en False para binarizar in situ.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore


class Binarizer(EncodingConverter, SklearnWrapper, BinarizerOperation):
    """Scikit-learn's Binarizer wrapper for DashAI."""

    SCHEMA = BinarizerSchema
    DESCRIPTION = MultilingualString(
        en=("Binarize data (set feature values to 0 or 1) according to a threshold."),
        es=(
            "Binariza datos (pone valores de características en 0 o 1) según un umbral."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Binarizer", es="Binarizador")
    IMAGE_PREVIEW = "binarizer.png"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Integer64 as the output type for binarized data."""
        import pyarrow as pa

        return Integer(arrow_type=pa.int64())
