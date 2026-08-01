"""Unit that persists a trained model to disk."""

import logging

from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

log = logging.getLogger(__name__)


class SaveModelUnit(BaseUnit):
    """Write a trained model under the runs directory, keyed by its run id.

    Takes no configuration: the destination is derived from the run the model
    belongs to, so a re-run overwrites its own artifact and never another's.
    """

    REQUIRES = ("model", "run_id")
    PROVIDES = ("model_path",)

    def execute(self, ctx: ExecutionContext) -> None:
        import os

        from kink import di

        config = di["config"]

        model = ctx.require("model")
        run_id = ctx.require("run_id")

        try:
            model_path = os.path.join(config["RUNS_PATH"], str(run_id))
            model.save(model_path)
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Model saving failed",
            ) from e

        ctx.put_ref("model_path", model_path)
