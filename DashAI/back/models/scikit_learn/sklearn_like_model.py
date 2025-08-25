from typing import Type

import joblib

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
    apply_categorical_label_encoder,
    categorical_label_encoder,
    dashai_to_pandas,
)
from DashAI.back.models.base_model import BaseModel


class SklearnLikeModel(BaseModel):
    """Abstract class to define the way to save sklearn like models."""

    def __init__(self, *args, **kwargs):
        """Initialize the SklearnLikeModel."""
        super().__init__(*args, **kwargs)
        # We store the dictionary of encodings for categorical columns.
        self.encodings = {}

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
        # We recieve base DashAIDataset,
        # so we first need to apply the transformations
        # and then convert to desired format to fit the model.
        x_processed = dashai_to_pandas(self.prepare_dataset(x_train, is_fit=True))
        y_processed = dashai_to_pandas(
            self.prepare_dataset(y_train, is_fit=True), squeeze=True
        )
        return super().fit(x_processed, y_processed)

    def prepare_dataset(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Apply the model transformations to the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool, optional
            If True, the method will apply transformations needed for fitting the model.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        if not is_fit:
            try:
                dataset = apply_categorical_label_encoder(dataset, self.encodings)
                return dataset
            except Exception as e:
                print(f"Couldn't apply categorical label encoding: {e}")
        else:
            try:
                # We apply as many transformations from dashai_dataset_utils as needed.
                dataset, encodings = categorical_label_encoder(dataset)
                self.encodings.update(encodings)  # Store the encodings for later use
                return dataset
            except Exception as e:
                print(
                    f"Couldn't apply transformations to the dataset for the model: {e}"
                )
