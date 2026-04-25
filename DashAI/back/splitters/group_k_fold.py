import numpy as np
from sklearn.model_selection import GroupKFold

from .base_fold_splitter import BaseFoldSplitter


class GroupKFoldSplitter(BaseFoldSplitter):
    def __init__(self, splits_data, dataset, output_column):
        super().__init__(splits_data, dataset, output_column)
        self.groups = splits_data.get("groups", None)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate lists with train and test indexes for each fold."""
        indexes = np.arange(len(x))

        try:
            try:
                dataset_df = x.to_pandas()
            except Exception as e:
                raise ValueError(
                    f"""Input x must be convertible
                    to a pandas DataFrame for GroupKFold splitting: {e}"""
                ) from e

            dataset_df_groups = dataset_df[self.groups]

            gkf = GroupKFold(n_splits=n_splits)
            folds = list(gkf.split(indexes, groups=dataset_df_groups))
        except ValueError as e:
            raise ValueError(f"Error in GroupKFold splitting: {e}") from e

        return folds
