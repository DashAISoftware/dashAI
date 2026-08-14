"""Tests for pruner resolution in OptunaOptimizer.

Regression coverage for the pruner being passed to ``optuna.create_study`` as a
raw schema string instead of a pruner instance. ``create_study`` does not
validate the argument, so the study was built with ``pruner`` set to a ``str``
and any pruning call raised ``AttributeError: 'str' object has no attribute
'prune'``.
"""

import optuna
import pytest

from DashAI.back.optimizers.optuna_optimizer import _build_pruner


@pytest.mark.parametrize(
    "name",
    ["MedianPruner", "HyperbandPruner", "SuccessiveHalvingPruner", "WilcoxonPruner"],
)
def test_build_pruner_returns_an_instance(name: str) -> None:
    pruner = _build_pruner(name)

    assert isinstance(pruner, optuna.pruners.BasePruner)
    assert type(pruner).__name__ == name


@pytest.mark.parametrize("disabled", [None, "", "None"])
def test_disabled_pruning_maps_to_nop_pruner(disabled: "str | None") -> None:
    """The schema sends the string "None" when the user disables pruning."""
    assert isinstance(_build_pruner(disabled), optuna.pruners.NopPruner)


def test_pruner_needing_configuration_fails_with_a_clear_message() -> None:
    """PatientPruner wraps another pruner, so it cannot be built from its name."""
    with pytest.raises(ValueError, match="requires configuration"):
        _build_pruner("PatientPruner")


def test_unknown_pruner_lists_the_valid_options() -> None:
    with pytest.raises(ValueError, match="Unknown pruner 'NotAPruner'") as excinfo:
        _build_pruner("NotAPruner")

    assert "MedianPruner" in str(excinfo.value)


def test_study_built_with_the_resolved_pruner_can_prune() -> None:
    """End to end: the failure mode this fixes was only visible when pruning."""
    study = optuna.create_study(
        direction="maximize", pruner=_build_pruner("MedianPruner")
    )
    trial = study.ask()
    trial.report(0.1, step=0)

    # With the raw string this raised AttributeError instead of returning a bool.
    assert trial.should_prune() in (True, False)
