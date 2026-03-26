from sklearn.feature_selection import VarianceThreshold as VarianceThresholdOperation

from DashAI.back.converters.category.dimensionality_reduction import (
    DimensionalityReductionConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class VarianceThresholdSchema(BaseSchema):
    threshold: schema_field(
        float_field(ge=0.0),
        0.0,
        description=MultilingualString(
            en=("Features with a variance lower than this threshold will be removed."),
            es=(
                "Se eliminarán las características con una varianza inferior "
                "a este umbral."
            ),
        ),
    )  # type: ignore


class VarianceThreshold(
    DimensionalityReductionConverter, SklearnWrapper, VarianceThresholdOperation
):
    """Scikit-learn's VarianceThreshold wrapper for DashAI."""

    SCHEMA = VarianceThresholdSchema
    DESCRIPTION = MultilingualString(
        en="Feature selector that removes all low-variance features.",
        es="Selector de características que elimina todas las de baja varianza.",
    )
    DISPLAY_NAME = MultilingualString(en="Variance Threshold", es="Umbral de Varianza")

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

    IMAGE_PREVIEW = "variance_threshold.png"
