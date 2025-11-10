import pyarrow as pa
from sklearn.feature_selection import SelectKBest as SelectKBestOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectKBestSchema(BaseSchema):
    k: schema_field(
        union_type(enum_field(["all"]), int_field(ge=1)),
        10,
        "Number of top features to select.",
    )  # type: ignore


class SelectKBest(SklearnWrapper, SelectKBestOperation):
    """SciKit-Learn's SelectKBest wrapper for DashAI."""

    SCHEMA = SelectKBestSchema
    DESCRIPTION = "Select features according to the k highest scores."
    SUPERVISED = True
    DISPLAY_NAME = "Select K Best"
    metadata = {}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
