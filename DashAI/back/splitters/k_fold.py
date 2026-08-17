from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import KFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class KFoldSplitter(FoldSplitter):
    """Splitter that generates K folds for cross-validation.

    This strategy is a standard choice for estimating model performance when the
    data is not naturally grouped and the goal is to obtain several
    semi-independent evaluation partitions. It is widely used in supervised
    learning tasks such as tabular classification, regression, text processing,
    and image classification.

    It is especially useful when a reliable estimate of generalization is needed
    without the additional complexity of group-aware or stratified schemes.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="K-Fold",
        es="K-Fold",
        pt="K-Fold",
        de="K-Fold",
        zh="K 折交叉验证",
    )
    FOLDS: bool = True
    SHUFFLE: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs for each K-fold split.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset whose length determines the number of available samples.
        y : DashAIDataset
            Target values associated with ``x``. This argument is accepted for
            interface consistency but is not used directly by the splitter.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for every fold.
        """
        indexes = np.arange(len(x))

        try:
            kf = KFold(
                n_splits=self.n_splits,
                shuffle=self.shuffle,
                random_state=self.random_state if self.shuffle else None,
            )
            folds = list(kf.split(indexes))
        except ValueError as e:
            raise ValueError(
                f"""Error in KFold splitting: {e}.
                Check if n_splits is less than or equal
                to the number of samples."""
            ) from e

        return folds
