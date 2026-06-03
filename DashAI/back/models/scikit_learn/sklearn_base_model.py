"""Shared infrastructure for scikit-learn-backed models."""

from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional

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


class SklearnBaseModel:
    """Technical mixin with shared scikit-learn model infrastructure.

    This class intentionally does not inherit from ``BaseModel``. Concrete
    models reach DashAI's model contract through task-level bases such as
    ``SupervisedModel`` or ``ClusteringModel``.
    """

    CATEGORICAL_ENCODING: CategoricalEncodingStrategy = (
        CategoricalEncodingStrategy.LABEL
    )

    def __init__(self, *args, **kwargs):
        """Initialize the SklearnBaseModel."""
        super().__init__(*args, **kwargs)
        self.encodings = {}
        self.one_hot_encoder: Optional[Any] = None
        self.categorical_columns: List[str] = []

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
    def load(filename: str) -> Any:
        """Deserialise a model from disk using joblib.

        Parameters
        ----------
        filename : str
            Path to the file previously written by :meth:`save`.

        Returns
        -------
        SklearnBaseModel
            The loaded model instance.
        """
        import joblib

        model = joblib.load(filename)
        return model

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
