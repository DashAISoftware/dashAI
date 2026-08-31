"""Base Model abstract class."""

import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Final

from DashAI.back.config_object import ConfigObject

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logger = logging.getLogger(__name__)


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract base class for all machine learning models in DashAI.

    All models must extend this class and implement the abstract methods
    `save`, `load`, and `train`. Evaluation is owned by task-specific
    executors or mixins, not by the universal model contract.
    """

    TYPE: Final[str] = "Model"
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    COLOR: str = "#795548"
    ICON: str = "Science"

    # Optional hook, set by an optimizer that wants to watch training as it goes.
    #
    # Signature: ``(results: dict[str, float], step: int) -> None``. It is called
    # once per epoch with the validation metrics of that epoch, and it may raise
    # to abort training early — that is how Optuna's pruning works.
    #
    # It lives here, on the base class, because every model with an epoch loop
    # already routes its per-epoch metrics through `calculate_metrics`. Hooking
    # the loops one by one would mean touching five files that do not share a
    # common ancestor, and missing any model added later.
    #
    # Models that train in a single shot never call `calculate_metrics` with
    # `level=EPOCH`, so for them this stays None and nothing changes.
    _epoch_reporter = None

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata values for the current model.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing UI metadata such as the
            model icon used in the DashAI frontend.
        """
        metadata: Dict[str, Any] = {}
        metadata["icon"] = cls.ICON if cls.ICON else "Science"
        metadata["requires_download"] = bool(getattr(cls, "REQUIRES_DOWNLOAD", False))
        metadata["download_size_bytes"] = getattr(cls, "DOWNLOAD_SIZE_BYTES", None)
        return metadata

    @abstractmethod
    def save(self, filename: str) -> None:
        """Store the model to disk.

        Parameters
        ----------
        filename : str
            Path where the model will be saved.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self, filename: str) -> Any:
        """Restore a model instance from disk.

        Parameters
        ----------
        filename : str
            Path where the model was previously saved.

        Returns
        -------
        Any
            The restored model instance.
        """
        raise NotImplementedError

    @abstractmethod
    def train(
        self,
        *args,
        **kwargs,
    ) -> "BaseModel":
        """Train the model with the data required by its task executor.
        The concrete signature depends on the modeling problem.

        Returns
        -------
        BaseModel
            The trained model instance.
        """
        raise NotImplementedError

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Hook for model specific preprocessing of input features.

        Override in subclasses that require custom tokenization, encoding,
        or any other input transformation. Must not mutate the input in place.

        Parameters
        ----------
        dataset : DashAIDataset
            The input dataset to preprocess.
        is_fit : bool
            Whether the call is part of a fitting phase.
            Defaults to False.

        Returns
        -------
        DashAIDataset
            The preprocessed dataset ready to be fed into
            the model.
        """
        return dataset

    def predict_prepared(self, features: Any) -> Any:
        """Predict from data that is already in this model's feature space.

        ``predict`` takes a ``DashAIDataset`` with the raw columns and runs
        ``prepare_dataset`` itself. Explainers that perturb the feature matrix
        (SHAP, partial dependence, permutation importance, DiCE) instead hold a
        frame that ``prepare_dataset`` already produced, and must not have it
        prepared a second time. They call this method.

        Subclasses that can consume a feature matrix must override it, and
        should implement ``predict`` as
        ``self.predict_prepared(self.prepare_dataset(x, is_fit=False).to_pandas())``
        so both paths share the same estimator call.

        Parameters
        ----------
        features : pandas.DataFrame or numpy.ndarray
            Feature matrix as returned by ``prepare_dataset(..., is_fit=False)``.
            No further preparation is applied to it.

        Returns
        -------
        Any
            The same kind of output as ``predict``: predicted values for
            regressors, class probabilities for DashAI classifiers.

        Raises
        ------
        NotImplementedError
            If the model cannot consume a raw feature matrix.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support prediction from a prepared "
            "feature matrix, so explainers that perturb the model input are not "
            "available for it."
        )

    def predict_proba_prepared(self, features: Any) -> Any:
        """Return class probabilities for data already in the feature space.

        Classification counterpart of ``predict_prepared``, for explainers that
        need the sklearn-native ``predict_proba`` semantics.

        Parameters
        ----------
        features : pandas.DataFrame or numpy.ndarray
            Feature matrix as returned by ``prepare_dataset(..., is_fit=False)``.

        Returns
        -------
        numpy.ndarray
            Array of shape ``(n_samples, n_classes)`` with class probabilities.

        Raises
        ------
        NotImplementedError
            If the model cannot consume a raw feature matrix.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support probability prediction from "
            "a prepared feature matrix, so explainers that perturb the model "
            "input are not available for it."
        )

    def prepare_output(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
        """Hook for model-specific preprocessing of output targets.

        This default exists for backward compatibility with supervised models that
        preprocess targets. Unsupervised models are not required to use it.

        By default, delegates to `prepare_dataset`. Override in subclasses
        that need separate input and output preprocessing logic.

        Parameters
        ----------
        dataset : DashAIDataset
            The output dataset (target labels) to
            preprocess.
        is_fit : bool
            Whether the call is part of a fitting phase.
            Defaults to False.

        Returns
        -------
        DashAIDataset
            The preprocessed output dataset.
        """
        return self.prepare_dataset(dataset, is_fit)
