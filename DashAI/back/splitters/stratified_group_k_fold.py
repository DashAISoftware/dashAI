import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class StratifiedGroupKFoldSplitter(FoldSplitter):
    """Splitter that preserves both class balance and group membership in each fold.

    This strategy is particularly valuable for grouped classification tasks where
    the target labels are imbalanced and the samples are also organized into
    non-independent groups. It simultaneously prevents leakage across groups and
    keeps the class distribution similar across folds, which makes the
    evaluation more reliable and less biased.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Stratified Group K-Fold",
        es="K-Fold Estratificado por Grupos",
        pt="K-Fold Estratificado por Grupos",
        de="Stratifiziertes Gruppen-K-Fold",
        zh="分层分组 K 折交叉验证",
    )
    FOLDS: bool = True
    GROUPS: bool = True
    SHUFFLE: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["GroupKFoldSplitter", "StratifiedGroupKFoldSplitter"]

    def __init__(self, splits_data):
        """Initialize the stratified group-based K-fold splitter.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary that may include the name of the group
            column used to define the groups.
        """
        super().__init__(splits_data)
        self.group_column = splits_data.get("group_column", None)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate train/test index pairs preserving both labels and groups.

        Parameters
        ----------
        x : object
            Input dataset that can be converted to a pandas DataFrame.
        y : object
            Target values used to preserve class balance across folds.
        n_splits : int
            Number of folds to create.
        shuffle : bool
            Whether samples should be shuffled before folding.
        random_state : int, optional
            Seed used for reproducible shuffling, by default 42.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs preserving group and label balance.
        """
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
