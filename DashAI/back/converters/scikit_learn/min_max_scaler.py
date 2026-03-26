from sklearn.preprocessing import MinMaxScaler as MinMaxScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class MinMaxScalerSchema(BaseSchema):
    min_range: schema_field(
        float_field(ge=0),
        0,
        description=MultilingualString(
            en="The minimum value of the range to scale the data to.",
            es="El valor mínimo del rango al que escalar los datos.",
        ),
    )  # type: ignore
    max_range: schema_field(
        float_field(ge=0),
        1,
        description=MultilingualString(
            en="The maximum value of the range to scale the data to.",
            es="El valor máximo del rango al que escalar los datos.",
        ),
    )  # type: ignore
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Set to False to perform inplace row normalization.",
            es="Ponlo en False para normalizar filas in situ.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore
    clip: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en="Set to True to clip the data to the feature range.",
            es="Ponlo en True para recortar los datos al rango de características.",
        ),
    )  # type: ignore


class MinMaxScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, MinMaxScalerOperation
):
    """Scikit-learn's MinMaxScaler wrapper for DashAI."""

    SCHEMA = MinMaxScalerSchema
    DESCRIPTION = MultilingualString(
        en="Transform features by scaling each feature to a given range.",
        es="Transforma características escalándolas a un rango dado.",
    )
    DISPLAY_NAME = MultilingualString(en="Min-Max Scaler", es="Escalador Min-Max")
    IMAGE_PREVIEW = "min_max_scaler.png"

    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

    def __init__(self, **kwargs):
        self.min_range = kwargs.pop("min_range", 0)
        self.max_range = kwargs.pop("max_range", 1)
        kwargs["feature_range"] = (self.min_range, self.max_range)
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for scaled data."""
        import pyarrow as pa

        return Float(arrow_type=pa.float64())
