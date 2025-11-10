import pyarrow as pa
from sklearn.feature_selection import VarianceThreshold as VarianceThresholdOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class VarianceThresholdSchema(BaseSchema):
    threshold: schema_field(
        float_field(ge=0.0),
        0.0,
        "Features with a variance lower than this threshold will be removed.",
    )  # type: ignore


class VarianceThreshold(SklearnWrapper, VarianceThresholdOperation):
    """Scikit-learn's VarianceThreshold wrapper for DashAI."""

    SCHEMA = VarianceThresholdSchema
    DESCRIPTION = "Feature selector that removes all low-variance features."
    DISPLAY_NAME = "Variance Threshold"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
