from pathlib import Path

import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    select_columns,
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.splitters.holdout import HoldoutSplitter


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


# ---------- TEST 1: tamaños correctos ----------
def test_holdout_sizes(sample_data):
    X, y = sample_data

    splitter = HoldoutSplitter(
        {
            "train": 0.7,
            "test": 0.2,
            "validation": 0.1,
            "random_state": 42,
            "shuffle": True,
        }
    )

    x_split, y_split, indices = splitter.split(X, y)

    assert len(x_split["train"]) == 105
    assert len(x_split["test"]) == 30
    assert len(x_split["validation"]) == 15


# ---------- TEST 2: no pierde datos ----------
def test_no_data_loss(sample_data):
    X, y = sample_data

    splitter = HoldoutSplitter({"train": 0.7, "test": 0.2, "validation": 0.1})

    _, _, indices = splitter.split(X, y)

    total = (
        len(indices["train_indexes"])
        + len(indices["test_indexes"])
        + len(indices["val_indexes"])
    )

    assert total == len(X)


# ---------- TEST 3: no duplica datos ----------
def test_no_duplicate_indices(sample_data):
    X, y = sample_data

    splitter = HoldoutSplitter({"train": 0.7, "test": 0.2, "validation": 0.1})

    _, _, indices = splitter.split(X, y)

    all_indices = (
        indices["train_indexes"] + indices["test_indexes"] + indices["val_indexes"]
    )

    assert len(all_indices) == len(set(all_indices))


# ---------- TEST 4: no sets vacíos ----------
def test_no_empty_splits(sample_data):
    X, y = sample_data

    splitter = HoldoutSplitter({"train": 0.7, "test": 0.2, "validation": 0.1})

    x_split, _, _ = splitter.split(X, y)

    assert len(x_split["train"]) > 0
    assert len(x_split["test"]) > 0
    assert len(x_split["validation"]) > 0


# ---------- TEST 5: reproducibilidad ----------
def test_reproducibility(sample_data):
    X, y = sample_data

    config = {"train": 0.7, "test": 0.2, "validation": 0.1, "random_state": 42}

    splitter1 = HoldoutSplitter(config)
    splitter2 = HoldoutSplitter(config)

    _, _, idx1 = splitter1.split(X, y)
    _, _, idx2 = splitter2.split(X, y)

    assert idx1 == idx2


# ---------- TEST 6: estratificación ----------
def test_stratification(sample_data):
    from collections import Counter

    X, y = sample_data

    splitter = HoldoutSplitter(
        {"train": 0.7, "test": 0.2, "validation": 0.1, "stratify": True}
    )

    _, y_split, _ = splitter.split(X, y)

    # helper simple para extraer labels
    def get_labels(y):
        return y[y.column_names[0]] if hasattr(y, "column_names") else y

    def ratio(arr):
        c = Counter(arr)
        total = len(arr)
        return {k: v / total for k, v in c.items()}

    original = ratio(get_labels(y))

    for split in ["train", "test", "validation"]:
        split_ratio = ratio(get_labels(y_split[split]))

        for cls in original:
            assert abs(split_ratio.get(cls, 0) - original[cls]) < 0.1


# ---------- TEST 7: sin test set ----------
def test_no_test_split(sample_data):
    X, y = sample_data

    splitter = HoldoutSplitter({"train": 0.8, "test": 0.0, "validation": 0.2})

    x_split, _, _ = splitter.split(X, y)

    assert len(x_split["test"]) == 0


# ---------- TEST 8: sin validation ----------
def test_no_validation_split(sample_data):
    X, y = sample_data

    splitter = HoldoutSplitter({"train": 0.8, "test": 0.2, "validation": 0.0})

    x_split, _, _ = splitter.split(X, y)

    assert len(x_split["validation"]) == 0
