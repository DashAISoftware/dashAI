from sklearn.feature_selection import SelectFwe as SelectFweOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectFweSchema(BaseSchema):
    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        description=MultilingualString(
            en="The highest uncorrected p-value for features to be kept.",
            es=(
                "El p-valor sin corregir más alto para que una característica "
                "sea conservada."
            ),
        ),
    )  # type: ignore


class SelectFwe(FeatureSelectionConverter, SklearnWrapper, SelectFweOperation):
    """Scikit-learn's SelectFwe wrapper for DashAI."""

    SCHEMA = SelectFweSchema
    DESCRIPTION = MultilingualString(
        en="Filter: Select features according to a family-wise error rate test.",
        es=(
            "Filtro: Selecciona características según una prueba de tasa de "
            "error familiar (FWE)."
        ),
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(en="Select FWE", es="Seleccionar FWE")
    IMAGE_PREVIEW = "select_fwe.png"
    metadata = {}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        import pyarrow as pa

        return Float(arrow_type=pa.float64())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
