import pyarrow as pa
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
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


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
    SUPERVISED = True
    DISPLAY_NAME = "Generic Univariate Select"
    metadata = {}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
