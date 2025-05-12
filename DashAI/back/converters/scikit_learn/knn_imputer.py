from sklearn.impute import KNNImputer as KNNImputerOperation

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


class KNNImputerSchema(BaseSchema):
    missing_values: schema_field(
        none_type(
            union_type(int_field(), union_type(float_field(), string_field()))
        ),  # int, float, str, np.nan or None
        None,  # np.nan,
        "The placeholder for the missing values.",
    )  # type: ignore
    n_neighbors: schema_field(
        int_field(ge=1),
        5,
        "The number of nearest neighbors to use for imputation.",
    )  # type: ignore
    weights: schema_field(
        enum_field(["uniform", "distance"]),  # {‘uniform’, ‘distance’} or callable
        "uniform",
        "The weight function to use for imputation.",
    )  # type: ignore
    metric: schema_field(
        enum_field(["nan_euclidean"]),  # {‘nan_euclidean‘} or callable
        "nan_euclidean",
        "The metric to use for imputation.",
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


class KNNImputer(SklearnWrapper, KNNImputerOperation):
    """Scikit-learn's KNNImputer wrapper for DashAI."""

    SCHEMA = KNNImputerSchema
    DESCRIPTION = "Imputation for completing missing values using k-Nearest Neighbors."

    def __init__(self, **kwargs):
        self.missing_values = kwargs.pop("missing_values", None)
        self.missing_values = cast_string_to_type(self.missing_values)
        kwargs["missing_values"] = self.missing_values

        super().__init__(**kwargs)
