import numpy as np
from sklearn.model_selection import RepeatedKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class RepeatedKFoldSplitter(FoldSplitter):
    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Repeated K-Fold",
        es="K-Fold Repetido",
        pt="K-Fold Repetido",
    )
    FOLDS: bool = True
    REPEATS: bool = True

    def __init__(self, splits_data):
        super().__init__(splits_data)
        self.n_repeats = splits_data.get("n_repeats", 2)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(len(x))

        try:
            rkf = RepeatedKFold(
                n_splits=n_splits,
                n_repeats=self.n_repeats,
                random_state=random_state,
            )
            folds = list(rkf.split(indexes))

        except ValueError as e:
            raise ValueError(f"Error in RepeatedKFold splitting: {e}") from e

        return folds
