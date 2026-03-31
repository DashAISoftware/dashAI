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
    """Remove features whose variance falls below a threshold.

    Features with low variance carry little information and can be removed
    without supervised labels. A threshold of 0.0 removes features that are
    constant across all samples. Unsupervised.

    Wraps scikit-learn's ``VarianceThreshold``.
    """

    SCHEMA = VarianceThresholdSchema
    DESCRIPTION = MultilingualString(
        en="Feature selector that removes all low-variance features.",
        es="Selector de características que elimina todas las de baja varianza.",
    )
    DISPLAY_NAME = MultilingualString(en="Variance Threshold", es="Umbral de Varianza")

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        Parameters
        ----------
        column_name : str, optional
            Not used; all output columns share the
            same type. Defaults to None.

        Returns
        -------
        DashAIDataType
            A Float type backed by ``pyarrow.float64()``.
        """
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

    IMAGE_PREVIEW = "variance_threshold.png"
