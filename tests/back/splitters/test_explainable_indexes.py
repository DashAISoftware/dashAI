"""Explainers need one flat set of indexes regardless of the evaluation strategy."""

import pytest

from DashAI.back.splitters.splits_payload import explainable_indexes

HOLDOUT_RUN = {
    "train_indexes": [0, 1, 2, 3, 4, 5],
    "test_indexes": [6, 7],
    "val_indexes": [8, 9],
}

CV_RUN_WITH_HOLDOUT = {
    "fold_0": {"train_indexes": [0, 1, 2], "test_indexes": [3, 4]},
    "fold_1": {"train_indexes": [3, 4], "test_indexes": [0, 1, 2]},
    "full_dataset": {"train_indexes": [0, 1, 2, 3, 4], "test_indexes": [5, 6]},
}

CV_RUN_WITHOUT_HOLDOUT = {
    "fold_0": {"train_indexes": [0, 1, 2], "test_indexes": [3, 4]},
    "full_dataset": {"train_indexes": [0, 1, 2, 3, 4], "test_indexes": []},
}


def test_holdout_run_indexes_pass_through():
    assert explainable_indexes(HOLDOUT_RUN) == (
        [0, 1, 2, 3, 4, 5],
        [6, 7],
        [8, 9],
    )


def test_cross_validation_run_uses_the_reserved_rows_as_its_test_split():
    train, test, val = explainable_indexes(CV_RUN_WITH_HOLDOUT)

    assert train == [0, 1, 2, 3, 4]
    assert test == [5, 6]
    assert val == []


def test_cross_validation_run_without_reserved_rows_is_refused():
    with pytest.raises(ValueError, match="reserved no data"):
        explainable_indexes(CV_RUN_WITHOUT_HOLDOUT)


def test_unknown_shape_is_refused():
    with pytest.raises(ValueError, match="neither a holdout nor"):
        explainable_indexes({"something": "else"})
