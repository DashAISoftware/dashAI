import pyarrow as pa
from sklearn.impute import MissingIndicator as MissingIndicatorOperation

from DashAI.back.api.utils import cast_string_to_type
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class MissingIndicatorSchema(BaseSchema):
    missing_values: schema_field(
        none_type(
            union_type(int_field(), union_type(float_field(), string_field()))
        ),  # int, float, str, np.nan or None
        None,  # np.nan,
        "The placeholder for the missing values.",
    )  # type: ignore
    features: schema_field(
        enum_field(["missing-only", "all"]),
        None,
        "The features to consider for missing values.",
    )  # type: ignore
    # sparse: Pandas output does not support sparse data. Set sparse=False
    error_on_new: schema_field(
        bool_field(),
        True,
        "Whether to raise an error on new missing values.",
    )  # type: ignore


class MissingIndicator(SklearnWrapper, MissingIndicatorOperation):
    """Scikit-learn's MissingIndicator wrapper for DashAI."""

    SCHEMA = MissingIndicatorSchema
    DESCRIPTION = "Binary indicators for missing values."
    DISPLAY_NAME = "Missing Indicator"

    def __init__(self, **kwargs):
        self.missing_values = kwargs.pop("missing_values", None)
        self.missing_values = cast_string_to_type(self.missing_values)
        kwargs["missing_values"] = self.missing_values

        # Pandas output does not support sparse data. Set sparse=False
        self.sparse = kwargs.pop("sparse", False)
        kwargs["sparse"] = self.sparse

        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Integer64 as the output type for binary indicators."""
        return Integer(arrow_type=pa.int64())
