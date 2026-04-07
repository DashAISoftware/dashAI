from sklearn.preprocessing import LabelBinarizer as LabelBinarizerOperation

from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class LabelBinarizerSchema(BaseSchema):
    """Schema for LabelBinarizer hyperparameters.

    Configures the integer values used to represent the negative and positive
    classes in the binary indicator matrix produced by sklearn's
    ``LabelBinarizer``. Both ``neg_label`` and ``pos_label`` must be integers,
    and ``pos_label`` must be strictly greater than ``neg_label``.
    """

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
    """Binarize a label column into a one-vs-all binary indicator matrix.

    Given a flat array of class labels, this converter produces a 2-D
    integer matrix in which each column corresponds to one class. For a
    sample belonging to class ``k``, column ``k`` is set to ``pos_label``
    and all other columns are set to ``neg_label``:

    * **Binary classification** — the output is a single column (shape
      ``(n_samples, 1)``) because one column is sufficient to encode two
      classes.
    * **Multiclass classification** — the output has one column per class
      (shape ``(n_samples, n_classes)``).

    Label binarization is required by classifiers that natively expect a
    binary indicator matrix for their targets (e.g. multi-label SVMs), and
    is useful for computing one-vs-all metrics directly on the raw output.

    References
    ----------
    - [1] https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.LabelBinarizer.html
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

    metadata = {
        "allowed_dtypes": ["string"],
        "restricted_dtypes": [],
    }

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
