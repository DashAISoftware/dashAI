"""Each splitter decides which partitions of its runs an explainer may target.

Nothing outside the splitter classes knows the payload layout, so a splitter
with a different partitioning scheme, including one shipped by a plugin,
participates without changes elsewhere. Both families agree on the name of the
partition the trained model never saw: a holdout run keeps its test split out
of training, and a fold based run reserves rows that no fold and no
hyperparameter search ever touched, which are the same rows its test metrics
are measured on.
"""

import pytest

from DashAI.back.splitters.holdout import HoldoutSplitter
from DashAI.back.splitters.k_fold import KFoldSplitter
from DashAI.back.splitters.splits_payload import explainable_indexes

HOLDOUT_RUN = {
    "train_indexes": [0, 1, 2, 3, 4, 5],
    "test_indexes": [6, 7],
    "val_indexes": [8, 9],
}

HOLDOUT_RUN_WITHOUT_TEST = {
    "train_indexes": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    "test_indexes": [],
    "val_indexes": [],
}

CV_RUN = {
    "fold_0": {"train_indexes": [0, 1, 2], "test_indexes": [3, 4]},
    "full_dataset": {"train_indexes": [0, 1, 2, 3, 4], "test_indexes": [5, 6]},
}

CV_RUN_WITHOUT_RESERVED_ROWS = {
    "fold_0": {"train_indexes": [0, 1, 2], "test_indexes": [3, 4]},
    "full_dataset": {"train_indexes": [0, 1, 2, 3, 4], "test_indexes": []},
}


def test_holdout_offers_its_three_partitions_and_the_whole_dataset():
    assert HoldoutSplitter.explainable_splits(HOLDOUT_RUN) == [
        {"name": "train", "rows": 6},
        {"name": "test", "rows": 2},
        {"name": "val", "rows": 2},
        {"name": "all", "rows": 10},
    ]


def test_cross_validation_offers_its_reserved_rows_as_the_test_partition():
    """The folds are never offered: the saved model was refit over all of them."""
    assert KFoldSplitter.explainable_splits(CV_RUN) == [
        {"name": "train", "rows": 5},
        {"name": "test", "rows": 2},
        {"name": "all", "rows": 7},
    ]


@pytest.mark.parametrize(
    ("splitter_class", "payload"),
    [
        (HoldoutSplitter, HOLDOUT_RUN_WITHOUT_TEST),
        (KFoldSplitter, CV_RUN_WITHOUT_RESERVED_ROWS),
    ],
)
def test_a_run_without_unseen_rows_offers_nothing(splitter_class, payload):
    assert splitter_class.explainable_splits(payload) == []


def test_the_refusal_names_the_partition_that_came_up_empty():
    for splitter_class, payload in (
        (KFoldSplitter, CV_RUN_WITHOUT_RESERVED_ROWS),
        (HoldoutSplitter, HOLDOUT_RUN_WITHOUT_TEST),
    ):
        with pytest.raises(ValueError, match="test partition"):
            explainable_indexes(splitter_class, payload)


def test_indexes_of_each_family_land_in_the_right_slots():
    assert explainable_indexes(HoldoutSplitter, HOLDOUT_RUN) == (
        [0, 1, 2, 3, 4, 5],
        [6, 7],
        [8, 9],
    )
    assert explainable_indexes(KFoldSplitter, CV_RUN) == ([0, 1, 2, 3, 4], [5, 6], [])


def test_a_payload_from_another_splitter_is_refused():
    with pytest.raises(ValueError, match="do not match the splitter"):
        explainable_indexes(KFoldSplitter, HOLDOUT_RUN)
