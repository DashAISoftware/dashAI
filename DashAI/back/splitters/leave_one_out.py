import numpy as np
from sklearn.model_selection import LeaveOneOut

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class LeaveOneOutSplitter(FoldSplitter):
    """Splitter that creates one fold per sample by leaving one example out at a time.

    This exhaustive strategy is useful for very small datasets where every
    observation should be tested in turn and the computational cost remains
    acceptable. It is often used as a reference method in small-sample studies
    and in settings where a highly thorough estimate of performance is desired.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneOut.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Leave-One-Out",
        es="Dejar Uno Fuera",
        pt="Deixar Um Fora",
    )
    SHUFFLE: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]

    def __init__(self, splits_data):
        """Initialize the leave-one-out splitter with the provided configuration."""
        super().__init__(splits_data)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate train/test index pairs following the leave-one-out scheme.

        Parameters
        ----------
        x : object
            Input dataset whose length determines the number of available samples.
        y : object
            Target values associated with ``x``. This argument is accepted for
            interface consistency but is not used directly by the splitter.
        n_splits : int
            Unused parameter retained for interface compatibility.
        shuffle : bool
            Unused parameter retained for interface compatibility.
        random_state : int, optional
            Unused parameter retained for interface compatibility.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs, one for each sample in the dataset.
        """
        indexes = np.arange(len(x))

        try:
            loo = LeaveOneOut()
            folds = list(loo.split(indexes))
        except ValueError as e:
            raise ValueError(f"Error in LeaveOneOut splitting: {e}") from e

        return folds
