from abc import ABCMeta, abstractmethod
from typing import Final

from beartype.typing import Dict, List, Tuple, Union
from sklearn.preprocessing import LabelEncoder


class BaseSplitter(metaclass=ABCMeta):
    """Abstract interface for all dataset splitters implemented in DashAI.

    This base class defines the common contract shared by every splitting
    strategy, including the ability to create reproducible partitions for
    training, validation, and testing. Concrete subclasses implement specific
    strategies such as holdout, K-fold.
    """

    TYPE: Final[str] = "Splitter"

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
    def split(
        self, x, y
    ) -> Tuple[Union[object, List[object]], Union[object, List[object]], Dict]:
        """Split the provided dataset into training and testing subsets.

        Parameters
        ----------
        x : object
            Input dataset or collection of samples to be partitioned.
        y : object
            Target labels or output data associated with ``x``.

        Returns
        -------
        tuple
            A tuple containing the partitioned datasets and the corresponding
            indices used to build each split.
        """
        raise NotImplementedError("The split method must be implemented by subclasses.")

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
