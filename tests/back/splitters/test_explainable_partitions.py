"""Each splitter decides which partitions of its runs an explainer may target.

Nothing outside the splitter classes knows the names or the payload layout, so a
splitter with a different partitioning scheme, including one shipped by a
plugin, participates without changes elsewhere.
"""

import pytest

from DashAI.back.splitters.base_splitter import BaseSplitter
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

HOLDOUT_RUN_VALIDATION_ONLY = {
    "train_indexes": [0, 1, 2, 3, 4, 5, 6, 7],
    "test_indexes": [],
    "val_indexes": [8, 9],
}

CV_RUN = {
    "fold_0": {"train_indexes": [0, 1, 2], "test_indexes": [3, 4]},
    "full_dataset": {"train_indexes": [0, 1, 2, 3, 4], "test_indexes": [5, 6]},
}

CV_RUN_WITHOUT_HOLDOUT = {
    "fold_0": {"train_indexes": [0, 1, 2], "test_indexes": [3, 4]},
    "full_dataset": {"train_indexes": [0, 1, 2, 3, 4], "test_indexes": []},
}


class ProbeSplitter(BaseSplitter):
    """A splitter that names its unseen rows differently from both families."""

    EVALUATION_PARTITION = "probe"

    def split(self, x, y):
        raise NotImplementedError

    def split_indexes(self, x, y):
        raise NotImplementedError

    @classmethod
    def explainable_partitions(cls, split_indexes):
        return {"train": split_indexes["kept"], "probe": split_indexes["probe"]}


def test_holdout_offers_its_three_partitions_and_the_whole_dataset():
    assert HoldoutSplitter.explainable_splits(HOLDOUT_RUN) == [
        {"name": "train", "rows": 6},
        {"name": "test", "rows": 2},
        {"name": "val", "rows": 2},
        {"name": "all", "rows": 10},
    ]


def test_cross_validation_names_its_reserved_rows_holdout_not_test():
    splits = KFoldSplitter.explainable_splits(CV_RUN)

    assert splits == [
        {"name": "train", "rows": 5},
        {"name": "holdout", "rows": 2},
        {"name": "all", "rows": 7},
    ]
    # "test" would collide with the per-fold test metrics reported for the run.
    assert "test" not in [split["name"] for split in splits]


def test_a_splitter_defines_its_own_partition_names():
    payload = {"kept": [0, 1, 2], "probe": [3, 4]}

    assert ProbeSplitter.explainable_splits(payload) == [
        {"name": "train", "rows": 3},
        {"name": "probe", "rows": 2},
        {"name": "all", "rows": 5},
    ]
    assert explainable_indexes(ProbeSplitter, payload) == ([0, 1, 2], [3, 4], [])


@pytest.mark.parametrize(
    ("splitter_class", "payload"),
    [
        (HoldoutSplitter, HOLDOUT_RUN_WITHOUT_TEST),
        (KFoldSplitter, CV_RUN_WITHOUT_HOLDOUT),
        (ProbeSplitter, {"kept": [0, 1], "probe": []}),
    ],
)
def test_a_run_without_unseen_rows_offers_nothing(splitter_class, payload):
    assert splitter_class.explainable_splits(payload) == []


def test_the_refusal_names_the_partition_that_came_up_empty():
    with pytest.raises(ValueError, match="holdout partition"):
        explainable_indexes(KFoldSplitter, CV_RUN_WITHOUT_HOLDOUT)

    with pytest.raises(ValueError, match="test partition"):
        explainable_indexes(HoldoutSplitter, HOLDOUT_RUN_WITHOUT_TEST)

    with pytest.raises(ValueError, match="probe partition"):
        explainable_indexes(ProbeSplitter, {"kept": [0, 1], "probe": []})


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


def test_a_holdout_run_without_a_test_partition_is_explained_on_validation():
    """A 0.8 / 0 / 0.2 split is valid, and validation is data the model
    never fitted on, so the run is explainable even though the partition
    explanations normally use came up empty."""
    assert HoldoutSplitter.explainable_splits(HOLDOUT_RUN_VALIDATION_ONLY) == [
        {"name": "train", "rows": 8},
        {"name": "val", "rows": 2},
        {"name": "all", "rows": 10},
    ]

    train, evaluation, validation = explainable_indexes(
        HoldoutSplitter, HOLDOUT_RUN_VALIDATION_ONLY
    )
    assert train == [0, 1, 2, 3, 4, 5, 6, 7]
    # The rows an explanation is measured on fall back to validation, so a
    # global explainer reading the evaluation slot gets unseen rows instead of
    # an empty dataset.
    assert evaluation == [8, 9]
    assert validation == [8, 9]
