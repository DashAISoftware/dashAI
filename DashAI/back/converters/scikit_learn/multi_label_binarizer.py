from sklearn.preprocessing import MultiLabelBinarizer as MultiLabelBinarizerOperation

from DashAI.back.api.utils import parse_string_to_list
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields import (
    bool_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class MultiLabelBinarizerSchema(BaseSchema):
    classes: schema_field(
        none_type(string_field()), # array-like of shape (n_features,)
        None,
        "Classes that will be binarized.",
    )  # type: ignore
    sparse_output: schema_field(
        bool_field(),
        False,
        "True if the returned array from transform is desired to be in sparse CSR format.",
    )  # type: ignore


class MultiLabelBinarizer(SklearnWrapper, MultiLabelBinarizerOperation):
    """Scikit-learn's MultiLabelBinarizer wrapper for DashAI."""

    SCHEMA = MultiLabelBinarizerSchema
    DESCRIPTION = "Transform between iterable of iterables and a multilabel format."

    def __init__(self, **kwargs):
        self.classes = kwargs.pop("classes", None)
        if self.classes != None:
            self.classes = [parse_string_to_list(self.classes)]
        kwargs["classes"] = self.classes

        super().__init__(**kwargs)
