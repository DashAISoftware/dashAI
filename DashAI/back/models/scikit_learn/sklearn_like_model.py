from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional

from DashAI.back.models.base_model import BaseModel
from DashAI.back.types.categorical import Categorical

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class CategoricalEncodingStrategy(str, Enum):
    """Strategy for encoding categorical variables.

    LABEL: Use LabelEncoder -
           Good for models that don't assume linear relationships between features.

    ONE_HOT: Use OneHotEncoder - creates binary columns for each category.
             Required for linear models (Logistic Regression, SVM, KNN)
             that would otherwise assume ordinal relationships.
    """

    LABEL = "label"
    ONE_HOT = "one_hot"


class SklearnLikeModel(BaseModel):
    """Abstract base class for scikit-learn-compatible DashAI models.

    Provides ``save`` / ``load`` via joblib, categorical encoding helpers
    (label or one-hot), and the ``prepare_dataset`` / ``prepare_output``
    pipeline expected by the DashAI training loop. Concrete subclasses
    (classifiers and regressors) inherit this mixin and supply ``train`` and
    ``predict`` implementations backed by scikit-learn estimators.
    """

    CATEGORICAL_ENCODING: CategoricalEncodingStrategy = (
        CategoricalEncodingStrategy.LABEL
    )

    def __init__(self, *args, **kwargs):
        """Initialize the SklearnLikeModel."""
        super().__init__(*args, **kwargs)
        self.encodings = {}
        self.one_hot_encoder: Optional[Any] = None
        self.categorical_columns: List[str] = []
        self.output_encodings = {}

    def save(self, filename: str) -> None:
        """Serialise the model to disk using joblib.

        Parameters
        ----------
        filename : str
            Destination file path where the model will be written.
        """
        import joblib

        joblib.dump(self, filename)

    @staticmethod
    def load(filename: str) -> None:
        """Deserialise a model from disk using joblib.

        Parameters
        ----------
        filename : str
            Path to the file previously written by :meth:`save`.

        Returns
        -------
        SklearnLikeModel
            The loaded model instance.
        """
        import joblib

        model = joblib.load(filename)
        return model

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

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Apply the model transformations to the dataset.

        Respects per-column encoder preference stored in each Categorical
        column's `encoder` field. Falls back to model's CATEGORICAL_ENCODING
        for columns with unrecognized encoder values.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool, optional
            If True, the method will fit encoders on the data.
            If False, will apply previously fitted encoders.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        import logging

        _logger = logging.getLogger(__name__)

        types = dataset.types
        has_categorical = any(isinstance(t, Categorical) for t in types.values())

        if not has_categorical:
            return dataset

        one_hot_cols = [
            c
            for c, t in types.items()
            if isinstance(t, Categorical) and t.encoder == "one_hot"
        ]
        label_cols = [
            c
            for c, t in types.items()
            if isinstance(t, Categorical) and t.encoder == "label"
        ]
        default_cols = [
            c
            for c, t in types.items()
            if isinstance(t, Categorical) and t.encoder not in ("one_hot", "label")
        ]
        if default_cols:
            _logger.warning(
                "Columns %s have unrecognized encoder preference. "
                "Falling back to model strategy %s.",
                default_cols,
                self.CATEGORICAL_ENCODING,
            )
            if self.CATEGORICAL_ENCODING == CategoricalEncodingStrategy.ONE_HOT:
                one_hot_cols.extend(default_cols)
            else:
                label_cols.extend(default_cols)

        prepared = dataset
        if label_cols:
            prepared = self._prepare_label_encoded(prepared, is_fit, columns=label_cols)
        if one_hot_cols:
            prepared = self._prepare_one_hot(prepared, is_fit, columns=one_hot_cols)
        return prepared

    def _prepare_label_encoded(
        self, dataset: "DashAIDataset", is_fit: bool, columns: list = None
    ) -> "DashAIDataset":
        """Prepare dataset using label encoding for categorical columns.

        This is appropriate for tree-based models that don't assume
        ordinal relationships between encoded values.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool
            If True, fit the encoder. If False, use existing encodings.
        columns : list, optional
            If given, only label-encode the specified columns.

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
            prepared, encodings = categorical_label_encoder(dataset, columns=columns)
            self.encodings.update(encodings)
        else:
            if self.encodings:
                relevant_encodings = {
                    k: v
                    for k, v in self.encodings.items()
                    if columns is None or k in columns
                }
                prepared = apply_categorical_label_encoder(dataset, relevant_encodings)

        return prepared

    def _prepare_one_hot(
        self, dataset: "DashAIDataset", is_fit: bool, columns: list = None
    ) -> "DashAIDataset":
        """Prepare dataset using one-hot encoding for categorical columns.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool
            If True, fit the encoder. If False, use existing encoder.
        columns : list, optional
            If given, only one-hot encode the specified columns.

        Returns
        -------
        DashAIDataset
            Dataset with categorical columns replaced by one-hot columns.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
            apply_categorical_one_hot_encoder,
            categorical_one_hot_encoder,
        )

        if is_fit:
            prepared, encoder, cat_cols = categorical_one_hot_encoder(
                dataset, columns=columns
            )
            self.one_hot_encoder = encoder
            self.categorical_columns = cat_cols
        else:
            if self.one_hot_encoder is not None:
                prepared = apply_categorical_one_hot_encoder(
                    dataset, self.one_hot_encoder, self.categorical_columns
                )
            else:
                prepared = dataset

        return prepared
