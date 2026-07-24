from abc import abstractmethod
from typing import Any, Dict, List, Tuple

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset_cv

from .base_splitter import BaseSplitter


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

    @classmethod
    def get_metadata(cls) -> dict:
        """Return metadata describing the feature capabilities of the splitter."""
        metadata = {
            "hasFolds": getattr(cls, "FOLDS", False),
            "hasRepeats": getattr(cls, "REPEATS", False),
            "hasShuffle": getattr(cls, "SHUFFLE", False),
            "hasGroups": getattr(cls, "GROUPS", False),
            "compatibleInnerSplitters": getattr(cls, "COMPATIBLE_INNER_SPLITTERS", []),
        }

        return metadata

    @abstractmethod
    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        """Generate train/test index pairs for each fold.

        Parameters
        ----------
        x : object
            Input dataset to be partitioned.
        y : object
            Target values associated with ``x``.
        n_splits : int
            Number of folds to generate.
        shuffle : bool
            Whether the samples should be shuffled before splitting.
        random_state : int, optional
            Seed used to make shuffling reproducible, by default 42.

        Returns
        -------
        list[tuple]
            A list of train/test index pairs for every fold.
        """
        raise NotImplementedError(
            "The split indexes method must be implemented by subclasses."
        )

    def split(self, x, y) -> Tuple[List[object], List[object], Dict[str, Any]]:
        """Create folds and return both the partitioned datasets and the indices.

        Parameters
        ----------
        x : object
            Input dataset to split.
        y : object
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

        folds = self.split_indexes(
            x=x,
            y=y,
            n_splits=self.n_splits,
            shuffle=self.shuffle,
            random_state=self.random_state,
        )

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
