import pyarrow as pa
from sklearn.preprocessing import Normalizer as NormalizerOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, enum_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class NormalizerSchema(BaseSchema):
    norm: schema_field(
        enum_field(["l1", "l2", "max"]),
        "l2",
        "The norm to use to normalize each non zero sample.",
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        "Set to False to perform inplace row normalization.",
        alias="copy",
    )  # type: ignore


class Normalizer(SklearnWrapper, NormalizerOperation):
    """Scikit-learn's Normalizer wrapper for DashAI."""

    SCHEMA = NormalizerSchema
    DESCRIPTION = "Normalize samples individually to unit norm."
    DISPLAY_NAME = "Normalizer"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for normalized data."""
        return Float(arrow_type=pa.float64())
