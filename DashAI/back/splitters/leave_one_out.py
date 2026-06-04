import numpy as np
from sklearn.model_selection import LeaveOneOut

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class LeaveOneOutSplitter(FoldSplitter):
    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Leave-One-Out",
        es="Dejar Uno Fuera",
        pt="Deixar Um Fora",
    )
    SHUFFLE: bool = True

    def __init__(self, splits_data):
        super().__init__(splits_data)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(len(x))

        try:
            loo = LeaveOneOut()
            folds = list(loo.split(indexes))
        except ValueError as e:
            raise ValueError(f"Error in LeaveOneOut splitting: {e}") from e

        return folds
