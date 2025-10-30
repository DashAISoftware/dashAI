from sklearn.feature_selection import SelectFdr as SelectFdrOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class SelectFdrSchema(BaseSchema):
    alpha: schema_field(
        float_field(ge=0.0, le=1.0),
        0.05,
        "The highest uncorrected p-value for features to be kept.",
    )  # type: ignore


class SelectFdr(FeatureSelectionConverter, SklearnWrapper, SelectFdrOperation):
    """SciKit-Learn's SelectFdr wrapper for DashAI."""

    SCHEMA = SelectFdrSchema
    DESCRIPTION = "Filter: Select features according to a false discovery rate test."
    SUPERVISED = True
    DISPLAY_NAME = "Select FDR"
    IMAGE_PREVIEW = "select_fdr.png"
    metadata = {}
    CATEGORY = "Feature Selection"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
