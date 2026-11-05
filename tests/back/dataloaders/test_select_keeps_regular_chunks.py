"""Selecting scattered rows leaves a table in regular Arrow chunks.

Rows that are not one contiguous range used to come out of
``DashAIDataset.select`` as one record batch per row. Every row-dropping
converter goes through it, and the layout outlived the selection: a dataset the
NaN remover cleaned kept a chunk per row once saved, and pickling the splits of
a 35k-row one took 40 s and almost 5 GB of memory.
"""

import numpy as np
import pandas as pd

from DashAI.back.converters.simple_converters.nan_remover import NanRemover
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    load_dataset,
    save_dataset,
    to_dashai_dataset,
)

ROWS = 2000
# Far below one chunk per row, which is what scattered rows used to get.
FEW_CHUNKS = 10


def _dataset(with_gaps=False):
    x = np.arange(ROWS, dtype="float64")
    if with_gaps:
        x[::3] = np.nan
    return to_dashai_dataset(
        pd.DataFrame({"x": x, "label": [f"c{i % 3}" for i in range(ROWS)]})
    )


def _chunks(dataset):
    return [column.num_chunks for column in dataset.arrow_table.columns]


def test_scattered_rows_come_back_in_a_few_chunks():
    keep = list(range(0, ROWS, 2))

    selected = _dataset().select(keep)

    assert isinstance(selected, DashAIDataset)
    assert max(_chunks(selected)) < FEW_CHUNKS


def test_scattered_rows_keep_the_requested_order():
    keep = [1500, 3, 999, 0, 42]

    selected = _dataset().select(keep)

    assert selected.arrow_table.column("x").to_pylist() == [float(i) for i in keep]
    assert selected.arrow_table.column("label").to_pylist() == [
        f"c{i % 3}" for i in keep
    ]


def test_scattered_rows_keep_the_dataset_types():
    dataset = _dataset()

    selected = dataset.select([5, 1, 7])

    assert {name: t.to_string() for name, t in selected.types.items()} == {
        name: t.to_string() for name, t in dataset.types.items()
    }


def test_an_empty_selection_is_still_a_dataset():
    selected = _dataset().select([])

    assert isinstance(selected, DashAIDataset)
    assert selected.num_rows == 0
    assert selected.column_names == ["x", "label"]


def test_the_nan_remover_output_is_not_fragmented(tmp_path):
    dataset = _dataset(with_gaps=True)
    remover = NanRemover().fit(dataset)

    cleaned = remover.transform(dataset)
    save_dataset(cleaned, tmp_path / "cleaned")
    reloaded = load_dataset(str(tmp_path / "cleaned"))

    assert cleaned.num_rows == ROWS - len(range(0, ROWS, 3))
    assert not any(np.isnan(cleaned.arrow_table.column("x").to_numpy()))
    assert max(_chunks(cleaned)) < FEW_CHUNKS
    assert max(_chunks(reloaded)) < FEW_CHUNKS
