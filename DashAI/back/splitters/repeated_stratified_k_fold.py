import numpy as np
from sklearn.model_selection import RepeatedStratifiedKFold

from .fold_splitter import FoldSplitter


class RepeatedStratifiedKFoldSplitter(FoldSplitter):
    def __init__(self, splits_data, dataset, output_column):
        super().__init__(splits_data, dataset, output_column)
        self.n_repeats = splits_data.get("n_repeats", 1)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(len(x))

        try:
            y_labels = self.prepare_y(y)

            rskf = RepeatedStratifiedKFold(
                n_splits=n_splits, n_repeats=self.n_repeats, random_state=random_state
            )
            folds = list(rskf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in RepeatedStratifiedKFold splitting: {e}") from e

        return folds
