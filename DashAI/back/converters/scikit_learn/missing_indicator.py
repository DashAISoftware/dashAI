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
    pass


class MissingIndicator(
    BasicPreprocessingConverter, SklearnWrapper, MissingIndicatorOperation
):
    """Add binary indicator columns flagging which values were originally missing.

    For each feature with missing values, a new column is added containing 1
    where the original value was NaN and 0 otherwise. Commonly used alongside
    an imputer to preserve missingness information.

    Wraps scikit-learn's ``MissingIndicator``.
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
