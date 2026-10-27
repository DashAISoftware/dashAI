"""Unit that saves a backtest's forecasts beside the run's model."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.forecast_scope import forecasts_file
from DashAI.back.units.save_model_unit import _SAFE_PREFIX

log = logging.getLogger(__name__)


class SaveForecastsSchema(BaseSchema):
    """Nothing to configure: where it writes is named after the run."""


class SaveForecastsUnit(BaseUnit):
    """Write the forecasts of every origin to a JSON file beside the model.

    ``RUNS_PATH/<artifact_prefix>_forecasts.json``, in the shape
    ``BacktestForecasterUnit`` publishes: the frequency, the horizon, the
    interval levels, and per origin its partition, its dates, what actually
    happened, the forecast and its bounds. ``GET /run/{id}/forecasts`` returns
    it as it is, and the forecasting reports draw from it, never from the
    model.

    Written aside and moved into place, so a save that dies halfway leaves no
    truncated file behind. ``artifact_prefix`` is a runtime parameter, as in
    ``SaveModelUnit``: no unit publishes it.
    """

    SCHEMA = SaveForecastsSchema

    REQUIRES = ("forecasts",)
    PROVIDES = ("forecasts_path",)
    RUNTIME_PARAMS = ("artifact_prefix",)

    def validate(self, ctx: ExecutionContext) -> None:
        prefix = self.config.get("artifact_prefix")
        if not isinstance(prefix, str) or not _SAFE_PREFIX.match(prefix):
            raise JobError(
                "The artifact prefix names a file under the runs directory, so "
                "it can only contain letters, digits, hyphens and underscores. "
                f"Got: {prefix!r}"
            )

    def execute(self, ctx: ExecutionContext) -> None:
        import json
        import os

        from kink import di

        forecasts = ctx.require("forecasts")
        path = forecasts_file(di["config"]["RUNS_PATH"], self.config["artifact_prefix"])
        partial = path.with_suffix(".json.partial")
        try:
            partial.write_text(json.dumps(forecasts), encoding="utf-8")
            os.replace(partial, path)
        except OSError as e:
            log.exception(e)
            raise JobError(f"Saving the forecasts failed: {e}") from e

        ctx.put_ref("forecasts_path", str(path))
