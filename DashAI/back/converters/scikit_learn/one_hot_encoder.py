from sklearn.preprocessing import OneHotEncoder as OneHotEncoderOperation

from DashAI.back.api.utils import cast_string_to_type, parse_string_to_list
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class OneHotEncoderSchema(BaseSchema):
    categories: schema_field(
        string_field(),  # ‘auto’ or a list of array-like
        "auto",
        "The categories of each feature.",
    )  # type: ignore
    drop: schema_field(
        none_type(
            string_field()
        ),  # {‘first’, ‘if_binary’} or an array-like of shape (n_features,)
        None,
        "Specifies a methodology to use to drop one of the categories per feature.",
    )  # type: ignore
    # sparse_output: Sparse output is not supported in pandas
    dtype: schema_field(
        enum_field(["int", "np.float32", "np.float64"]),  # number type
        "np.float64",
        "Desired dtype of output.",
    )  # type: ignore
    handle_unknown: schema_field(
        enum_field(["error", "ignore", "infrequent_if_exist"]),
        "error",
        (
            "Whether to raise an error or ignore if an unknown categorical feature "
            "is present during transform."
        ),
    )  # type: ignore
    min_frequency: schema_field(
        none_type(union_type(int_field(ge=0), float_field(ge=0.0, le=1.0))),
        None,
        "Minimum frequency of a category to be considered as frequent.",
    )  # type: ignore
    max_categories: schema_field(
        none_type(int_field(ge=1)),
        None,
        "Maximum number of categories to encode.",
    )  # type: ignore
    # Added in version 1.3
    feature_name_combiner: schema_field(
        enum_field(
            [
                "concat",
            ]
        ),  # “concat” or callable
        "concat",
        "Method used to combine feature names.",
    )  # type: ignore


class OneHotEncoder(SklearnWrapper, OneHotEncoderOperation):
    """Scikit-learn's OneHotEncoder wrapper for DashAI."""

    SCHEMA = OneHotEncoderSchema
    DESCRIPTION = "Encode categorical integer features as a one-hot numeric array."

    def __init__(self, **kwargs):
        self.categories = kwargs.pop("categories", "auto")
        if self.categories != "auto":
            self.categories = [parse_string_to_list(self.categories)]
        kwargs["categories"] = self.categories

        self.drop = kwargs.pop("drop", None)
        if self.drop is not None and self.drop != "first" and self.drop != "if_binary":
            self.drop = [parse_string_to_list(self.drop)]
        kwargs["drop"] = self.drop

        self.dtype = kwargs.pop("dtype", "np.float64")
        self.dtype = cast_string_to_type(self.dtype)
        kwargs["dtype"] = self.dtype

        # Pandas output does not support sparse data. Set sparse_output=False
        self.sparse_output = kwargs.pop("sparse_output", False)
        kwargs["sparse_output"] = self.sparse_output

        super().__init__(**kwargs)
