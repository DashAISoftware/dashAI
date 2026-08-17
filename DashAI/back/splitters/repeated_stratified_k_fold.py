from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import RepeatedStratifiedKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RepeatedStratifiedKFoldSplitter(FoldSplitter):
    """Splitter that repeats the stratified K-fold procedure multiple times.

    This strategy preserves class proportions in each fold while repeating the
    partitioning scheme several times, which makes it particularly useful for
    imbalanced classification problems where a stable and representative estimate
    is needed.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.RepeatedStratifiedKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Repeated Stratified K-Fold",
        es="K-Fold Estratificado Repetido",
        pt="K-Fold Estratificado Repetido",
        de="Wiederholtes stratifiziertes K-Fold",
        zh="重复分层 K 折交叉验证",
    )
    FOLDS: bool = True
    REPEATS: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]

    def __init__(self, splits_data):
        """Initialize the repeated stratified K-fold splitter.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary that may include the number of repeats.
        """
        super().__init__(splits_data)
        self.n_repeats = splits_data.get("n_repeats", 2)

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs preserving class proportions.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose length determines the number of available samples.
        y : DashAIDataset
            Target values used to preserve class distribution across folds.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for all folds and repeats.
        """
        indexes = np.arange(len(x))

        try:
            y_labels = self.prepare_y(y)

            rskf = RepeatedStratifiedKFold(
                n_splits=self.n_splits,
                n_repeats=self.n_repeats,
                random_state=self.random_state,
            )
            folds = list(rskf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in RepeatedStratifiedKFold splitting: {e}") from e

        return folds
