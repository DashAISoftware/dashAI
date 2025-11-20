import pyarrow as pa
from sklearn.impute import MissingIndicator as MissingIndicatorOperation

from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class MissingIndicatorSchema(BaseSchema):
    pass


class MissingIndicator(
    BasicPreprocessingConverter, SklearnWrapper, MissingIndicatorOperation
):
    """Scikit-learn's MissingIndicator wrapper for DashAI."""

    CATEGORY = "Basic Preprocessing"
    SCHEMA = MissingIndicatorSchema
    DESCRIPTION = "Binary indicators for missing values."
    DISPLAY_NAME = "Missing Indicator"
    IMAGE_PREVIEW = "missing_indicator.png"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Integer64 as the output type for binary indicators."""
        return Integer(arrow_type=pa.int64())
