from sklearn.feature_selection import (
    SelectFpr as SelectFprOperation,
)

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    float_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class SelectFprSchema(BaseSchema):
    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        "The highest p-value for features to be kept.",
    )  # type: ignore


class SelectFpr(SklearnWrapper, SelectFprOperation):
    """SciKit-Learn's SelectFpr wrapper for DashAI."""

    SCHEMA = SelectFprSchema
    DESCRIPTION = "Filter: Select features according to a false positive rate test."
