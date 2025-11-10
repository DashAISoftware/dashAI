import pyarrow as pa
from sklearn.feature_selection import SelectPercentile as SelectPercentileOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectPercentileSchema(BaseSchema):
    percentile: schema_field(
        int_field(ge=1, le=100),
        10,
        "Percent of features to keep.",
    )  # type: ignore


class SelectPercentile(SklearnWrapper, SelectPercentileOperation):
    """SciKit-Learn's SelectPercentile wrapper for DashAI."""

    SCHEMA = SelectPercentileSchema
    DESCRIPTION = "Select features according to a percentile of the highest scores."
    SUPERVISED = True
    DISPLAY_NAME = "Select Percentile"
    metadata = {}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
