from sklearn.feature_selection import (
    SelectKBest as SelectKBestOperation,
)

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class SelectKBestSchema(BaseSchema):
    k: schema_field(
        union_type(enum_field(["all"]), int_field(ge=1)),
        10,
        "Number of top features to select.",
    )  # type: ignore


class SelectKBest(SklearnWrapper, SelectKBestOperation):
    """SciKit-Learn's SelectKBest wrapper for DashAI."""

    SCHEMA = SelectKBestSchema
    DESCRIPTION = "Select features according to the k highest scores."
