import pyarrow as pa
from sklearn.feature_selection import SelectFdr as SelectFdrOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectFdrSchema(BaseSchema):
    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        "The highest uncorrected p-value for features to be kept.",
    )  # type: ignore


class SelectFdr(SklearnWrapper, SelectFdrOperation):
    """SciKit-Learn's SelectFdr wrapper for DashAI."""

    SCHEMA = SelectFdrSchema
    DESCRIPTION = "Filter: Select features according to a false discovery rate test."
    SUPERVISED = True
    DISPLAY_NAME = "Select FDR"
    metadata = {}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
