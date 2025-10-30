from sklearn.preprocessing import MaxAbsScaler as MaxAbsScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class MaxAbsScalerSchema(BaseSchema):
    use_copy: schema_field(
        bool_field(),
        True,
        "Set to False to perform inplace scaling.",
        alias="copy",
    )  # type: ignore


class MaxAbsScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, MaxAbsScalerOperation
):
    """Scikit-learn's MaxAbsScaler wrapper for DashAI."""

    SCHEMA = MaxAbsScalerSchema
    DESCRIPTION = "Scale each feature by its maximum absolute value."
    CATEGORY = "Scaling & Normalization"
    DISPLAY_NAME = "Max Abs Scaler"
    IMAGE_PREVIEW = "max_abs_scaler.png"
