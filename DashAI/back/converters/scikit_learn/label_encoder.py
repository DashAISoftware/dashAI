from typing import Union

from sklearn.preprocessing import LabelEncoder as LabelEncoderOperation

from DashAI.back.converters.category.encoding import EncodingConverter
from DashAI.back.converters.sklearn_wrapper import SklearnWrapper
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)


class LabelEncoderSchema(BaseSchema):
    pass


class LabelEncoder(EncodingConverter, SklearnWrapper):
    """Scikit-learn's LabelEncoder wrapper for DashAI that supports multiple columns."""

    SCHEMA = LabelEncoderSchema
    DESCRIPTION = "Encode target labels with value between 0 and n_classes-1."
    SHORT_DESCRIPTION = "Convert categorical labels to numeric values"
    CATEGORY = "Encoding"
    DISPLAY_NAME = "Label Encoder"
    IMAGE_PREVIEW = "label_encoder.png"

    def __init__(self, **kwargs):
        super().__init__()
        self.encoders = {}
        self.fitted_columns = []
        self.metadata = {
            "changes_data_types": True,
            "supported_dtypes": ["object", "category", "string"],
        }

    def fit(self, x: DashAIDataset, y: Union[DashAIDataset, None] = None):
        """Fit label encoders to each column in the dataset."""
        x_pandas = x.to_pandas()

        for col in x_pandas.columns:
            if x_pandas[col].dtype.name in self.metadata["supported_dtypes"]:
                mask = x_pandas[col].notna()
                if mask.any():
                    encoder = LabelEncoderOperation()
                    encoder.fit(x_pandas.loc[mask, col])
                    self.encoders[col] = encoder
                    self.fitted_columns.append(col)

        return self

    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """Transform columns preserving NaN values."""
        x_pandas = x.to_pandas().copy()

        for col in self.fitted_columns:
            if col in x_pandas.columns:
                mask = x_pandas[col].notna()
                if mask.any():
                    x_pandas.loc[mask, col] = self.encoders[col].transform(
                        x_pandas.loc[mask, col]
                    )

        return to_dashai_dataset(x_pandas)
