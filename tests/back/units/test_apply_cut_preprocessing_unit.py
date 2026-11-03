"""Contract tests of ``ApplyCutPreprocessingUnit``, with the context by hand.

The unit hands each cut of a backtest the exogenous variables as that cut's
own preprocessor made them: ``origin_{i}.pkl`` for validation origin ``i``,
``test.pkl`` for the test and ``final.pkl`` for the final fit, each fitted by
``PreprocessingJob`` on the steps before its cut (RECONCILING_FORECASTING
§7.3). These feed it what its ``REQUIRES`` says and check what it publishes
(ATOMIZING §6).
"""

import os
import pickle

import numpy as np
import pandas as pd
import pytest

from DashAI.back.converters.scikit_learn.standard_scaler import StandardScaler
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.job.base_job import JobError
from DashAI.back.preprocessing.column_ref import (
    ConverterSequence,
    ConverterStep,
)
from DashAI.back.preprocessing.session_preprocessor import SessionPreprocessor
from DashAI.back.tasks.time_grid import TimeGrid
from DashAI.back.units.apply_cut_preprocessing_unit import (
    ApplyCutPreprocessingUnit,
    cut_lengths,
)
from DashAI.back.units.context import ExecutionContext

N_STEPS = 24
CUTS = {"horizon": 3, "validation_origins": [15, 18], "test_origin": 21, "n_steps": 24}
GRID = TimeGrid(
    freq="MS",
    first=pd.Timestamp("2020-01-01"),
    last=pd.Timestamp("2021-12-01"),
    n_steps=N_STEPS,
)
PROMO = [{"kind": "raw", "name": "promo"}]
REGISTRY = {"StandardScaler": {"class": StandardScaler}}
#: The file of each cut, and the steps it is fitted on.
FITS = {"origin_0": 15, "origin_1": 18, "test": 21, "final": 24}


def _promo():
    return np.array([float((i * 7) % 5) for i in range(N_STEPS)])


def _dataset(promo=None):
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=N_STEPS, freq="MS").strftime(
                "%Y-%m-%d"
            ),
            "sales": np.arange(N_STEPS, dtype=float),
            "promo": _promo() if promo is None else promo,
        }
    )
    return transform_dataset_with_schema(
        to_dashai_dataset(frame),
        {
            "date": {"type": "Date", "dtype": "%Y-%m-%d"},
            "sales": {"type": "Float", "dtype": "float64"},
            "promo": {"type": "Float", "dtype": "float64"},
        },
    )


def _context(dataset=None):
    ctx = ExecutionContext()
    ctx.put("dataset", _dataset() if dataset is None else dataset)
    ctx.put_ref("split_indexes", CUTS)
    ctx.put_ref("grid", GRID.to_ref())
    return ctx


def _fit_artifacts(directory, dataset):
    """Scale ``promo`` once per cut, on the steps before it, as the job does."""
    sequence = ConverterSequence(
        steps=[ConverterStep(converter="StandardScaler", params={}, scope=PROMO)]
    )
    for name, steps in FITS.items():
        preprocessor = SessionPreprocessor(sequence, REGISTRY, target_columns=["sales"])
        preprocessor.fit_transform({"train": dataset.select(range(steps))})
        with open(os.path.join(directory, f"{name}.pkl"), "wb") as f:
            pickle.dump(preprocessor, f)
    return str(directory)


def _cuts(published):
    return [*published["validation"], published["test"], published["final"]]


def test_without_artifacts_every_cut_reads_the_raw_columns():
    ctx = _context()

    ApplyCutPreprocessingUnit(exogenous_column_refs=PROMO)(ctx)

    for cut in _cuts(ctx.require("exogenous")):
        assert cut["columns"] == ["promo"]
        np.testing.assert_array_equal(cut["values"], _promo().reshape(-1, 1))


def test_without_the_role_every_cut_reads_no_column():
    ctx = _context()

    ApplyCutPreprocessingUnit(exogenous_column_refs=None)(ctx)

    published = ctx.require("exogenous")
    assert len(published["validation"]) == 2
    for cut in _cuts(published):
        assert cut["columns"] == []
        assert cut["values"].shape == (N_STEPS, 0)


def test_each_cut_reads_what_its_own_preprocessor_made(tmp_path):
    dataset = _dataset()
    ctx = _context(dataset)

    ApplyCutPreprocessingUnit(
        exogenous_column_refs=PROMO,
        preprocessing_artifacts_path=_fit_artifacts(tmp_path, dataset),
    )(ctx)

    promo = _promo()
    for cut, steps in zip(_cuts(ctx.require("exogenous")), FITS.values(), strict=True):
        fitted = promo[:steps]
        expected = (promo - fitted.mean()) / fitted.std()
        np.testing.assert_allclose(cut["values"][:, 0], expected, rtol=1e-12)


def test_a_missing_artifact_is_named(tmp_path):
    dataset = _dataset()
    directory = _fit_artifacts(tmp_path, dataset)
    os.remove(os.path.join(directory, "origin_1.pkl"))
    unit = ApplyCutPreprocessingUnit(
        exogenous_column_refs=PROMO, preprocessing_artifacts_path=directory
    )

    with pytest.raises(JobError, match="origin_1"):
        unit(_context(dataset))


def test_a_group_ref_without_artifacts_is_a_wiring_error():
    unit = ApplyCutPreprocessingUnit(
        exogenous_column_refs=[{"kind": "group", "step": 0}]
    )

    with pytest.raises(JobError, match="preprocessing_artifacts_path"):
        unit(_context())


def test_a_gap_in_the_steps_a_cut_reads_names_the_column_and_the_date():
    promo = _promo()
    promo[10] = np.nan

    with pytest.raises(JobError, match=r"'promo' has no value on 2020-11-01\."):
        ApplyCutPreprocessingUnit(exogenous_column_refs=PROMO)(
            _context(_dataset(promo))
        )


def test_each_cut_reads_the_steps_up_to_its_horizon():
    # A validation origin reads up to the end of its window; the test and the
    # final fit read the whole series.
    assert cut_lengths(CUTS) == [18, 21, 24, 24]


class _DroppingPreprocessor:
    """A preprocessor that drops a row, which no step of a backtest may do."""

    resolved_columns = {}
    resolved_slots = {}

    def transform_dataset(self, dataset, unseen=None):
        return dataset.select(range(dataset.num_rows - 1))


def test_a_preprocessor_that_changes_the_rows_is_a_contract_error(tmp_path):
    for name in FITS:
        with open(tmp_path / f"{name}.pkl", "wb") as f:
            pickle.dump(_DroppingPreprocessor(), f)
    unit = ApplyCutPreprocessingUnit(
        exogenous_column_refs=PROMO, preprocessing_artifacts_path=str(tmp_path)
    )

    with pytest.raises(JobError, match="24 rows"):
        unit(_context())


def test_the_dataset_is_left_as_it_was(tmp_path):
    dataset = _dataset()
    before = dataset.to_pandas()
    ctx = _context(dataset)

    ApplyCutPreprocessingUnit(
        exogenous_column_refs=PROMO,
        preprocessing_artifacts_path=_fit_artifacts(tmp_path, dataset),
    )(ctx)

    assert ctx.require("dataset") is dataset
    pd.testing.assert_frame_equal(dataset.to_pandas(), before)
