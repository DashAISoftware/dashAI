from sklearn.feature_selection import (
    SelectPercentile as SelectPercentileOperation,
)

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


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
