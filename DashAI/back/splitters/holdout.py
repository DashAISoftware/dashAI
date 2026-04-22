from typing import List, Tuple, Union

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset

from .base_splitter import BaseSplitter


class HoldoutSplitter(BaseSplitter):
    def __init__(self, splits_data):
        super().__init__(splits_data)
        # actualmente están como "train", "test" y "val"
        self.train_size = splits_data.get("train_size", None)
        self.test_size = splits_data.get("test_size", None)
        self.val_size = splits_data.get("val_size", None)
        self.splitted_indexes = splits_data.get("splitted_indexes", {})
        self.stratify = splits_data.get("stratify", False)

    def split(self, x, y) -> Tuple[object, object, List[List]]:
        # Si algún tamaño es None, se asume que se asignaron indices manualmente
        if all(idx is None for idx in [self.train_size, self.test_size, self.val_size]):
            train_indices = self.splitted_indexes.get("train_indexes", [])
            test_indices = self.splitted_indexes.get("test_indexes", [])
            val_indices = self.splitted_indexes.get("val_indexes", [])

            indices = self.splitted_indexes

        else:
            total_rows = len(x)

            labels = None
            if self.stratify:
                labels = self.prepare_y(y)

            train_indices, test_indices, val_indices = self.split_indexes(
                total_rows=total_rows,
                train_size=self.train_size,
                test_size=self.test_size,
                val_size=self.val_size,
                shuffle=self.shuffle,
                stratify=self.stratify,
                labels=labels,
                seed=self.random_state,
            )

            indices = {
                "train_indexes": train_indices,
                "test_indexes": test_indices,
                "val_indexes": val_indices,
            }

        x_prepared = split_dataset(x, train_indices, test_indices, val_indices)
        y_prepared = split_dataset(y, train_indices, test_indices, val_indices)

        return x_prepared, y_prepared, indices

    def split_indexes(
        self,
        total_rows: int,
        train_size: float,
        test_size: float,
        val_size: float,
        seed: Union[int, None] = None,
        shuffle: bool = True,
        stratify: bool = False,
        labels: Union[List, None] = None,
    ) -> Tuple[List, List, List]:
        """Generate lists with train, test and validation indexes.

        The algorithm for splitting the dataset is as follows:

        1. The dataset is divided into a training and a test-validation split
            (sum of test_size and val_size).
        2. The test and validation set is generated from the test-validation set,
            where the size of the test-validation set is now considered to be 100%.
            Therefore, the sizes of the test and validation sets will now be
            calculated as 100%, i.e. as val_size/(test_size+val_size) and
            test_size/(test_size+val_size) respectively.

        Example:

        If we split a dataset into 0.8 training, a 0.1 test, and a 0.1 validation,
        in the first process we split the training data with 80% of the data, and
        the test-validation data with the remaining 20%; and then in the second
        process we split this 20% into 50% test and 50% validation.

        Parameters
        ----------
        total_rows : int
            Size of the Dataset.
        train_size : float
            Proportion of the dataset for train split (in 0-1).
        test_size : float
            Proportion of the dataset for test split (in 0-1).
        val_size : float
            Proportion of the dataset for validation split (in 0-1).
        seed : Union[int, None], optional
            Set seed to control to enable replicability, by default None
        shuffle : bool, optional
            If True, the data will be shuffled when splitting the dataset,
            by default True.
        stratify : bool, optional
            If True, the data will be stratified when splitting the dataset,
            by default False.

        Returns
        -------
        Tuple[List, List, List]
            Train, Test and Validation indexes.
        """

        # Generate shuffled indexes
        if seed is None:
            seed = 42
        import numpy as np
        from sklearn.model_selection import train_test_split

        indexes = np.arange(total_rows)
        stratify_labels = np.array(labels) if stratify else None

        if test_size == 0 and val_size == 0:
            return indexes.tolist(), [], []

        if test_size == 0:
            train_indexes, val_indexes = train_test_split(
                indexes,
                train_size=train_size,
                random_state=seed,
                shuffle=shuffle,
                stratify=stratify_labels,
            )
            return train_indexes.tolist(), [], val_indexes.tolist()

        if val_size == 0:
            train_indexes, test_indexes = train_test_split(
                indexes,
                train_size=train_size,
                random_state=seed,
                shuffle=shuffle,
                stratify=stratify_labels,
            )
            return train_indexes.tolist(), test_indexes.tolist(), []

        test_val = test_size + val_size
        val_proportion = test_size / test_val

        train_indexes, test_val_indexes = train_test_split(
            indexes,
            train_size=train_size,
            random_state=seed,
            shuffle=shuffle,
            stratify=stratify_labels,
        )

        stratify_labels_test_val = (
            stratify_labels[test_val_indexes] if stratify else None
        )

        test_indexes, val_indexes = train_test_split(
            test_val_indexes,
            train_size=val_proportion,
            random_state=seed,
            shuffle=shuffle,
            stratify=stratify_labels_test_val,
        )
        return train_indexes.tolist(), test_indexes.tolist(), val_indexes.tolist()
