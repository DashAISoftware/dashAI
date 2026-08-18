from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

import numpy as np
from sklearn.model_selection import LeaveOneOut

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.core.utils import MultilingualString

from .fold_splitter import FoldSplitter

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class LeaveOneOutSplitterSchema(BaseSchema):
    """Schema that configures the Leave-One-Out splitter.

    Leave-One-Out creates one fold per sample, using it as the test set while
    every other sample is used for training. It has no configurable
    parameters: the number of folds is always the dataset size, and
    ``sklearn.model_selection.LeaveOneOut`` is deterministic, so it does not
    accept ``n_splits``, ``shuffle``, or ``random_state``.
    """


class LeaveOneOutSplitter(FoldSplitter):
    """Splitter that creates one fold per sample by leaving one example out at a time.

    This exhaustive strategy is useful for very small datasets where every
    observation should be tested in turn and the computational cost remains
    acceptable. It is often used as a reference method in small-sample studies
    and in settings where a highly thorough estimate of performance is desired.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneOut.html
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "RegressionTask",
        "TranslationTask",
        "ImageClassificationTask",
    ]
    DISPLAY_NAME: str = MultilingualString(
        en="Leave-One-Out",
        es="Dejar Uno Fuera",
        pt="Deixar Um Fora",
        de="Leave-One-Out",
        zh="留一法",
    )
    COMPATIBLE_INNER_SPLITTERS = ["KFoldSplitter", "StratifiedKFoldSplitter"]
    SCHEMA = LeaveOneOutSplitterSchema

    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs following the leave-one-out scheme.

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
            A list of train/test index pairs, one for each sample in the dataset.
        """
        indexes = np.arange(len(x))

        try:
            loo = LeaveOneOut()
            folds = list(loo.split(indexes))
        except ValueError as e:
            raise ValueError(f"Error in LeaveOneOut splitting: {e}") from e

        return folds
