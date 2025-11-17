from sklearn.feature_selection import VarianceThreshold as VarianceThresholdOperation

from DashAI.back.converters.category.dimensionality_reduction import (
    DimensionalityReductionConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class VarianceThresholdSchema(BaseSchema):
    threshold: schema_field(
        float_field(ge=0.0),
        0.0,
        "Features with a variance lower than this threshold will be removed.",
    )  # type: ignore


class VarianceThreshold(
    DimensionalityReductionConverter, SklearnWrapper, VarianceThresholdOperation
):
    """Scikit-learn's VarianceThreshold wrapper for DashAI."""

    SCHEMA = VarianceThresholdSchema
    DESCRIPTION = "Feature selector that removes all low-variance features."
    CATEGORY = "Dimensionality Reduction"
    DISPLAY_NAME = "Variance Threshold"
    IMAGE_PREVIEW = "variance_threshold.png"
