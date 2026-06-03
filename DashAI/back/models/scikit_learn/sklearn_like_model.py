from typing import TYPE_CHECKING

from DashAI.back.models.scikit_learn.sklearn_base_model import (
    CategoricalEncodingStrategy as CategoricalEncodingStrategy,
)
from DashAI.back.models.scikit_learn.sklearn_base_model import (
    SklearnBaseModel,
)
from DashAI.back.models.supervised_model import SupervisedModel

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class SklearnLikeModel(SklearnBaseModel, SupervisedModel):
    """Abstract base class for scikit-learn-compatible DashAI models.

    Provides ``save`` / ``load`` via joblib, categorical encoding helpers
    (label or one-hot), and the ``prepare_dataset`` / ``prepare_output``
    pipeline expected by the DashAI training loop. Concrete subclasses
    (classifiers and regressors) inherit this mixin and supply ``train`` and
    ``predict`` implementations backed by scikit-learn estimators.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the SklearnLikeModel."""
        super().__init__(*args, **kwargs)
        self.output_encodings = {}

    # --- Methods for process the data for sklearn models ---

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        """Train the sklearn model on the provided dataset.

        Applies ``prepare_dataset`` and ``prepare_output`` to encode categorical
        features and targets before delegating to the scikit-learn ``fit`` method.

        Parameters
        ----------
        x_train : DashAIDataset
            The input features for training.
        y_train : DashAIDataset
            The target labels for training.
        x_validation : DashAIDataset, optional
            Validation input features (unused in sklearn models). Defaults to None.
        y_validation : DashAIDataset, optional
            Validation target labels (unused in sklearn models). Defaults to None.

        Returns
        -------
        BaseModel
            The fitted scikit-learn estimator (self).
        """
        x_processed = self.prepare_dataset(x_train, is_fit=True).to_pandas()
        y_processed = self.prepare_output(y_train, is_fit=True).to_pandas()
        return super().fit(x_processed, y_processed)

    def predict(self, x: "DashAIDataset"):
        """Predict using the trained model.

        Parameters
        ----------
        x : DashAIDataset
            Dataset with the input data.

        Returns
        -------
        np.ndarray
            Predicted values.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        if isinstance(x, DashAIDataset):
            x = self.prepare_dataset(x, is_fit=False).to_pandas()
        return super().predict(x)

    def prepare_output(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Prepare output targets using Label encoding.

        Parameters
        ----------
        dataset : DashAIDataset
            The output dataset to be transformed.
        is_fit : bool, optional
            If True, fit the encoder. If False, use existing encodings.

        Returns
        -------
        DashAIDataset
            Dataset with categorical columns converted to integers.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
            apply_categorical_label_encoder,
            categorical_label_encoder,
        )

        prepared = dataset

        if is_fit:
            prepared, encodings = categorical_label_encoder(dataset)
            self.output_encodings.update(encodings)
        else:
            if self.output_encodings:
                prepared = apply_categorical_label_encoder(
                    dataset, self.output_encodings
                )

        return prepared
