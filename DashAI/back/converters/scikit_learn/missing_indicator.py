from sklearn.impute import MissingIndicator as MissingIndicatorOperation

from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields.base_schema import BaseSchema


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
