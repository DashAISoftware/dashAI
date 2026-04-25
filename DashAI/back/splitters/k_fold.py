import numpy as np
from sklearn.model_selection import KFold

from .base_splitter import BaseFoldSplitter


class KFoldSplitter(BaseFoldSplitter):
    def __init__(self, splits_data):
        super().__init__(splits_data)

    def split_indexes(
        self, total_rows, n_splits, shuffle, random_state=42, y_labels=None
    ):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(total_rows)

        try:
            kf = KFold(n_splits=n_splits, shuffle=shuffle, random_state=random_state)
            folds = list(kf.split(indexes))
        except ValueError as e:
            raise ValueError(
                f"""Error in KFold splitting: {e}.
                Check if n_splits is less than or equal
                to the number of samples."""
            ) from e

        return folds
