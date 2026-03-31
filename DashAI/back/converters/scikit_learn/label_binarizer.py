from sklearn.preprocessing import LabelBinarizer as LabelBinarizerOperation

from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class LabelBinarizerSchema(BaseSchema):
    neg_label: schema_field(
        int_field(),
        0,
        description=MultilingualString(
            en="Value with which negative labels must be encoded.",
            es="Valor con el que deben codificarse las etiquetas negativas.",
        ),
    )  # type: ignore
    pos_label: schema_field(
        int_field(),
        1,
        description=MultilingualString(
            en="Value with which positive labels must be encoded.",
            es="Valor con el que deben codificarse las etiquetas positivas.",
        ),
    )  # type: ignore


class LabelBinarizer(EncodingConverter, SklearnWrapper, LabelBinarizerOperation):
    """Binarize labels into a one-vs-all binary matrix.

    Transforms a single-column target into a binary matrix where each
    column represents one class. For binary classification the output is
    a single column; for multiclass it is a matrix with one column per class.

    Wraps scikit-learn's ``LabelBinarizer``.
    """

    SCHEMA = LabelBinarizerSchema
    DESCRIPTION = MultilingualString(
        en="Binarize labels in a one-vs-all fashion.",
        es="Binariza etiquetas en esquema uno-contra-todos.",
    )
    DISPLAY_NAME = MultilingualString(
        en="Label Binarizer", es="Binarizador de Etiquetas"
    )
    IMAGE_PREVIEW = "label_binarizer.png"

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
            representing the binary (0/1) or one-vs-all matrix values.
        """
        import pyarrow as pa

        return Integer(arrow_type=pa.int64())
