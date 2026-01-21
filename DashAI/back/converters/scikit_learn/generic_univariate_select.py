import pyarrow as pa
from sklearn.feature_selection import (
    GenericUnivariateSelect as GenericUnivariateSelectOperation,
)

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class GenericUnivariateSelectSchema(BaseSchema):
    mode: schema_field(
        enum_field(["percentile", "k_best", "fpr", "fdr", "fwe"]),
        "percentile",
        description=MultilingualString(
            en="Select features according to a percentile of the highest scores.",
            es=(
                "Selecciona características según un percentil de las "
                "puntuaciones más altas."
            ),
        ),
    )  # type: ignore
    param: schema_field(
        none_type(
            union_type(enum_field(["all"]), union_type(float_field(), int_field()))
        ),
        1e-5,
        description=MultilingualString(
            en="Parameter of the mode.",
            es="Parámetro del modo.",
        ),
    )  # type: ignore


class GenericUnivariateSelect(
    FeatureSelectionConverter, SklearnWrapper, GenericUnivariateSelectOperation
):
    """SciKit-Learn's GenericUnivariateSelect wrapper for DashAI."""

    SCHEMA = GenericUnivariateSelectSchema
    DESCRIPTION = MultilingualString(
        en="Univariate feature selector with configurable strategy.",
        es="Selector univariante de características con estrategia configurable.",
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(
        en="Generic Univariate Select", es="Selección Univariante Genérica"
    )
    IMAGE_PREVIEW = "generic_univariate_select.png"
    metadata = {}
    CATEGORY = MultilingualString(
        en="Feature Selection", es="Selección de Características"
    )

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float64 as the output type for selected features."""
        return Float(arrow_type=pa.float64())
