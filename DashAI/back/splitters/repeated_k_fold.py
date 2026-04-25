import numpy as np
from sklearn.model_selection import RepeatedKFold

from .base_splitter import BaseFoldSplitter


class RepeatedKFoldSplitter(BaseFoldSplitter):
    def __init__(self, splits_data, dataset, output_column):
        super().__init__(splits_data, dataset, output_column)
        self.n_repeats = splits_data.get("n_repeats", 1)

    def split_indexes(
        self, total_rows, n_splits, shuffle, random_state=42, y_labels=None
    ):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(total_rows)

        try:
            kf = RepeatedKFold(
                n_splits=n_splits,
                shuffle=shuffle,
                n_repeats=self.n_repeats,
                random_state=random_state,
            )
            folds = list(kf.split(indexes))

        except ValueError as e:
            raise ValueError(f"Error in RepeatedKFold splitting: {e}") from e

        return folds
