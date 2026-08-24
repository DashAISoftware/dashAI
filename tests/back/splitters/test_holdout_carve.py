"""Cross-validation splitters keep a slice of the dataset out of the folds.

The reserved rows land in the trailing ``full_dataset`` entry's test partition,
which is what the final model is scored and explained against. With
``holdout=0`` the splitters behave as if the feature did not exist.
"""

import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.splitters.group_k_fold import GroupKFoldSplitter
from DashAI.back.splitters.k_fold import KFoldSplitter
from DashAI.back.splitters.repeated_k_fold import RepeatedKFoldSplitter
from DashAI.back.splitters.stratified_group_k_fold import StratifiedGroupKFoldSplitter
from DashAI.back.splitters.stratified_k_fold import StratifiedKFoldSplitter

ALL_SPLITTERS = [
    KFoldSplitter,
    StratifiedKFoldSplitter,
    GroupKFoldSplitter,
    StratifiedGroupKFoldSplitter,
    RepeatedKFoldSplitter,
]

# Group aware splitters move whole groups, so they cannot hit an exact row count.
GROUP_SPLITTERS = (GroupKFoldSplitter, StratifiedGroupKFoldSplitter)
GROUP_SIZE = 4


def dataset(rows: int = 100):
    """Build a dataset with a group column and a balanced binary target."""
    return to_dashai_dataset(
        pd.DataFrame(
            {
                "a": list(range(rows)),
                "group": [i // 4 for i in range(rows)],
                "y": [0, 1] * (rows // 2),
            }
        )
    )


def xy(rows: int = 100):
    ds = dataset(rows)
    return ds.select_columns(["a", "group"]), ds.select_columns(["y"])


def config(**overrides):
    base = {
        "n_splits": 4,
        "n_repeats": 2,
        "shuffle": True,
        "random_state": 42,
        "group_column": "group",
        "holdout": 0.1,
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("splitter_cls", ALL_SPLITTERS)
def test_holdout_lands_in_the_full_dataset_test_partition(splitter_cls):
    x, y = xy()
    _, _, indices = splitter_cls(config()).split(x, y)

    holdout = indices["full_dataset"]["test_indexes"]
    remaining = indices["full_dataset"]["train_indexes"]

    if splitter_cls in GROUP_SPLITTERS:
        assert abs(len(holdout) - 10) < GROUP_SIZE
    else:
        assert len(holdout) == 10
    assert len(holdout) + len(remaining) == 100
    assert set(holdout) | set(remaining) == set(range(100))
    assert not set(holdout) & set(remaining)


@pytest.mark.parametrize("splitter_cls", ALL_SPLITTERS)
def test_no_fold_ever_sees_a_holdout_row(splitter_cls):
    x, y = xy()
    _, _, indices = splitter_cls(config()).split(x, y)

    holdout = set(indices["full_dataset"]["test_indexes"])
    fold_keys = [k for k in indices if k.startswith("fold_")]
    assert fold_keys

    for key in fold_keys:
        fold = indices[key]
        assert not holdout & set(fold["train_indexes"])
        assert not holdout & set(fold["test_indexes"])
        # Folds partition exactly the rows left after the carve.
        assert set(fold["train_indexes"]) | set(fold["test_indexes"]) == set(
            indices["full_dataset"]["train_indexes"]
        )


@pytest.mark.parametrize("splitter_cls", ALL_SPLITTERS)
def test_holdout_zero_keeps_every_row_in_cross_validation(splitter_cls):
    x, y = xy()
    _, _, indices = splitter_cls(config(holdout=0)).split(x, y)

    assert indices["full_dataset"]["test_indexes"] == []
    assert len(indices["full_dataset"]["train_indexes"]) == 100


@pytest.mark.parametrize("splitter_cls", ALL_SPLITTERS)
def test_fold_datasets_match_the_reported_indexes(splitter_cls):
    x, y = xy()
    x_folds, y_folds, indices = splitter_cls(config()).split(x, y)

    for i, key in enumerate(k for k in indices if k.startswith("fold_")):
        assert len(x_folds[i]["train"]) == len(indices[key]["train_indexes"])
        assert len(x_folds[i]["test"]) == len(indices[key]["test_indexes"])

    expected_holdout = len(indices["full_dataset"]["test_indexes"])
    assert len(x_folds[-1]["train"]) == 100 - expected_holdout
    assert len(x_folds[-1]["test"]) == expected_holdout
    assert len(y_folds[-1]["test"]) == expected_holdout


def test_group_holdout_keeps_whole_groups_together():
    x, y = xy()
    groups = dataset().to_pandas()["group"]

    for splitter_cls in (GroupKFoldSplitter, StratifiedGroupKFoldSplitter):
        _, _, indices = splitter_cls(config()).split(x, y)
        holdout = indices["full_dataset"]["test_indexes"]
        remaining = indices["full_dataset"]["train_indexes"]

        holdout_groups = set(groups[holdout])
        remaining_groups = set(groups[remaining])
        assert holdout_groups
        assert not holdout_groups & remaining_groups


def test_stratified_holdout_preserves_the_class_balance():
    x, y = xy()
    labels = dataset().to_pandas()["y"]

    _, _, indices = StratifiedKFoldSplitter(config(holdout=0.2)).split(x, y)
    holdout = indices["full_dataset"]["test_indexes"]

    assert len(holdout) == 20
    assert sorted(labels[holdout].value_counts().tolist()) == [10, 10]


def test_the_carve_is_reproducible_and_seed_dependent():
    x, y = xy()

    first = KFoldSplitter(config(random_state=1)).split(x, y)[2]
    again = KFoldSplitter(config(random_state=1)).split(x, y)[2]
    other = KFoldSplitter(config(random_state=99)).split(x, y)[2]

    assert (
        first["full_dataset"]["test_indexes"] == again["full_dataset"]["test_indexes"]
    )
    assert (
        first["full_dataset"]["test_indexes"] != other["full_dataset"]["test_indexes"]
    )


def test_holdout_is_declared_in_every_fold_splitter_schema():
    for splitter_cls in ALL_SPLITTERS:
        holdout = splitter_cls.get_schema()["properties"]["holdout"]
        assert holdout["type"] == "number"
        assert holdout["minimum"] == 0
        assert holdout["maximum"] == 0.5
        assert holdout["placeholder"] == 0.1
