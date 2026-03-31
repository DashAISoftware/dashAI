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
    """Select features whose p-value falls below a False Positive Rate threshold.

    Retains features with a p-value below ``alpha`` under the null hypothesis
    of independence from the target. Supervised: requires ``y`` at fit time.

    Wraps scikit-learn's ``SelectFPR``.
    """

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
        """Initialize the SelectFpr converter.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        super().__init__(**kwargs)

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
