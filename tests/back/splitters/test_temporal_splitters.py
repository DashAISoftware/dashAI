"""The temporal splitters cut a series into backtest origins, in steps.

A model is fitted on the steps before an origin and scored on the ``horizon``
steps after it. The test is the last origin, at ``n - horizon``; the
validation origins sit before it, one horizon apart. A holdout is the same
backtest with one validation origin.
"""

import pytest

from DashAI.back.splitters.origin_splitter import OriginSplitter
from DashAI.back.splitters.rolling_origin import RollingOriginSplitter
from DashAI.back.splitters.temporal_holdout import TemporalHoldoutSplitter

SPLITTERS = [TemporalHoldoutSplitter, RollingOriginSplitter]


def test_the_holdout_has_one_validation_origin_before_the_test():
    cuts = TemporalHoldoutSplitter({"horizon": 6}).cuts(48)

    assert cuts == {
        "horizon": 6,
        "validation_origins": [36],
        "test_origin": 42,
        "n_steps": 48,
    }


def test_the_rolling_origin_steps_back_one_horizon_per_origin():
    cuts = RollingOriginSplitter({"horizon": 6, "n_origins": 3}).cuts(48)

    assert cuts["validation_origins"] == [24, 30, 36]
    assert cuts["test_origin"] == 42


def test_the_holdout_ignores_a_number_of_origins():
    # It is the one-origin backtest whatever a payload says.
    cuts = TemporalHoldoutSplitter({"horizon": 3, "n_origins": 5}).cuts(20)

    assert cuts["validation_origins"] == [14]


@pytest.mark.parametrize("splitter", SPLITTERS)
def test_every_window_is_one_horizon_and_they_tile_the_end(splitter):
    cuts = splitter({"horizon": 4, "n_origins": 3}).cuts(40)
    origins = [*cuts["validation_origins"], cuts["test_origin"]]

    # Each window starts where the previous one ended, and the last one ends
    # with the series: validation and test measure the same horizon.
    assert all(b - a == 4 for a, b in zip(origins, origins[1:], strict=False))
    assert cuts["test_origin"] + 4 == 40


@pytest.mark.parametrize("splitter", SPLITTERS)
def test_the_shortest_series_leaves_one_step_to_fit_on(splitter):
    data = {"horizon": 3, "n_origins": 2}
    n_origins = 1 if splitter is TemporalHoldoutSplitter else 2
    shortest = (n_origins + 1) * 3 + 1

    cuts = splitter(data).cuts(shortest)

    assert cuts["validation_origins"][0] == 1


@pytest.mark.parametrize(
    ("splitter", "needed"),
    [(TemporalHoldoutSplitter, 7), (RollingOriginSplitter, 10)],
)
def test_a_series_too_short_is_refused_naming_what_to_change(splitter, needed):
    expected = f"at least {needed} steps.*Shorten the horizon"
    with pytest.raises(ValueError, match=expected):
        splitter({"horizon": 3, "n_origins": 2}).cuts(needed - 1)


@pytest.mark.parametrize("splitter", SPLITTERS)
def test_the_size_check_the_api_runs_is_the_cut(splitter):
    with pytest.raises(ValueError, match="needs a series of at least"):
        splitter({"horizon": 5}).validate_size(5)


@pytest.mark.parametrize("splitter", SPLITTERS)
def test_a_backtest_cuts_steps_and_never_rows(splitter):
    instance = splitter({"horizon": 2})

    with pytest.raises(NotImplementedError, match="call cuts"):
        instance.split(None, None)
    with pytest.raises(NotImplementedError, match="call cuts"):
        instance.split_indexes(None, None)


@pytest.mark.parametrize("splitter", SPLITTERS)
def test_a_backtest_offers_no_rows_to_explain(splitter):
    cuts = splitter({"horizon": 6}).cuts(48)

    assert splitter.explainable_partitions(cuts) == {}
    assert splitter.explainable_splits(cuts) == []


@pytest.mark.parametrize("splitter", SPLITTERS)
def test_a_backtest_never_shuffles(splitter):
    assert splitter({"horizon": 2, "shuffle": True}).shuffle is False


def test_the_two_splitters_share_the_origin_splitter():
    for splitter in SPLITTERS:
        assert issubclass(splitter, OriginSplitter)
    assert "Base" not in OriginSplitter.__name__


def test_the_schemas_take_steps_not_proportions():
    holdout = TemporalHoldoutSplitter.SCHEMA.model_json_schema()["properties"]
    rolling = RollingOriginSplitter.SCHEMA.model_json_schema()["properties"]

    assert set(holdout) == {"horizon"}
    assert set(rolling) == {"horizon", "n_origins"}
