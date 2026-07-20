import numpy as np
from sklearn.model_selection import GroupKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class GroupKFoldSplitter(FoldSplitter):
    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Group K-Fold",
        es="K-Fold por Grupos",
        pt="K-Fold por Grupos",
    )
    FOLDS: bool = True
    GROUPS: bool = True
    SHUFFLE: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["GroupKFoldSplitter", "StratifiedGroupKFoldSplitter"]

    def __init__(self, splits_data):
        super().__init__(splits_data)
        self.group_column = splits_data.get("group_column", None)

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

            dataset_df_groups = dataset_df[self.group_column]

            gkf = GroupKFold(n_splits=n_splits)
            folds = list(gkf.split(indexes, groups=dataset_df_groups))
        except ValueError as e:
            raise ValueError(f"Error in GroupKFold splitting: {e}") from e

        return folds
