from typing import Type

import joblib

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, modify_table
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Integer, Text, Boolean, Float, Time, Timestamp, Duration, Date, Decimal, Binary

from DashAI.back.types.utils import to_arrow_types
from DashAI.back.models.base_model import BaseModel
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import pandas as pd
import pyarrow as pa




class SklearnLikeModel(BaseModel):
    """Abstract class to define the way to save sklearn like models."""

    def __init__(self, *args, **kwargs):
        """Initialize the SklearnLikeModel."""
        super().__init__(*args, **kwargs)

    def save(self, filename: str) -> None:
        """Save the model in the specified path."""
        joblib.dump(self, filename)

    @staticmethod
    def load(filename: str) -> None:
        """Load the model of the specified path."""
        model = joblib.load(filename)
        return model
    
    # --- Methods for process the data for sklearn models ---

    def fit(
        self, x_train: DashAIDataset, y_train: DashAIDataset
    ) -> Type["SklearnLikeModel"]:
        """Fit the estimator.

        Parameters
        ----------
        x_train : DashAIDataset
            Dataset with the input data.
        y_train : DashAIDataset
            Dataset with the target data.

        Returns
        -------
        self
            The fitted estimator object.
        """
        x_processed = self.convert_format(x_train)
        y_processed = self.convert_format(y_train)
        return super().fit(x_processed, y_processed)
    
    def convert_format(
        self, dataset: DashAIDataset
    ) -> pd.DataFrame:
        """Convert the dataset to a format suitable for the model.

        Parameters
        ----------
        y : DashAIDataset
            The dataset to be converted.

        Returns
        -------
        pd.DataFrame
            The converted dataset in pandas DataFrame format.
        """
        
        # Convert the DashAIDataset to a pandas DataFrame
        
        df = (self.apply_model_transformations(dataset)).to_pandas()

        
        return df
 
    
    def apply_model_transformations(
        self, dataset: DashAIDataset
    ) -> DashAIDataset:
        """Apply the model transformations to the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.

        Returns
        -------
        DashAIDataset
            The transformed dataset.
        """
        print("Applying model transformations to the dataset...")

        new_columns = {}
        table = dataset.arrow_table
        print("Dataset types:", dataset._types)
        for col, _type in dataset._types.items():
            array = table[col]
            if isinstance(_type, Categorical):
                print(f"Processing column '{col}' with Categorical type.")
                print(f"Categories: {_type.categories}")
                if all(isinstance(c, str) for c in _type.categories) or all(isinstance(c, bool) for c in _type.categories):
                    values = [ _type.str2int(x.as_py()) for x in array ]
                    new_columns[col] = pa.array(values, type=pa.int64())
                else:
                    new_columns[col] = pa.array(array, type=pa.int64())
            else:
                new_columns[col] = pa.array(array, type=to_arrow_types(_type.dtype))
        transformed_dataset = modify_table(dataset, columns=new_columns)

        return transformed_dataset