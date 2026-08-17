from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import StratifiedKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class StratifiedKFoldSplitter(FoldSplitter):
    """Splitter that generates folds while preserving the class distribution.

    This strategy is particularly useful for classification problems with
    imbalanced labels, where each fold should retain a similar proportion of
    each class to produce a more meaningful and less biased estimate of model
    performance.

    It is commonly used in tabular and image classification tasks when the
    evaluation must reflect the original class distribution.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Stratified K-Fold",
        es="K-Fold Estratificado",
        pt="K-Fold Estratificado",
        de="Stratifiziertes K-Fold",
        zh="分层 K 折交叉验证",
    )
    FOLDS: bool = True
    SHUFFLE: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs while preserving class proportions.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose length determines the number of available samples.
        y : DashAIDataset
            Target values used to preserve the class distribution across folds.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for every stratified fold.
        """
        indexes = np.arange(len(x))

        try:
            y_labels = self.prepare_y(y)

            kf = StratifiedKFold(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=self.random_state,
            )
            folds = list(kf.split(indexes, y=y_labels))
        except ValueError as e:
            raise ValueError(f"Error in StratifiedKFold splitting: {e}") from e

        return folds
