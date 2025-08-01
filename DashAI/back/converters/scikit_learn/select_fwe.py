from sklearn.feature_selection import (
    SelectFwe as SelectFweOperation,
)

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    float_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class SelectFweSchema(BaseSchema):
    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        "The highest uncorrected p-value for features to be kept.",
    )  # type: ignore


class SelectFwe(SklearnWrapper, SelectFweOperation):
    """Scikit-learn's SelectFwe wrapper for DashAI."""

    SCHEMA = SelectFweSchema
    DESCRIPTION = "Filter: Select features according to a family-wise error rate test."
