import pyarrow as pa
from sklearn.preprocessing import MaxAbsScaler as MaxAbsScalerOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class MaxAbsScalerSchema(BaseSchema):
    use_copy: schema_field(
        bool_field(),
        True,
        "Set to False to perform inplace scaling.",
        alias="copy",
    )  # type: ignore


class MaxAbsScaler(SklearnWrapper, MaxAbsScalerOperation):
    """Scikit-learn's MaxAbsScaler wrapper for DashAI."""

    SCHEMA = MaxAbsScalerSchema
    DESCRIPTION = "Scale each feature by its maximum absolute value."
    DISPLAY_NAME = "Max Abs Scaler"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for scaled data."""
        return Float(arrow_type=pa.float64())
