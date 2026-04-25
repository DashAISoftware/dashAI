import numpy as np
from sklearn.model_selection import LeaveOneOut

from .base_fold_splitter import BaseFoldSplitter


class LeaveOneOutSplitter(BaseFoldSplitter):
    def __init__(self, splits_data, dataset, output_column):
        super().__init__(splits_data, dataset, output_column)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(len(x))

        try:
            loo = LeaveOneOut()
            folds = list(loo.split(indexes))
        except ValueError as e:
            raise ValueError(f"Error in LeaveOneOut splitting: {e}") from e

        return folds
