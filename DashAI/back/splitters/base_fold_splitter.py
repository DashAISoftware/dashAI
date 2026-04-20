from typing import Dict, List, Tuple

from sklearn.naive_bayes import abstractmethod

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset_cv

from .base_splitter import BaseSplitter


class BaseFoldSplitter(BaseSplitter):
    def __init__(self, splits_data):
        super().__init__(splits_data)
        self.n_splits = splits_data.get("n_splits", 5)

    @abstractmethod
    def split_indexes(
        self, total_rows, n_splits, shuffle, random_state=42, y_labels=None
    ):
        raise NotImplementedError(
            "The split indexes method must be implemented by subclasses."
        )

    def split(self, x, y) -> Tuple[List[object], List[object], Dict]:
        total_rows = len(x)

        folds = self.split_indexes(
            total_rows=total_rows,
            n_splits=self.n_splits,
            shuffle=self.shuffle,
            random_state=self.random_state,
            y_labels=self.prepare_y(y),
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
        indice = {"train_indexes": list(range(total_rows)), "test_indexes": []}
        indices["full_dataset"] = indice
        x_prepared.append(split_dataset_cv(x, indice, list(range(total_rows)), []))
        y_prepared.append(split_dataset_cv(y, indice, list(range(total_rows)), []))

        return x_prepared, y_prepared, indices
