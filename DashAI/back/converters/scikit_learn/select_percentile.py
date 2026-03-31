from sklearn.feature_selection import SelectPercentile as SelectPercentileOperation

from DashAI.back.converters.category.feature_selection import FeatureSelectionConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


class SelectPercentileSchema(BaseSchema):
    """Schema for Select Percentile hyperparameters."""

    percentile: schema_field(
        int_field(ge=1, le=100),
        10,
        description=MultilingualString(
            en="Percent of features to keep.",
            es="Porcentaje de características a conservar.",
        ),
    )  # type: ignore


class SelectPercentile(
    FeatureSelectionConverter, SklearnWrapper, SelectPercentileOperation
):
    """Select the top percentile of features by a univariate statistical test.

    Like ``SelectKBest`` but retains a percentage of features rather than a
    fixed count. Supervised: requires ``y`` at fit time.

    Wraps scikit-learn's ``SelectPercentile``.
    """

    SCHEMA = SelectPercentileSchema
    DESCRIPTION = MultilingualString(
        en="Select features according to a percentile of the highest scores.",
        es=(
            "Selecciona características según un percentil de las puntuaciones "
            "más altas."
        ),
    )
    SUPERVISED = True
    DISPLAY_NAME = MultilingualString(
        en="Select Percentile", es="Seleccionar Percentil"
    )
    IMAGE_PREVIEW = "select_percentile.png"
    metadata = {}

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

    def __init__(self, **kwargs):
        """Initialize the SelectPercentile converter.

        Patches ``_get_tags`` to advertise ``requires_y=True`` so that the
        pipeline passes the target array at fit time, then delegates to the
        parent initializer.

        Parameters
        ----------
        **kwargs
            Configuration keyword arguments matching the converter's
            schema fields. Forwarded to the underlying scikit-learn class.
        """
        if callable(self._get_tags):
            original_get_tags = self._get_tags
            self._get_tags = lambda *a, **k: {
                **original_get_tags(*a, **k),
                "requires_y": True,
            }
        else:
            self._get_tags = {**self._get_tags, "requires_y": True}
        super().__init__(**kwargs)
