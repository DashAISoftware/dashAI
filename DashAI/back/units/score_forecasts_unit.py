"""Unit that scores the forecasts of a backtest and records the metrics."""

import logging
import math
from typing import Dict, List, Optional, Tuple

from DashAI.back.core.schema_fields import (
    BaseSchema,
    list_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import scored_forecast

log = logging.getLogger(__name__)


def _metrics_field(alias: MultilingualString, description: MultilingualString):
    return schema_field(
        list_field(string_field()),
        placeholder=[],
        description=description,
        alias=alias,
    )


class ScoreForecastsSchema(BaseSchema):
    validation_metrics: _metrics_field(
        alias=MultilingualString(
            en="Validation metrics",
            es="Métricas de validación",
            pt="Métricas de validação",
            de="Validierungsmetriken",
            zh="验证指标",
        ),
        description=MultilingualString(
            en="Metrics scored on every validation origin, and their mean.",
            es="Métricas evaluadas en cada origen de validación, y su promedio.",
            pt="Métricas avaliadas em cada origem de validação, e a sua média.",
            de="Auf jedem Validierungsursprung bewertete Metriken und ihr Mittel.",
            zh="在每个验证起点上评估的指标及其平均值。",
        ),
    )  # type: ignore
    test_metrics: _metrics_field(
        alias=MultilingualString(
            en="Test metrics",
            es="Métricas de prueba",
            pt="Métricas de teste",
            de="Testmetriken",
            zh="测试指标",
        ),
        description=MultilingualString(
            en="Metrics scored on the test origin.",
            es="Métricas evaluadas en el origen de prueba.",
            pt="Métricas avaliadas na origem de teste.",
            de="Auf dem Testursprung bewertete Metriken.",
            zh="在测试起点上评估的指标。",
        ),
    )  # type: ignore


class ScoreForecastsUnit(BaseUnit):
    """Score each origin's forecasts into the rows a run's metrics are.

    Publishes ``forecast_metrics``, a list of plain rows:

    - one ``FOLD`` row per validation origin and metric, with the origin's
      index, as the folds of a cross-validation have theirs;
    - one ``LAST`` validation row per metric, holding the mean over the origins
      and its standard deviation (0 for a single origin, as a holdout has);
    - one ``LAST`` test row per metric, for the test origin.

    A metric with no value on an origin (``UndefinedMetricError``, or a score
    that is not a number) has a ``None`` value and the reason, and then the
    summary has none either, with the first origin's reason: averaging the
    others would summarise a different set of origins.

    The rows are values, not database rows: a unit does not write domain rows
    (``test_unit_contracts``), so the job persists them. Unlike
    cross-validation, where the job also computes the summary, the summary is
    computed here with the scores it summarises, so it is addressable in a
    graph (FORECASTING U9).
    """

    SCHEMA = ScoreForecastsSchema

    REQUIRES = ("forecasts", "series")
    PROVIDES = ("forecast_metrics",)

    def _metric_classes(self, names: List[str]) -> list:
        from kink import di

        registry = di["component_registry"]
        try:
            return [registry[name]["class"] for name in names]
        except Exception as e:
            log.exception(e)
            raise JobError(f"Unable to find the metrics {names} in registry") from e

    @staticmethod
    def _score(metric, forecast, dates) -> Tuple[Optional[float], Optional[str]]:
        """A metric's value on a forecast, or None and the reason it has none.

        The reason names the dates of the values that leave the metric
        undefined, from the forecast's own window.
        """
        from DashAI.back.metrics.undefined_metric import (
            UndefinedMetricError,
            describe_undefined,
        )

        try:
            value = float(metric.score_forecast(forecast))
        except UndefinedMetricError as undefined:
            return None, describe_undefined(undefined, dates)
        if not math.isfinite(value):
            return None, f"{metric.__name__} returned {value}, which is not a number."
        return value, None

    def execute(self, ctx: ExecutionContext) -> None:
        import numpy as np

        forecasts = ctx.require("forecasts")
        series = np.asarray(ctx.require("series"), dtype=float)
        season_length = forecasts.get("season_length", 1)

        validation = [o for o in forecasts["origins"] if o["partition"] == "validation"]
        test = [o for o in forecasts["origins"] if o["partition"] == "test"]

        rows: List[Dict] = []

        def row(split, level, name, value, reason, fold=None, std=None):
            rows.append(
                {
                    "split": split,
                    "level": level,
                    "name": name,
                    "value": value,
                    "unavailable_reason": reason,
                    "std_value": std,
                    "fold_index": fold,
                }
            )

        for metric in self._metric_classes(self.config["validation_metrics"]):
            scores: Dict[int, Tuple[Optional[float], Optional[str]]] = {
                origin["index"]: self._score(
                    metric,
                    scored_forecast(origin, series, season_length),
                    origin["dates"],
                )
                for origin in validation
            }
            for index, (value, reason) in scores.items():
                row(
                    "VALIDATION",
                    "FOLD",
                    metric.__name__,
                    value,
                    reason,
                    fold=index,
                )
            reasons = [reason for _, reason in scores.values() if reason is not None]
            if reasons:
                row(
                    "VALIDATION",
                    "LAST",
                    metric.__name__,
                    None,
                    reasons[0],
                )
            elif scores:
                values = [value for value, _ in scores.values()]
                row(
                    "VALIDATION",
                    "LAST",
                    metric.__name__,
                    float(np.mean(values)),
                    None,
                    std=float(np.std(values)) if len(values) > 1 else 0.0,
                )

        for metric in self._metric_classes(self.config["test_metrics"]):
            for origin in test:
                value, reason = self._score(
                    metric,
                    scored_forecast(origin, series, season_length),
                    origin["dates"],
                )
                row("TEST", "LAST", metric.__name__, value, reason)

        ctx.put_ref("forecast_metrics", rows)
