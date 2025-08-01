from sklearn.impute import SimpleImputer as SimpleImputerOperation

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


class SimpleImputerSchema(BaseSchema):
    missing_values: schema_field(
        none_type(
            union_type(int_field(), union_type(float_field(), string_field()))
        ),  # int, float, str, np.nan, None or pandas.NA
        None,  # np.nan,
        "The placeholder for the missing values.",
    )  # type: ignore
    strategy: schema_field(
        enum_field(["mean", "median", "most_frequent", "constant"]),
        "mean",
        "The imputation strategy.",
    )  # type: ignore
    fill_value: schema_field(
        none_type(union_type(int_field(), union_type(float_field(), string_field()))),
        None,
        "The value to replace missing values with.",
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        "If True, a copy of X will be created.",
        alias="copy",
    )  # type: ignore
    add_indicator: schema_field(
        bool_field(),
        False,
        "If True, a MissingIndicator transform will stack onto output.",
    )  # type: ignore
    keep_empty_features: schema_field(
        bool_field(),
        False,
        "If True, empty features will be kept.",
    )  # type: ignore


class SimpleImputer(SklearnWrapper, SimpleImputerOperation):
    """SciKit-Learn's SimpleImputer wrapper for DashAI."""

    SCHEMA = SimpleImputerSchema
    DESCRIPTION = (
        "Univariate imputer for completing missing values with simple strategies."
    )

    def __init__(self, **kwargs):
        self.missing_values = kwargs.pop("missing_values", None)
        self.missing_values = cast_string_to_type(self.missing_values)
        kwargs["missing_values"] = self.missing_values

        super().__init__(**kwargs)
