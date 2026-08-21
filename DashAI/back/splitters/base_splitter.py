from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Final, List

from sklearn.preprocessing import LabelEncoder

from DashAI.back.config_object import ConfigObject

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseSplitter(ConfigObject, metaclass=ABCMeta):
    """Abstract interface for all dataset splitters implemented in DashAI.

    This base class defines the common contract shared by every splitting
    strategy, including the ability to create reproducible partitions for
    training, validation, and testing. Concrete subclasses implement specific
    strategies such as holdout, K-fold.
    """

    TYPE: Final[str] = "Splitter"

    # Name of the partition an explainer evaluates on, which is the data the
    # trained model has not seen. Splitters that reserve rows under another
    # name override this so the frontend and the metrics never disagree about
    # what "test" means.
    EVALUATION_PARTITION: str = "test"

    @classmethod
    def explainable_partitions(
        cls, split_indexes: Dict[str, Any]
    ) -> Dict[str, List[int]]:
        """Map each partition an explainer may target to its row indexes.

        Each splitter decides which partitions its runs expose and what they
        are called, so adding a splitter with a different partitioning scheme
        needs no change in the explainability code or in the frontend.

        Parameters
        ----------
        split_indexes : dict
            The ``Run.split_indexes`` payload of a run produced by this
            splitter, already parsed.

        Returns
        -------
        dict
            Partition name to row indexes, in the order they should be offered.

        Raises
        ------
        NotImplementedError
            If the subclass does not provide an implementation.
        """
        raise NotImplementedError(
            "The explainable partitions method must be implemented by subclasses."
        )

    @classmethod
    def explainable_splits(cls, split_indexes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Describe the partitions of a run that an explainer may target.

        Built from :meth:`explainable_partitions`, dropping the partitions that
        received no rows and appending an entry covering the whole dataset.

        Parameters
        ----------
        split_indexes : dict
            The ``Run.split_indexes`` payload, already parsed.

        Returns
        -------
        list[dict]
            One ``{"name", "rows"}`` entry per non-empty partition, followed by
            an ``all`` entry. Empty when the run has no data to explain.
        """
        try:
            partitions = cls.explainable_partitions(split_indexes)
        except (KeyError, NotImplementedError, TypeError):
            return []

        splits = [
            {"name": name, "rows": len(indexes)}
            for name, indexes in partitions.items()
            if indexes
        ]
        if not any(split["name"] == cls.EVALUATION_PARTITION for split in splits):
            # Without the partition the model never saw there is nothing an
            # explanation could be measured on.
            return []

        splits.append(
            {
                "name": "all",
                "rows": sum(len(indexes) for indexes in partitions.values()),
            }
        )
        return splits

    def __init__(self, splits_data):
        """Initialize the common splitter configuration.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary containing splitter options such as the
            random state and whether the data should be shuffled.
        """
        self.random_state = splits_data.get("random_state", 42)
        self.shuffle = splits_data.get("shuffle", True)

    @abstractmethod
    def split(self, x: DashAIDataset, y: DashAIDataset):
        """Split the provided dataset into training and testing subsets.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset or collection of samples to be partitioned.
        y : DashAIDataset
            Target labels or output data associated with ``x``.

        Returns
        -------
        tuple
            A tuple containing the partitioned datasets and the corresponding
            indices used to build each split.
        """
        raise NotImplementedError("The split method must be implemented by subclasses.")

    @abstractmethod
    def split_indexes(self, x: DashAIDataset, y: DashAIDataset):
        """Generate train/test and/or validation index pairs.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset to be partitioned.
        y : DashAIDataset
            Target values associated with ``x``.

        Returns
        -------
        tuple | list[tuple]
            A tuple for holdout splitters containing train/test/validation indices,
            or a list of tuples for fold-based splitters containing train/test index
            pairs for each fold.
        """
        raise NotImplementedError(
            "The split indexes method must be implemented by subclasses."
        )

    def prepare_y(self, y):
        """Encode the target variable for stratified splitting.

        Parameters
        ----------
        y : object
            Target values to encode. This may be a list, a pandas-like object,
            or a DashAI dataset that exposes a single target column.

        Returns
        -------
        object
            Encoded labels suitable for stratified splitting.

        Raises
        ------
        ValueError
            If the target values are missing or cannot be converted into a
            valid label representation.
        """
        if y is None:
            raise ValueError(
                "Target variable 'y' cannot be None for stratified splitting."
            )

        if all(isinstance(v, int) for v in y):
            return y

        # Case Dataset (HuggingFace / DashAIDataset)
        if hasattr(y, "column_names"):
            if len(y.column_names) != 1:
                raise ValueError("y must contain exactly one column")

            col = y.column_names[0]
            y = y[col]

        try:
            return LabelEncoder().fit_transform(y)
        except Exception as e:
            raise ValueError("Cannot encode labels") from e
