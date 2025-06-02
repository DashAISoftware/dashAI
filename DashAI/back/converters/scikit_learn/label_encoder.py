from sklearn.preprocessing import LabelEncoder as LabelEncoderOperation

from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields.base_schema import BaseSchema


class LabelEncoderSchema(BaseSchema):
    pass


class LabelEncoder(SklearnWrapper, LabelEncoderOperation):
    """Scikit-learn's LabelEncoder wrapper for DashAI."""

    SCHEMA = LabelEncoderSchema
    DESCRIPTION = "Encode target labels with value between 0 and n_classes-1."
