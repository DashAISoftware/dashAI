"""The metrics forecasting offers, and how regression shares its own.

Each metric is one class under one registry name. MAE and RMSE are regression
metrics that the single-series task lists; MAPE, SMAPE, MASE and interval
coverage are forecasting metrics, offered to forecasting alone for now
(RECONCILING_FORECASTING §2.13). A forecast is scored through
``score_forecast``, which a point metric answers with its own ``score``.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.metrics.forecasting.interval_coverage import IntervalCoverage
from DashAI.back.metrics.forecasting.mape import MAPE
from DashAI.back.metrics.forecasting.mase import MASE
from DashAI.back.metrics.forecasting.smape import SMAPE
from DashAI.back.metrics.forecasting_metric import ForecastingMetric, ScoredForecast
from DashAI.back.metrics.regression.mae import MAE
from DashAI.back.metrics.regression.rmse import RMSE
from DashAI.back.metrics.regression_metric import RegressionMetric
from DashAI.back.metrics.undefined_metric import UndefinedMetricError


def _true(values):
    return to_dashai_dataset(pd.DataFrame({"target": values}))


def _forecast(actual, point, history=(1.0, 2.0, 3.0, 4.0), season_length=1, **bounds):
    return ScoredForecast(
        actual=np.asarray(actual, dtype=float),
        point=np.asarray(point, dtype=float),
        history=np.asarray(history, dtype=float),
        season_length=season_length,
        **bounds,
    )


# --- MAPE and SMAPE ----------------------------------------------------------


def test_mape_matches_a_hand_computed_value():
    # errors 10/100 and 20/200 -> 10% and 10% -> 10%
    score = MAPE.score(_true([100.0, 200.0]), np.array([110.0, 180.0]))

    assert score == pytest.approx(10.0)


def test_mape_is_zero_for_a_perfect_forecast():
    assert MAPE.score(_true([1.0, 2.0]), np.array([1.0, 2.0])) == pytest.approx(0.0)


def test_mape_is_undefined_when_any_actual_is_zero():
    # Leaving the zero row out would report the error of a different series,
    # which is what MAPE used to do.
    with pytest.raises(UndefinedMetricError, match="1 of them are zero") as raised:
        MAPE.score(_true([0.0, 100.0]), np.array([5.0, 110.0]))

    assert "SMAPE or MASE" in raised.value.reason


def test_an_undefined_metric_is_not_an_error_optuna_swallows():
    # Optuna catches ValueError and ArithmeticError as unfittable trials.
    assert not issubclass(UndefinedMetricError, (ValueError, ArithmeticError))


def test_smape_matches_a_hand_computed_value():
    # |100-110| = 10, denominator (100+110)/2 = 105 -> 2*10/210 = 9.5238%
    score = SMAPE.score(_true([100.0]), np.array([110.0]))

    assert score == pytest.approx(200 * 10 / 210)


def test_smape_is_zero_for_a_perfect_forecast():
    assert SMAPE.score(_true([1.0, 2.0]), np.array([1.0, 2.0])) == pytest.approx(0.0)


def test_smape_survives_a_zero_actual():
    # The case that breaks MAPE. Predicting 5 when the truth is 0 is the
    # worst possible relative error, which sMAPE caps at 200 percent.
    score = SMAPE.score(_true([0.0]), np.array([5.0]))

    assert score == pytest.approx(200.0)


def test_smape_treats_a_matching_pair_of_zeros_as_no_error():
    score = SMAPE.score(_true([0.0, 100.0]), np.array([0.0, 100.0]))

    assert score == pytest.approx(0.0)


def test_both_metrics_are_minimised():
    assert MAPE.MAXIMIZE is False
    assert SMAPE.MAXIMIZE is False


def test_coverage_cannot_be_optimized():
    # Higher coverage means more actuals inside the interval, which is the
    # axis MAXIMIZE describes; better is near 0.95, which no direction is. So
    # it says it cannot be optimized, and nothing picks a best run by it.
    assert IntervalCoverage.MAXIMIZE is True
    assert IntervalCoverage.get_metadata()["optimizable"] is False


@pytest.mark.parametrize("metric", [MAE, RMSE, MAPE, SMAPE, MASE])
def test_an_error_metric_can_be_optimized(metric):
    assert metric.get_metadata()["optimizable"] is True


# --- who offers what ---------------------------------------------------------


def test_the_percentage_metrics_are_offered_to_forecasting_alone_for_now():
    for metric in (MAPE, SMAPE):
        assert issubclass(metric, ForecastingMetric)
        assert not issubclass(metric, RegressionMetric)
    assert ForecastingMetric.COMPATIBLE_COMPONENTS == ["SingleSeriesForecastingTask"]


def test_regression_metrics_name_only_regression():
    # A forecasting task lists the regression metrics it shares in its own
    # COMPATIBLE_COMPONENTS: the metric never names it.
    assert RegressionMetric.COMPATIBLE_COMPONENTS == ["RegressionTask"]


def test_the_single_series_task_lists_the_shared_point_metrics():
    from DashAI.back.tasks.single_series_forecasting_task import (
        SingleSeriesForecastingTask,
    )

    assert SingleSeriesForecastingTask.COMPATIBLE_COMPONENTS == ["MAE", "RMSE"]


# --- scoring a forecast ------------------------------------------------------


@pytest.mark.parametrize("metric", [MAE, RMSE, MAPE, SMAPE])
def test_a_point_metric_scores_a_forecast_with_its_own_score(metric):
    actual, point = [100.0, 200.0, 150.0], [110.0, 180.0, 150.0]

    assert metric.score_forecast(_forecast(actual, point)) == metric.score(
        _true(actual), np.asarray(point)
    )


def test_mase_scales_the_error_by_the_seasonal_naive_error_of_the_history():
    # History changes by 2, 2, 4 across one step: scale = 8 / 3.
    forecast = _forecast([10.0, 12.0], [11.0, 14.0], history=[1.0, 3.0, 5.0, 9.0])

    assert MASE.score_forecast(forecast) == pytest.approx((1.0 + 2.0) / 2 / (8 / 3))


def test_mase_counts_the_change_across_a_season():
    history = [1.0, 2.0, 5.0, 7.0]
    forecast = _forecast([10.0], [12.0], history=history, season_length=2)

    # Seasonal changes 5 - 1 and 7 - 2: scale = 4.5.
    assert MASE.score_forecast(forecast) == pytest.approx(2.0 / 4.5)


def test_mase_is_undefined_on_a_history_that_never_changes():
    with pytest.raises(UndefinedMetricError, match="does not change"):
        MASE.score_forecast(_forecast([1.0], [2.0], history=[5.0, 5.0, 5.0]))


def test_mase_is_undefined_on_a_history_no_longer_than_a_season():
    with pytest.raises(UndefinedMetricError, match="has none"):
        MASE.score_forecast(
            _forecast([1.0], [2.0], history=[1.0, 2.0], season_length=2)
        )


def test_coverage_is_the_share_of_actuals_inside_the_95_interval():
    forecast = _forecast(
        [1.0, 5.0, 9.0, 4.0],
        [2.0, 5.0, 8.0, 4.0],
        lower={95: np.array([0.0, 4.0, 9.5, 3.0])},
        upper={95: np.array([3.0, 6.0, 10.0, 5.0])},
    )

    assert IntervalCoverage.score_forecast(forecast) == pytest.approx(0.75)


def test_coverage_is_undefined_without_an_interval():
    with pytest.raises(UndefinedMetricError, match="no 95% prediction interval"):
        IntervalCoverage.score_forecast(_forecast([1.0], [1.0]))


def test_coverage_is_undefined_when_the_bounds_are_not_numbers():
    forecast = _forecast(
        [1.0],
        [1.0],
        lower={95: np.array([np.nan])},
        upper={95: np.array([np.nan])},
    )

    with pytest.raises(UndefinedMetricError, match="not numbers"):
        IntervalCoverage.score_forecast(forecast)


@pytest.mark.parametrize("metric", [MASE, IntervalCoverage])
def test_a_forecasting_metric_has_no_value_on_rows_alone(metric):
    # What a session that lists it for a task scored by rows records.
    with pytest.raises(UndefinedMetricError, match="no value on rows alone"):
        metric.score(_true([1.0]), np.array([1.0]))
