from typing import Any, Dict, List, Tuple, Union

from DashAI.back.dataloaders.classes.dashai_dataset import split_dataset

from .base_splitter import BaseSplitter


class HoldoutSplitter(BaseSplitter):
    """Splitter that creates train, test, and validation partitions for holdout
    evaluation.

    This strategy is appropriate when a single representative split is sufficient
    for model selection or final assessment. It is commonly used for quick
    experiments, hyperparameter tuning, and production-ready evaluation where
    the computational cost of repeated cross-validation would be excessive.

    It is especially useful for large datasets and for workflows that require a
    simple partitioning scheme with clear train/test/validation boundaries.

    References
    ----------
    - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.train_test_split.html
    """

    def __init__(self, splits_data):
        """Initialize the holdout splitter with the requested proportions.

        Parameters
        ----------
        splits_data : dict
            Configuration dictionary containing train, test, and validation
            proportions, as well as optional custom indices and stratification
            settings.
        """
        super().__init__(splits_data)
        self.train_size = splits_data.get("train", None)
        self.test_size = splits_data.get("test", None)
        self.val_size = splits_data.get("validation", None)
        self.splitted_indexes = splits_data.get("splitted_indexes", {})
        self.stratify = splits_data.get("stratify", False)

    def split(self, x, y) -> Tuple[object, object, Dict[str, Any]]:
        """Split the input data into holdout partitions and return the
        resulting datasets.

        Parameters
        ----------
        x : object
            Input dataset to partition.
        y : object
            Target values associated with ``x``.

        Returns
        -------
        tuple
            A tuple containing the partitioned input and output datasets, along
            with the indices used for each split.
        """
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
            Whether the split should preserve class proportions, by default False.
        labels : List or None, optional
            Labels used for stratified splitting when requested.

        Returns
        -------
        tuple[List, List, List]
            Lists of indices for the training, test, and validation partitions.
        """
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
