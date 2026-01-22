import pyarrow as pa
from sklearn.preprocessing import MaxAbsScaler as MaxAbsScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class MaxAbsScalerSchema(BaseSchema):
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Set to False to perform inplace scaling.",
            es="Ponlo en False para realizar el escalado in situ.",
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore


class MaxAbsScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, MaxAbsScalerOperation
):
    """Scikit-learn's MaxAbsScaler wrapper for DashAI."""

    SCHEMA = MaxAbsScalerSchema
    DESCRIPTION = MultilingualString(
        en="Scale each feature by its maximum absolute value.",
        es="Escala cada característica por su valor absoluto máximo.",
    )
    DISPLAY_NAME = MultilingualString(en="Max Abs Scaler", es="Escalador Max Abs")
    IMAGE_PREVIEW = "max_abs_scaler.png"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for scaled data."""
        return Float(arrow_type=pa.float64())
