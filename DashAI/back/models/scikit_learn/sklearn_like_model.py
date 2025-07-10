from typing import Type

import joblib

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
    categorical_label_encoder,
    dashai_to_pandas,
)
from DashAI.back.models.base_model import BaseModel


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
        # We recieve base DashAIDataset, so we first need to apply the transformations and then convert to desired format to fit the model.
        x_processed = dashai_to_pandas(x_train)
        y_processed = dashai_to_pandas(y_train, squeeze=True)
        return super().fit(x_processed, y_processed)
