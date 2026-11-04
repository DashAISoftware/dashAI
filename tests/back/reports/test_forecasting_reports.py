"""Unit tests for the forecasting reports, drawn from a backtest's forecasts.

A forecasting report reads the forecasts file of a run, never the model
(D6): ``compute_forecasts(forecasts)``. Its row-based ``compute`` refuses.
"""

import json

import numpy as np
import pytest

from DashAI.back.core.artifacts import normalize_artifacts
from DashAI.back.reports.base_report import BaseReport, ReportError
from DashAI.back.reports.forecasting.forecast_error_by_step import (
    ForecastErrorByStep,
)
from DashAI.back.reports.forecasting.forecast_vs_actual import ForecastVsActual
from DashAI.back.reports.forecasting.forecasting_report import ForecastingReport
from DashAI.back.reports.forecasting.residual_autocorrelation import (
    ResidualAutocorrelation,
)
from DashAI.back.reports.forecasting.residuals_over_time import ResidualsOverTime

REPORTS = [
    ForecastVsActual,
    ForecastErrorByStep,
    ResidualsOverTime,
    ResidualAutocorrelation,
]


def _origin(partition, index, start, actual, forecast, spread=1.0):
    dates = [f"2024-{month:02d}-01T00:00:00" for month in range(start, start + 3)]
    return {
        "partition": partition,
        "index": index,
        "origin_step": start,
        "dates": dates,
        "actual": actual,
        "forecast": forecast,
        "lower": {"95": [value - spread for value in forecast]},
        "upper": {"95": [value + spread for value in forecast]},
    }


@pytest.fixture(name="forecasts")
def a_backtest_of_two_validation_origins_and_the_test():
    return {
        "version": 1,
        "freq": "MS",
        "horizon": 3,
        "levels": [95],
        "season_length": 1,
        "origins": [
            _origin("validation", 0, 1, [10.0, 12.0, 14.0], [11.0, 11.0, 11.0]),
            _origin("validation", 1, 4, [16.0, 18.0, 20.0], [15.0, 15.0, 15.0]),
            _origin("test", 0, 7, [22.0, 24.0, 26.0], [21.0, 21.0, 21.0]),
        ],
    }


def _figure(artifact):
    assert artifact.type == "plotly"
    return json.loads(artifact.payload)


def test_forecast_vs_actual_draws_the_actual_series_and_each_origin(forecasts):
    figure = _figure(ForecastVsActual().compute_forecasts(forecasts)[0])

    actual = figure["data"][0]
    assert actual["name"] == "Actual"
    assert actual["x"][0] == "2024-01-01T00:00:00"
    assert actual["y"] == [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0]
    names = [trace["name"] for trace in figure["data"]]
    assert "Validation 1: forecast" in names
    assert "Test: forecast" in names
    bands = [trace for trace in figure["data"] if trace.get("fill") == "toself"]
    assert len(bands) == 3


def test_the_residuals_are_actual_minus_forecast_against_the_date(forecasts):
    figure = _figure(ResidualsOverTime().compute_forecasts(forecasts)[0])

    test = next(trace for trace in figure["data"] if trace["name"] == "Test")
    assert test["x"] == [
        "2024-07-01T00:00:00",
        "2024-08-01T00:00:00",
        "2024-09-01T00:00:00",
    ]
    assert test["y"] == [1.0, 3.0, 5.0]


def test_the_error_by_step_averages_the_validation_origins(forecasts):
    figure = _figure(ForecastErrorByStep().compute_forecasts(forecasts)[0])

    validation, test = figure["data"]
    assert validation["x"] == [1, 2, 3]
    # Step 1 misses by 1 and 1, step 2 by 1 and 3, step 3 by 3 and 5.
    assert validation["y"] == pytest.approx([1.0, 2.0, 4.0])
    assert test["y"] == pytest.approx([1.0, 3.0, 5.0])


def test_the_autocorrelation_reads_every_residual_in_date_order(forecasts):
    figure = _figure(ResidualAutocorrelation(max_lag=3).compute_forecasts(forecasts)[0])

    residuals = np.array([-1.0, 1.0, 3.0, 1.0, 3.0, 5.0, 1.0, 3.0, 5.0])
    centered = residuals - residuals.mean()
    denom = centered @ centered
    expected = [(centered[k:] @ centered[:-k]) / denom for k in range(1, 4)]
    assert figure["data"][0]["y"] == pytest.approx(expected)


def test_a_step_with_no_value_is_left_out(forecasts):
    forecasts["origins"][2]["actual"][1] = None

    figure = _figure(ResidualsOverTime().compute_forecasts(forecasts)[0])

    test = next(trace for trace in figure["data"] if trace["name"] == "Test")
    assert test["y"] == [1.0, 5.0]


@pytest.mark.parametrize("report", REPORTS, ids=lambda r: r.__name__)
def test_every_report_output_normalizes(report, forecasts):
    for item in normalize_artifacts(report().compute_forecasts(forecasts)):
        assert item["type"] in {"plotly", "table", "text", "image", "grouped"}


@pytest.mark.parametrize("report", REPORTS, ids=lambda r: r.__name__)
def test_a_forecasting_report_draws_no_partition_of_rows(report):
    with pytest.raises(ReportError, match="draws the forecasts a backtest saved"):
        report().compute(np.ones(3), np.ones(3))


@pytest.mark.parametrize("report", REPORTS, ids=lambda r: r.__name__)
def test_every_report_is_a_forecasting_report_of_the_task(report):
    assert report.TYPE == "Report"
    assert issubclass(report, BaseReport)
    assert issubclass(report, ForecastingReport)
    assert report.COMPATIBLE_COMPONENTS == ["SingleSeriesForecastingTask"]
