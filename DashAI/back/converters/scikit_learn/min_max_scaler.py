from sklearn.preprocessing import MinMaxScaler as MinMaxScalerOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class MinMaxScalerSchema(BaseSchema):
    min_range: schema_field(
        float_field(ge=0),
        0,
        "The minimum value of the range to scale the data to.",
    )  # type: ignore
    max_range: schema_field(
        float_field(ge=0),
        1,
        "The maximum value of the range to scale the data to.",
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        "Set to False to perform inplace row normalization.",
        alias="copy",
    )  # type: ignore
    clip: schema_field(
        bool_field(),
        False,
        "Set to True to clip the data to the feature range.",
    )  # type: ignore


class MinMaxScaler(SklearnWrapper, MinMaxScalerOperation):
    """Scikit-learn's MinMaxScaler wrapper for DashAI."""

    SCHEMA = MinMaxScalerSchema
    DESCRIPTION = "Transform features by scaling each feature to a given range."

    def __init__(self, **kwargs):
        self.min_range = kwargs.pop("min_range", 0)
        self.max_range = kwargs.pop("max_range", 1)
        kwargs["feature_range"] = (self.min_range, self.max_range)
        super().__init__(**kwargs)
