import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class StratifiedGroupKFoldSplitter(FoldSplitter):
    COMPATIBLE_COMPONENTS = ["TabularClassificationTask", "TextClassificationTask"]
    DISPLAY_NAME: str = MultilingualString(
        en="Stratified Group K-Fold",
        es="K-Fold Estratificado por Grupos",
        pt="K-Fold Estratificado por Grupos",
    )
    FOLDS: bool = True
    GROUPS: bool = True
    SHUFFLE: bool = True

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
                    to a pandas DataFrame for StratifiedGroupKFold splitting: {e}"""
                ) from e

            try:
                y_labels = self.prepare_y(y)
            except Exception as e:
                raise ValueError(
                    f"""y must be convertible to a format suitable for
                    StratifiedGroupKFold splitting: {e}"""
                ) from e

            dataset_df_groups = dataset_df[self.group_column]

            sgkf = StratifiedGroupKFold(
                n_splits=n_splits, shuffle=shuffle, random_state=random_state
            )
            folds = list(sgkf.split(indexes, y=y_labels, groups=dataset_df_groups))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedGroupKFold splitting: {e}") from e

        return folds
