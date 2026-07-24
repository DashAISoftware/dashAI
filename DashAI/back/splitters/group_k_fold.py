import numpy as np
from sklearn.model_selection import GroupKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter


class GroupKFoldSplitter(FoldSplitter):
    """Splitter that generates folds while preserving the group structure of the data.

    This strategy is useful when samples are not independent because they share
    a common group, such as a patient, document, image collection, or other
    entity that should not appear in both train and test partitions. It helps
    prevent leakage by keeping all observations from the same group within the
    same fold.

    It is commonly applied in grouped classification, regression, and
    translation settings where group-level dependencies must be respected.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html
    """

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
        """Initialize the group-based K-fold splitter.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary that may include the name of the group
            column used to define the groups.
        """
        super().__init__(splits_data)
        self.group_column = splits_data.get("group_column", None)

    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate train/test index pairs while keeping groups together.

        Parameters
        ----------
        x : object
            Input dataset that can be converted to a pandas DataFrame.
        y : object
            Target values associated with ``x``. This argument is accepted for
            interface consistency but is not used directly by the splitter.
        n_splits : int
            Number of folds to create.
        shuffle : bool
            Whether samples should be shuffled before folding.
        random_state : int, optional
            Seed used for reproducible shuffling; retained for interface
            compatibility.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs preserving the group assignments.
        """
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
