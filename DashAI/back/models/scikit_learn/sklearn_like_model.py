from typing import Type

import joblib

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

from DashAI.back.dataloaders.classes.dashai_dataset_utils import dashai_to_pandas, categorical_label_encoder

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
        #We recieve base DashAIDataset, so we first need to apply the transformations and then convert to desired format to fit the model.
        x_processed = dashai_to_pandas(self.prepare_dataset(x_train))
        y_processed = dashai_to_pandas(self.prepare_dataset(y_train), squeeze=True)
        return super().fit(x_processed, y_processed)


    def prepare_dataset(
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
            The prepared dataset ready to be converted to an accepted format in the model.
        """
        try:
            #We apply as many transformations from dashai_dataset_utils as needed.
            ds = categorical_label_encoder(dataset)
            return ds
        except Exception as e:
            print(f"Couldn't apply transformations to the dataset for the model: {e}")
        



            