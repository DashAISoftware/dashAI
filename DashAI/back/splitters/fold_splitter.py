from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset_cv

from .base_splitter import BaseSplitter

if TYPE_CHECKING:
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class FoldSplitter(BaseSplitter):
    """Shared base class for splitters that generate multiple cross-validation folds.

    This abstraction centralizes the logic required by fold-based evaluation
    strategies, including the creation of several train/test partitions and the
    addition of a full-data fold for training on the complete dataset.
    """

    def __init__(self, splits_data):
        """Initialize the fold splitter with the requested number of splits.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary that may include the number of folds to
            generate.
        """
        super().__init__(splits_data)
        self.n_splits = splits_data.get("n_splits", 5)

    @abstractmethod
    def split_indexes(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> List[Tuple[List, List]]:
        """Generate train/test index pairs for each fold.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset to be partitioned.
        y : DashAIDataset
            Target values associated with ``x``.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for every fold.
        """
        raise NotImplementedError(
            "The split indexes method must be implemented by subclasses."
        )

    def split(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> Tuple[List[DatasetDict], List[DatasetDict], Dict[str, Any]]:
        """Create folds and return both the partitioned datasets and the indices.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset to split.
        y : DashAIDataset
            Target values associated with ``x``.

        Returns
        -------
        tuple[list, list, dict]
            A tuple containing the split datasets for every fold and a mapping
            from fold names to their corresponding train/test indices.

        Raises
        ------
        ValueError
            If the number of samples is lower than the number of requested
            splits.
        """
        if len(x) < self.n_splits:
            raise ValueError(
                f"""Number of splits (n_splits={self.n_splits}) cannot be
                greater than the number of samples ({len(x)})."""
            )

        folds = self.split_indexes(x, y)

        indices = {}
        x_prepared, y_prepared = [], []

        for i, (train_idx, test_idx) in enumerate(folds):
            indice = {
                "train_indexes": train_idx.tolist(),
                "test_indexes": test_idx.tolist(),
            }
            indices[f"fold_{i}"] = indice

            x_prepared.append(split_dataset_cv(x, indice, train_idx, test_idx))
            y_prepared.append(split_dataset_cv(y, indice, train_idx, test_idx))

        # Add the full dataset as the last fold for training on all data
        indice = {"train_indexes": list(range(len(x))), "test_indexes": []}
        indices["full_dataset"] = indice
        x_prepared.append(split_dataset_cv(x, indice, list(range(len(x))), []))
        y_prepared.append(split_dataset_cv(y, indice, list(range(len(x))), []))

        return x_prepared, y_prepared, indices
