from sklearn.preprocessing import OrdinalEncoder as OrdinalEncoderOperation

from DashAI.back.api.utils import cast_nan_or_int_types, cast_numpy_types
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    schema_field,
    none_type,
    union_type,
    int_field,
    float_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class OrdinalEncoderSchema(BaseSchema):
    categories: schema_field(
        string_field(),  # "auto" or a list of array-like
        "auto",
        "Categories (unique values) per feature.",
    )  # type: ignore
    dtype: schema_field(
        enum_field(["np.int32", "np.int64", "np.float32", "np.float64"]), # number type
        "np.float64",
        "Desired dtype of output.",
    )  # type: ignore
    handle_unknown: schema_field(
        enum_field(["error", "use_encoded_value"]),
        "error",
        "Whether to raise an error or ignore if an unknown categorical feature is present during transform.",
    )  # type: ignore
    unknown_value: schema_field(
        none_type(
            enum_field(["int", "np.nan"]), # int or np.nan
        ),
        None,
        "The value to use for unknown categories.",
    )  # type: ignore
    encoded_missing_values: schema_field(
        enum_field(["int", "np.nan"]), # int or np.nan
        "np.nan",
        "Encoded value of missing categories.",
    )  # type: ignore
    # Added in version 1.3
    min_frequency: schema_field(
        none_type(union_type(int_field(ge=1), float_field(ge=0.0, le=1.0))),
        None,
        "Minimum frequency of a category to be considered as frequent.",
    )  # type: ignore
    # Added in version 1.3
    max_categories: schema_field(
        none_type(int_field(ge=1)),
        None,
        "Maximum number of categories to encode.",
    )  # type: ignore


class OrdinalEncoder(SklearnWrapper, OrdinalEncoderOperation):
    """Scikit-learn's OrdinalEncoder wrapper for DashAI."""

    SCHEMA = OrdinalEncoderSchema
    DESCRIPTION = "Encode categorical features as an integer array."

    def __init__(self, **kwargs):
        self.dtype = kwargs.pop("dtype", "np.float64")
        self.dtype = cast_numpy_types(self.dtype)
        kwargs["dtype"] = self.dtype

        self.unknown_value = kwargs.pop("unknown_value", None)
        if self.unknown_value is not None:
            self.unknown_value = cast_nan_or_int_types(self.unknown_value)
        kwargs["unknown_value"] = self.unknown_value

        self.encoded_missing_values = kwargs.pop("encoded_missing_values", "np.nan")
        self.encoded_missing_values = cast_nan_or_int_types(self.encoded_missing_values)
        kwargs["encoded_missing_values"] = self.encoded_missing_values

        self.min_frequency = kwargs.pop("min_frequency", None)
        if self.min_frequency is not None:
            self.min_frequency = cast_nan_or_int_types(self.min_frequency)
        kwargs["min_frequency"] = self.min_frequency

        super().__init__(**kwargs)
