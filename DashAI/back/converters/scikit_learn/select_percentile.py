from sklearn.feature_selection import SelectPercentile as SelectPercentileOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class SelectPercentileSchema(BaseSchema):
    percentile: schema_field(
        int_field(ge=1, le=100),
        10,
        "Percent of features to keep.",
    )  # type: ignore


class SelectPercentile(
    FeatureSelectionConverter, SklearnWrapper, SelectPercentileOperation
):
    """SciKit-Learn's SelectPercentile wrapper for DashAI."""

    SCHEMA = SelectPercentileSchema
    DESCRIPTION = "Select features according to a percentile of the highest scores."
    SUPERVISED = True
    DISPLAY_NAME = "Select Percentile"
    IMAGE_PREVIEW = "select_percentile.png"
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
