import pyarrow as pa
from sklearn.preprocessing import StandardScaler as StandardScalerOperation

from DashAI.back.converters.category.scaling_and_normalization import (
    ScalingAndNormalizationConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class StandardScalerSchema(BaseSchema):
    use_copy: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=("If False, try to avoid a copy and do inplace scaling instead."),
            es=("Si es False, intenta evitar copias y realiza la escalación in situ."),
        ),
        alias=MultilingualString(en="copy", es="copiar"),
    )  # type: ignore
    with_mean: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="If True, center the data before scaling.",
            es="Si es True, centra los datos antes de escalar.",
        ),
    )  # type: ignore
    with_std: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en=(
                "If True, scale the data to unit variance (or equivalently, "
                "unit standard deviation)."
            ),
            es=(
                "Si es True, escala los datos a varianza unitaria (o "
                "equivalentemente, desviación estándar unitaria)."
            ),
        ),
    )  # type: ignore


class StandardScaler(
    ScalingAndNormalizationConverter, SklearnWrapper, StandardScalerOperation
):
    """Scikit-learn's Standard Scaler wrapper for DashAI."""

    SCHEMA = StandardScalerSchema
    DESCRIPTION = MultilingualString(
        en=("Standardize features by removing the mean and scaling to unit variance."),
        es=(
            "Estandariza las características eliminando la media y escalando "
            "a varianza unitaria."
        ),
    )
    CATEGORY = MultilingualString(
        en="Scaling & Normalization", es="Escalado y Normalización"
    )
    DISPLAY_NAME = MultilingualString(en="Standard Scaler", es="Estandarizador")

    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for standardized data."""
        return Float(arrow_type=pa.float64())

    IMAGE_PREVIEW = "standard_scaler.png"
