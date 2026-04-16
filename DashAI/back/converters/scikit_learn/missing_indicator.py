from sklearn.impute import MissingIndicator as MissingIndicatorOperation

from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class MissingIndicatorSchema(BaseSchema):
    """Schema for configuring the MissingIndicator converter.

    Wraps ``sklearn.impute.MissingIndicator``. The current configuration uses
    default scikit-learn settings (all features with missing values are
    indicated, NaN is treated as the missing marker). No additional schema
    fields are exposed; the class is kept as a stub to satisfy the DashAI
    component interface.
    """


class MissingIndicator(
    BasicPreprocessingConverter, SklearnWrapper, MissingIndicatorOperation
):
    """Add binary indicator columns that flag which values were originally missing.

    For each feature that contains at least one NaN in the training data, a
    new binary column is appended to the output. The indicator column contains
    1 where the original value was missing and 0 otherwise.

    This converter is typically stacked onto an imputer (via the imputer's
    ``add_indicator=True`` option, or explicitly in a pipeline) so that the
    model can distinguish between "value was imputed" and "value was genuinely
    observed". Preserving missingness patterns can improve downstream model
    accuracy when data is not missing completely at random (MCAR). Output
    columns are typed as ``Integer`` (``int64``) in DashAI.

    Wraps ``sklearn.impute.MissingIndicator``.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.impute.MissingIndicator.html
    """

    SCHEMA = MissingIndicatorSchema
    DESCRIPTION = MultilingualString(
        en="Binary indicators for missing values.",
        es="Indicadores binarios para valores faltantes.",
    )
    DISPLAY_NAME = MultilingualString(
        en="Missing Indicator", es="Indicador de Faltantes"
    )
    IMAGE_PREVIEW = "missing_indicator.png"

    def __init__(self, **kwargs):
        """Initialize the MissingIndicator converter.

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
            An Integer type backed by ``pyarrow.int64()``,
            representing binary 0/1 missingness flags.
        """
        import pyarrow as pa

        return Integer(arrow_type=pa.int64())
