import pyarrow as pa
from sklearn.preprocessing import LabelBinarizer as LabelBinarizerOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Integer


class LabelBinarizerSchema(BaseSchema):
    neg_label: schema_field(
        int_field(),
        0,
        "Value with which negative labels must be encoded.",
    )  # type: ignore
    pos_label: schema_field(
        int_field(),
        1,
        "Value with which positive labels must be encoded.",
    )  # type: ignore
    # sparse_output: Sparse output is not supported in pandas


class LabelBinarizer(SklearnWrapper, LabelBinarizerOperation):
    """Scikit-learn's LabelBinarizer wrapper for DashAI."""

    SCHEMA = LabelBinarizerSchema
    DESCRIPTION = "Binarize labels in a one-vs-all fashion."
    DISPLAY_NAME = "Label Binarizer"

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Integer64 as the output type for binarized labels."""
        return Integer(arrow_type=pa.int64())
