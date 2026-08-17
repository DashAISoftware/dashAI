from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import RepeatedKFold

from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class RepeatedKFoldSplitter(FoldSplitter):
    """Splitter that repeats the K-fold procedure multiple times.

    Repeating the folds helps reduce the variance of the performance estimate by
    averaging over several random resamplings of the same evaluation scheme. This
    is useful when a single K-fold run is too noisy or when more stable estimates
    are needed for model comparison.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.RepeatedKFold.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Repeated K-Fold",
        es="K-Fold Repetido",
        pt="K-Fold Repetido",
        de="Wiederholtes K-Fold",
        zh="重复 K 折交叉验证",
    )
    FOLDS: bool = True
    REPEATS: bool = True
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]

    def __init__(self, splits_data):
        """Initialize the repeated K-fold splitter.

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
        """Generate train/test index pairs for each repetition of the K-fold split.

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
            A list of train/test index pairs for all folds and repeats.
        """
        indexes = np.arange(len(x))

        try:
            rkf = RepeatedKFold(
                n_splits=self.n_splits,
                n_repeats=self.n_repeats,
                random_state=self.random_state,
            )
            folds = list(rkf.split(indexes))

        except ValueError as e:
            raise ValueError(f"Error in RepeatedKFold splitting: {e}") from e

        return folds
