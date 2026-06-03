"""Base adapter for scikit-learn clustering models."""

from typing import TYPE_CHECKING

from DashAI.back.models.clustering_model import ClusteringModel
from DashAI.back.models.scikit_learn.sklearn_base_model import SklearnBaseModel

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class SklearnLikeClusterer(SklearnBaseModel, ClusteringModel):
    """Shared behaviour for scikit-learn-style clustering algorithms.

    Concrete subclasses also inherit from the actual sklearn estimator, for
    example ``KMeans`` or ``DBSCAN``. This adapter maps DashAI's clustering
    contract to the sklearn API: models are fitted with input features only and
    cluster assignments are exposed through ``get_cluster_labels``.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the sklearn clustering adapter.

        Parameters
        ----------
        *args : tuple
            Positional arguments forwarded to the sklearn estimator.
        **kwargs : dict
            Keyword arguments forwarded to the sklearn estimator.
        """
        super().__init__(*args, **kwargs)
        self._labels: "ndarray | None" = None
        self._fitted_feature_names: list[str] = []

    def train(self, x_train: "DashAIDataset") -> "SklearnLikeClusterer":
        """Fit the clustering model using input features only.

        Parameters
        ----------
        x_train : DashAIDataset
            Dataset containing the input columns selected for clustering.

        Returns
        -------
        SklearnLikeClusterer
            The fitted clustering adapter.

        Raises
        ------
        ValueError
            If the wrapped sklearn estimator does not expose labels after
            fitting.
        """
        x_processed = self.prepare_dataset(x_train, is_fit=True).to_pandas()
        self._fitted_feature_names = list(x_processed.columns)

        if hasattr(self, "fit_predict"):
            self._labels = self.fit_predict(x_processed)
        else:
            self.fit(x_processed)
            self._labels = getattr(self, "labels_", None)

        if self._labels is None:
            raise ValueError(
                f"{self.__class__.__name__} did not produce cluster labels."
            )

        return self

    def get_cluster_labels(self, x: "DashAIDataset | None" = None) -> "ndarray":
        """Return fitted labels or assign labels to new samples when supported.

        Some sklearn clusterers, such as K-Means, implement ``predict`` and can
        assign labels to new samples. Others, such as DBSCAN, only expose labels
        for the fitted dataset through ``labels_``. This method supports both
        cases.

        Parameters
        ----------
        x : DashAIDataset, optional
            Samples to assign to clusters. If omitted, or if the wrapped
            estimator does not support ``predict``, the labels discovered during
            fitting are returned.

        Returns
        -------
        numpy.ndarray
            Cluster label assigned to each sample.

        Raises
        ------
        ValueError
            If the model has not been fitted, or if labels are requested for
            unseen samples from an estimator that cannot predict new labels.
        """
        if x is not None and hasattr(self, "predict"):
            x_processed = self.prepare_dataset(x, is_fit=False).to_pandas()
            return self.predict(x_processed)

        if self._labels is None:
            raise ValueError(
                f"{self.__class__.__name__} must be fitted before returning labels."
            )

        if x is not None and len(x) != len(self._labels):
            raise ValueError(
                f"{self.__class__.__name__} cannot assign labels to unseen samples."
            )

        return self._labels
