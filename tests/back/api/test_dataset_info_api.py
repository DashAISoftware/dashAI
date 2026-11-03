"""GET /dataset/{id}/info: what the session wizard reads of a dataset.

The wizard offers a predefined split only when the dataset carries partitions
of its own, and shows their shares. Both come from here, so the wizard divides
no sizes itself.
"""

import json

import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import get_dataset_info


def _write_splits(path, total_rows, train=0, validation=0, test=0):
    split_indices = {
        "train": list(range(train)),
        "validation": list(range(train, train + validation)),
        "test": list(range(train + validation, train + validation + test)),
    }
    (path / "splits.json").write_text(
        json.dumps({"total_rows": total_rows, "split_indices": split_indices}),
        encoding="utf-8",
    )
    return str(path)


def test_a_dataset_with_partitions_of_its_own_gives_their_shares(tmp_path):
    info = get_dataset_info(_write_splits(tmp_path, 10, train=6, test=4))

    assert info["predefined_splits"] == {"train": 0.6, "validation": 0.0, "test": 0.4}


def test_a_dataset_without_partitions_of_its_own_gives_none(tmp_path):
    info = get_dataset_info(_write_splits(tmp_path, 10))

    assert info["predefined_splits"] is None


def test_a_small_partition_still_counts(tmp_path):
    # One row in a thousand rounds to 0.00 in the wizard, which then took the
    # dataset for one without partitions.
    info = get_dataset_info(_write_splits(tmp_path, 1000, train=999, test=1))

    assert info["predefined_splits"]["test"] == pytest.approx(0.001)


def test_partitions_without_a_row_count_share_their_own_rows(tmp_path):
    # total_rows 0 divided by zero in the wizard, and hid the partitions.
    info = get_dataset_info(_write_splits(tmp_path, 0, train=3, test=1))

    assert info["predefined_splits"] == {"train": 0.75, "validation": 0.0, "test": 0.25}


def test_the_endpoint_says_iris_has_no_partitions_of_its_own(client, dataset_1):
    response = client.get(f"/api/v1/dataset/{dataset_1.id}/info")

    assert response.status_code == 200, response.text
    assert response.json()["predefined_splits"] is None
