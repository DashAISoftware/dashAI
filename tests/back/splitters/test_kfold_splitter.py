from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    select_columns,
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.splitters.k_fold import KFoldSplitter


# ---------- FIXTURE ----------
@pytest.fixture
def sample_data():
    ruta = Path("tests") / "back" / "splitters" / "iris.csv"
    test_df = pd.read_csv(ruta)

    dataset = to_dashai_dataset(test_df)

    schema = {
        "SepalLengthCm": {"type": "Float", "dtype": "float64"},
        "SepalWidthCm": {"type": "Float", "dtype": "float64"},
        "PetalLengthCm": {"type": "Float", "dtype": "float64"},
        "PetalWidthCm": {"type": "Float", "dtype": "float64"},
        "Species": {"type": "Categorical", "dtype": "string"},
    }

    dataset = transform_dataset_with_schema(dataset, schema)

    X, y = select_columns(
        dataset,
        input_columns=[
            "SepalLengthCm",
            "SepalWidthCm",
            "PetalLengthCm",
            "PetalWidthCm",
        ],
        output_columns=["Species"],
    )
    return X, y


def test_kfold_number_of_splits(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})
    folds = splitter.split_indexes(X, y, n_splits=5, shuffle=False)

    assert len(folds) == 5


def test_kfold_all_samples_used_in_test(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})
    folds = splitter.split_indexes(X, y, n_splits=5, shuffle=False)

    test_indices = []

    for _, test_idx in folds:
        test_indices.extend(test_idx)

    assert sorted(test_indices) == list(range(len(X)))


def test_kfold_no_overlap(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})
    folds = splitter.split_indexes(X, y, n_splits=5, shuffle=False)

    for train_idx, test_idx in folds:
        assert len(set(train_idx) & set(test_idx)) == 0


def test_kfold_split_sizes(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})
    folds = splitter.split_indexes(X, y, n_splits=5, shuffle=False)

    n = len(X)

    for train_idx, test_idx in folds:
        assert len(train_idx) + len(test_idx) == n


def test_kfold_shuffle_changes_splits(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})

    folds1 = splitter.split_indexes(X, y, n_splits=5, shuffle=False)
    folds2 = splitter.split_indexes(X, y, n_splits=5, shuffle=True, random_state=50)

    assert any(
        not (train1 == train2).all() or not (test1 == test2).all()
        for (train1, test1), (train2, test2) in zip(folds1, folds2)
    )


def test_kfold_invalid_splits(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})

    with pytest.raises(ValueError, match="n_splits"):
        splitter.split_indexes(X, y, n_splits=len(X) + 1, shuffle=False)


def test_kfold_reproducibility(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({})

    folds1 = splitter.split_indexes(X, y, 5, shuffle=True, random_state=42)
    folds2 = splitter.split_indexes(X, y, 5, shuffle=True, random_state=42)

    assert all(
        np.array_equal(train1, train2) and np.array_equal(test1, test2)
        for (train1, test1), (train2, test2) in zip(folds1, folds2)
    )


# Split method
def test_number_of_folds(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({"n_splits": 5})
    x_split, y_split, _ = splitter.split(X, y)

    assert len(x_split) == 6  # incluye full_dataset


def test_fold_structure(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({"n_splits": 5})
    x_split, _, _ = splitter.split(X, y)

    for fold in x_split[:-1]:  # ignorar full_dataset
        assert "train" in fold
        assert "test" in fold


def test_no_overlap(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({"n_splits": 5})
    _, _, indices = splitter.split(X, y)

    for k, v in indices.items():
        if k == "full_dataset":
            continue

        train = set(v["train_indexes"])
        test = set(v["test_indexes"])

        assert len(train & test) == 0


def test_full_dataset(sample_data):
    X, y = sample_data

    splitter = KFoldSplitter({"n_splits": 5})
    _, _, indices = splitter.split(X, y)

    full = indices["full_dataset"]

    assert full["test_indexes"] == []
    assert full["train_indexes"] == list(range(len(X)))
