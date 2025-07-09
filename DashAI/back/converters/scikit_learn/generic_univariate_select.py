from sklearn.feature_selection import (
    GenericUnivariateSelect as GenericUnivariateSelectOperation,
)

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class GenericUnivariateSelectSchema(BaseSchema):
    mode: schema_field(
        enum_field(["percentile", "k_best", "fpr", "fdr", "fwe"]),
        "percentile",
        "Select features according to a percentile of the highest scores.",
    )  # type: ignore
    param: schema_field(
        none_type(
            union_type(enum_field(["all"]), union_type(float_field(), int_field()))
        ),
        1e-5,
        "Parameter of the mode.",
    )  # type: ignore


class GenericUnivariateSelect(SklearnWrapper, GenericUnivariateSelectOperation):
    """SciKit-Learn's GenericUnivariateSelect wrapper for DashAI."""

    SCHEMA = GenericUnivariateSelectSchema
    DESCRIPTION = "Univariate feature selector with configurable strategy."
