from abc import abstractmethod
from typing import TYPE_CHECKING, Sequence

from DashAI.back.models.base_model import BaseModel

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ClusteringModel(BaseModel):
    """Base contract for models that perform clustering tasks.

    Concrete clustering models receive input features and produce discovered
    cluster assignments. They are evaluated by clustering executors with
    metrics that use ``X`` and labels, not ``y_true`` and ``y_pred``. Backend
    adapters such as sklearn or FAISS should implement this contract once so
    concrete clustering algorithms can remain small.
    """

    COMPATIBLE_COMPONENTS = ["ClusteringTask"]

    @abstractmethod
    def train(self, x: "DashAIDataset") -> "ClusteringModel":
        """Fit the clustering model using input features only.

        Clustering models do not receive target columns. Implementations should
        store the labels discovered during fitting when the backend exposes
        them only for the training data.

        Parameters
        ----------
        x : DashAIDataset
            Input feature matrix used to fit the clustering model.

        Returns
        -------
        ClusteringModel
            The fitted clustering model instance.
        """
        raise NotImplementedError

    @abstractmethod
    def get_cluster_labels(
        self, x: "DashAIDataset" = None
    ) -> "ndarray | Sequence[int]":
        """Return cluster labels for fitted data or provided samples.

        Algorithms that support assigning labels to new samples may use ``x``.
        Algorithms that only expose labels for the fitted dataset should return
        those stored labels when ``x`` is omitted.

        Parameters
        ----------
        x : DashAIDataset, optional
            Input samples to assign to clusters. If omitted, the method should
            return labels discovered during fitting when the backend supports
            only fitted-data labels.

        Returns
        -------
        array-like
            Cluster label assigned to each sample. Noise points may be encoded
            with backend-specific labels such as ``-1``.
        """
        raise NotImplementedError
