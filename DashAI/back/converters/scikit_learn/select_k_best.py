import pyarrow as pa
from sklearn.feature_selection import SelectKBest as SelectKBestOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectKBestSchema(BaseSchema):
    k: schema_field(
        union_type(enum_field(["all"]), int_field(ge=1)),
        10,
        description=MultilingualString(
            en="Number of top features to select.",
            es="Número de características superiores a seleccionar.",
        ),
    )  # type: ignore


class SelectKBest(FeatureSelectionConverter, SklearnWrapper, SelectKBestOperation):
    """SciKit-Learn's SelectKBest wrapper for DashAI."""

    SCHEMA = SelectKBestSchema
    DESCRIPTION = MultilingualString(
        en="Select features according to the k highest scores.",
        es="Selecciona características según las k puntuaciones más altas.",
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(en="Select K Best", es="Seleccionar K Mejores")
    IMAGE_PREVIEW = "select_k_best.png"
    metadata = {}

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())

    def __init__(self, **kwargs):
        if callable(self._get_tags):
            original_get_tags = self._get_tags
            self._get_tags = lambda *a, **k: {
                **original_get_tags(*a, **k),
                "requires_y": True,
            }
        else:
            self._get_tags = {**self._get_tags, "requires_y": True}
        super().__init__(**kwargs)
