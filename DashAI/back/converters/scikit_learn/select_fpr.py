import pyarrow as pa
from sklearn.feature_selection import SelectFpr as SelectFprOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectFprSchema(BaseSchema):
    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        description=MultilingualString(
            en="The highest p-value for features to be kept.",
            es="El p-valor más alto para conservar características.",
        ),
    )  # type: ignore


class SelectFpr(FeatureSelectionConverter, SklearnWrapper, SelectFprOperation):
    """SciKit-Learn's SelectFpr wrapper for DashAI."""

    SCHEMA = SelectFprSchema
    DESCRIPTION = MultilingualString(
        en="Filter: Select features according to a false positive rate test.",
        es=(
            "Filtro: Selecciona características según una prueba de tasa de "
            "falsos positivos (FPR)."
        ),
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(en="Select FPR", es="Seleccionar FPR")
    IMAGE_PREVIEW = "select_fpr.png"
    metadata = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
