import pyarrow as pa
from sklearn.preprocessing import StandardScaler as StandardScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class StandardScalerSchema(BaseSchema):
    use_copy: schema_field(
        bool_field(),
        True,
        "If False, try to avoid a copy and do inplace scaling instead.",
        alias="copy",
    )  # type: ignore
    with_mean: schema_field(
        bool_field(),
        True,
        "If True, center the data before scaling.",
    )  # type: ignore
    with_std: schema_field(
        bool_field(),
        True,
        (
            "If True, scale the data to unit variance (or equivalently, unit "
            "standard deviation)."
        ),
    )  # type: ignore


class StandardScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, StandardScalerOperation
):
    """Scikit-learn's Standard Scaler wrapper for DashAI."""

    SCHEMA = StandardScalerSchema
    DESCRIPTION = (
        "Standardize features by removing the mean and scaling to unit variance."
    )
    CATEGORY = "Scaling & Normalization"
    DISPLAY_NAME = "Standard Scaler"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for standardized data."""
        return Float(arrow_type=pa.float64())

    IMAGE_PREVIEW = "standard_scaler.png"
