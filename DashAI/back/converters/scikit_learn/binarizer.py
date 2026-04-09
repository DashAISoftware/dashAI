from sklearn.preprocessing import Binarizer as BinarizerOperation

from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import float_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class BinarizerSchema(BaseSchema):
    """Schema for Binarizer hyperparameters."""

    threshold: schema_field(
        float_field(),
        0.0,
        description=MultilingualString(
            en=(
                "Feature values below or equal to this are replaced by 0, "
                "above it by 1."
            ),
            es=(
                "Los valores por debajo o igual al umbral se reemplazan por 0; "
                "los superiores por 1."
            ),
        ),
    )  # type: ignore


class Binarizer(EncodingConverter, SklearnWrapper, BinarizerOperation):
    """Threshold each feature to produce binary (0/1) values.

    Values greater than the threshold become 1; all others become 0.
    Wraps scikit-learn's ``Binarizer``.
    """

    SCHEMA = BinarizerSchema
    DESCRIPTION = MultilingualString(
        en=("Binarize data (set feature values to 0 or 1) according to a threshold."),
        es=(
            "Binariza datos (pone valores de características en 0 o 1) según un umbral."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Binarizer", es="Binarizador")
    IMAGE_PREVIEW = "binarizer.png"

    metadata = {
        "allowed_dtypes": ["int64", "float64", "float32"],
        "restricted_dtypes": [],
    }

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the DashAI data type produced by this converter for a column.

        Parameters
        ----------
        column_name : str, optional
            Not used; all output columns share the same type. Defaults to None.

        Returns
        -------
        DashAIDataType
            An Integer type backed by ``pyarrow.int64()``.
        """
        import pyarrow as pa

        return Integer(arrow_type=pa.int64())
