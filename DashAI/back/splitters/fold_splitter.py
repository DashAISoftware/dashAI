from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset_cv

from .base_splitter import BaseSplitter

if TYPE_CHECKING:
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


def sklearn_random_state(shuffle: bool, random_state: int):
    """Adapt a seed to scikit-learn's shuffle contract.

    The ``KFold`` family raises when ``random_state`` is set while ``shuffle``
    is False, so the seed is only forwarded when it can have an effect. Meant
    for the splitters that expose ``shuffle`` as a parameter; the repeated
    splitters always shuffle and take no such argument, so they pass their seed
    through directly.

    Parameters
    ----------
    shuffle : bool
        Whether the splitter shuffles before splitting.
    random_state : int
        The configured seed.

    Returns
    -------
    int or None
        ``random_state`` when shuffling, ``None`` otherwise.
    """
    return random_state if shuffle else None


class FoldSplitter(BaseSplitter):
    """Shared base class for splitters that generate multiple cross-validation folds.

    This abstraction centralizes the logic required by fold-based evaluation
    strategies, including the creation of several train/test partitions and the
    addition of a full-data fold for training on the complete dataset.
    """

    #: How the rows reserved for explanations are chosen. ``"random"`` samples
    #: them uniformly, ``"stratified"`` preserves the target distribution, and
    #: ``"group"`` moves whole groups so a group never spans the carve.
    HOLDOUT_STRATEGY: str = "random"

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
        self.holdout = splits_data.get("holdout", 0.1)

    @classmethod
    def get_metadata(cls) -> dict:
        """Return metadata describing the splitter's compatibility."""
        return {
            "compatibleInnerSplitters": getattr(cls, "COMPATIBLE_INNER_SPLITTERS", []),
        }

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

    def _carve_holdout(
        self, x: DashAIDataset, y: DashAIDataset
    ) -> Tuple[List[int], List[int]]:
        """Reserve the rows that stay out of cross-validation.

        The reserved rows are picked according to ``HOLDOUT_STRATEGY`` so the
        carve respects whatever the splitter guarantees: a stratified splitter
        keeps the class balance, and a grouped one never splits a group.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset being split.
        y : DashAIDataset
            Target values associated with ``x``.

        Returns
        -------
        tuple[list[int], list[int]]
            The reserved row indexes and the rows left for the folds, both as
            positions in the original dataset.

        Raises
        ------
        ValueError
            If the requested proportion leaves no rows on either side.
        """
        import numpy as np

        all_indexes = list(range(len(x)))
        if not self.holdout:
            return [], all_indexes

        n_holdout = int(round(len(x) * self.holdout))
        if n_holdout < 1 or len(x) - n_holdout < self.n_splits:
            raise ValueError(
                f"""A holdout of {self.holdout} leaves too few rows: it would
                reserve {n_holdout} of {len(x)} samples for explanations and
                leave {len(x) - n_holdout} for {self.n_splits} folds."""
            )

        indexes = np.arange(len(x))
        seed = self.random_state

        if self.HOLDOUT_STRATEGY == "group":
            from sklearn.model_selection import GroupShuffleSplit

            groups = x.to_pandas()[self.group_column]
            splitter = GroupShuffleSplit(
                n_splits=1, test_size=self.holdout, random_state=seed
            )
            pool, holdout = next(splitter.split(indexes, groups=groups))
        elif self.HOLDOUT_STRATEGY == "stratified":
            from sklearn.model_selection import StratifiedShuffleSplit

            splitter = StratifiedShuffleSplit(
                n_splits=1, test_size=self.holdout, random_state=seed
            )
            pool, holdout = next(splitter.split(indexes, y=self.prepare_y(y)))
        else:
            from sklearn.model_selection import ShuffleSplit

            splitter = ShuffleSplit(
                n_splits=1, test_size=self.holdout, random_state=seed
            )
            pool, holdout = next(splitter.split(indexes))

        return sorted(int(i) for i in holdout), sorted(int(i) for i in pool)

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
        holdout_indexes, fold_pool = self._carve_holdout(x, y)

        if len(fold_pool) < self.n_splits:
            raise ValueError(
                f"""Number of splits (n_splits={self.n_splits}) cannot be
                greater than the number of samples ({len(fold_pool)})."""
            )

        # The folds are built over the rows left after the carve, so
        # ``split_indexes`` sees a dataset without the reserved rows and returns
        # positions within it, which are mapped back to original row numbers.
        pool_x = x.select(fold_pool) if holdout_indexes else x
        pool_y = y.select(fold_pool) if holdout_indexes else y
        folds = self.split_indexes(pool_x, pool_y)

        indices = {}
        x_prepared, y_prepared = [], []

        for i, (train_positions, test_positions) in enumerate(folds):
            train_idx = [fold_pool[p] for p in train_positions]
            test_idx = [fold_pool[p] for p in test_positions]
            indice = {
                "train_indexes": train_idx,
                "test_indexes": test_idx,
            }
            indices[f"fold_{i}"] = indice

            x_prepared.append(split_dataset_cv(x, indice, train_idx, test_idx))
            y_prepared.append(split_dataset_cv(y, indice, train_idx, test_idx))

        # The trailing entry trains the final model. Its train partition is
        # every row the folds could use, and its test partition holds the rows
        # reserved for scoring and explaining that model, which is empty when no
        # holdout was requested.
        indice = {
            "train_indexes": fold_pool,
            "test_indexes": holdout_indexes,
        }
        indices["full_dataset"] = indice
        x_prepared.append(split_dataset_cv(x, indice, fold_pool, holdout_indexes))
        y_prepared.append(split_dataset_cv(y, indice, fold_pool, holdout_indexes))

        return x_prepared, y_prepared, indices
