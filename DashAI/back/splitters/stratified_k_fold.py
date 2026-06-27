import numpy as np
from sklearn.model_selection import StratifiedKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class StratifiedKFoldSplitter(FoldSplitter):
    COMPATIBLE_COMPONENTS = ["TabularClassificationTask", "TextClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="Stratified K-Fold",
        es="K-Fold Estratificado",
        pt="K-Fold Estratificado",
    )
    FOLDS: bool = True
    SHUFFLE: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]

    def __init__(self, splits_data):
        super().__init__(splits_data)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(len(x))

        try:
            y_labels = self.prepare_y(y)

            kf = StratifiedKFold(
                n_splits=n_splits, shuffle=shuffle, random_state=random_state
            )
            folds = list(kf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedKFold splitting: {e}") from e

        return folds
