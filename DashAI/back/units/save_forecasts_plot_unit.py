"""Unit that saves the figures of a backtest's Forecasts view."""

import logging

from DashAI.back.core.schema_fields import BaseSchema
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext
from DashAI.back.units.save_model_unit import _SAFE_PREFIX

log = logging.getLogger(__name__)


class SaveForecastsPlotSchema(BaseSchema):
    """Nothing to configure: where it writes is named after the run."""


class SaveForecastsPlotUnit(BaseUnit):
    """Draw the forecasts of every origin and write the figures beside the model.

    ``RUNS_PATH/forecasts_plots_<artifact_prefix>.pickle``, the artifacts
    ``forecasts_artifacts`` builds from the forecasts ``BacktestForecasterUnit``
    publishes. The run's ``forecasts`` plot row points at it; the figures are
    drawn from the forecasts, never from the model.

    ``artifact_prefix`` is a runtime parameter, as in ``SaveModelUnit``: no
    unit publishes it.
    """

    SCHEMA = SaveForecastsPlotSchema

    REQUIRES = ("forecasts",)
    PROVIDES = ("forecasts_plot_path",)
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
        from kink import di

        from DashAI.back.core.run_plots import run_plot_file, write_run_plot_file
        from DashAI.back.evaluation.forecasts_plot import forecasts_artifacts

        forecasts = ctx.require("forecasts")
        path = run_plot_file(
            di["config"]["RUNS_PATH"], "forecasts", self.config["artifact_prefix"]
        )
        try:
            write_run_plot_file(path, forecasts_artifacts(forecasts))
        except OSError as e:
            log.exception(e)
            raise JobError(f"Saving the forecasts plot failed: {e}") from e

        ctx.put_ref("forecasts_plot_path", str(path))
