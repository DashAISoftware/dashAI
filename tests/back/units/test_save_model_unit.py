"""Tests for SaveModelUnit's contract, independent of a real model or disk."""

import os

import pytest
from kink import di

from DashAI.back.job.base_job import JobError
from DashAI.back.units.context import ExecutionContext, UnitContractError
from DashAI.back.units.save_model_unit import SaveModelUnit


class _RecordingModel:
    """Stands in for a trained model, recording where it was asked to go."""

    def __init__(self) -> None:
        self.saved_to = None

    def save(self, path) -> None:
        self.saved_to = path


@pytest.fixture(name="runs_path")
def fixture_runs_path(tmp_path):
    di["config"] = {"RUNS_PATH": str(tmp_path)}
    yield str(tmp_path)
    del di["config"]


def test_the_model_lands_in_a_directory_named_by_the_prefix(runs_path):
    ctx = ExecutionContext()
    model = _RecordingModel()
    ctx.put("model", model)

    SaveModelUnit(artifact_prefix="pipeline-3-save")(ctx)

    assert model.saved_to == os.path.join(runs_path, "pipeline-3-save")
    assert ctx.require("model_path") == model.saved_to


def test_a_numeric_run_id_is_a_valid_prefix(runs_path):
    """The path a real run writes to has to keep working unchanged.

    ``ModelJob`` passes ``str(run.id)``, and
    ``test_model_job_orchestration.py`` asserts the directory is named exactly
    that. A guard that rejected it would break every training run.
    """
    ctx = ExecutionContext()
    model = _RecordingModel()
    ctx.put("model", model)

    SaveModelUnit(artifact_prefix="17")(ctx)

    assert model.saved_to == os.path.join(runs_path, "17")


@pytest.mark.parametrize(
    "prefix",
    ["../escape", "a/b", "a\b", "", "C:nope", ".", "with space"],
)
def test_a_prefix_that_could_be_read_as_a_path_is_refused(runs_path, prefix):
    """A prefix is a directory name, so it must not be able to leave RUNS_PATH.

    ``os.path.join`` with a separator or a parent reference in the prefix
    happily produces a destination outside the runs directory, and the model
    would be written there without any error.
    """
    ctx = ExecutionContext()
    model = _RecordingModel()
    ctx.put("model", model)

    with pytest.raises(JobError, match="artifact prefix"):
        SaveModelUnit(artifact_prefix=prefix)(ctx)

    assert model.saved_to is None


def test_validate_runs_before_anything_is_written(runs_path):
    """``__call__`` validates first, so a bad prefix never reaches ``save``."""
    unit = SaveModelUnit(artifact_prefix="../escape")
    ctx = ExecutionContext()
    ctx.put("model", _RecordingModel())

    with pytest.raises(JobError):
        unit.validate(ctx)


def test_the_unit_still_needs_a_model(runs_path):
    """``run_id`` left REQUIRES; ``model`` did not."""
    with pytest.raises(UnitContractError, match="'model'"):
        SaveModelUnit(artifact_prefix="1")(ExecutionContext())
