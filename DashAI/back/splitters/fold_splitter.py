from abc import abstractmethod
from typing import Dict, List, Tuple

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset_cv

from .base_splitter import BaseSplitter


class FoldSplitter(BaseSplitter):
    def __init__(self, splits_data):
        super().__init__(splits_data)
        self.n_splits = splits_data.get("n_splits", 5)

    @abstractmethod
    def split_indexes(self, x, y, n_splits, shuffle, random_state=42):
        raise NotImplementedError(
            "The split indexes method must be implemented by subclasses."
        )

    def split(self, x, y) -> Tuple[List[object], List[object], Dict]:
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
