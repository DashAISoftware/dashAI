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


class SelectKBestSchema(BaseSchema):
    k: schema_field(
        union_type(enum_field(["all"]), int_field(ge=1)),
        10,
        "Number of top features to select.",
    )  # type: ignore


class SelectKBest(FeatureSelectionConverter, SklearnWrapper, SelectKBestOperation):
    """SciKit-Learn's SelectKBest wrapper for DashAI."""

    SCHEMA = SelectKBestSchema
    DESCRIPTION = "Select features according to the k highest scores."
    SUPERVISED = True
    DISPLAY_NAME = "Select K Best"
    IMAGE_PREVIEW = "select_k_best.png"
    metadata = {}
    CATEGORY = "Feature Selection"

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
