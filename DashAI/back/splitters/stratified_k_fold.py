import numpy as np
from sklearn.model_selection import StratifiedKFold

from .base_fold_splitter import BaseFoldSplitter


class StratifiedKFoldSplitter(BaseFoldSplitter):
    def __init__(self, splits_data, dataset, output_column):
        super().__init__(splits_data, dataset, output_column)

    def split_indexes(
        self, total_rows, n_splits, shuffle, random_state=42, y_labels=None
    ):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(total_rows)

        try:
            if y_labels is None:
                raise ValueError("y_labels must be provided for StratifiedKFold.")

            kf = StratifiedKFold(
                n_splits=n_splits, shuffle=shuffle, random_state=random_state
            )
            folds = list(kf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedKFold splitting: {e}") from e

        return folds
