"""Unit that persists a trained model to disk."""

import logging
import re

from DashAI.back.core.atomic import atomic_save_path
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

log = logging.getLogger(__name__)

#: A prefix names a directory directly under RUNS_PATH, so anything that could
#: be read as a path — a separator, a parent reference, a drive letter — has to
#: be refused rather than cleaned up: a caller that meant one destination and
#: silently got another is the failure this guards against.
_SAFE_PREFIX = re.compile(r"^[A-Za-z0-9_-]+$")


class SaveModelUnit(BaseUnit):
    """Write a trained model under the runs directory, in its own subdirectory.

    The destination is named by ``artifact_prefix``, which the caller chooses:
    a run passes its own id, so a re-run overwrites its own artifact and never
    another's. A caller that is not a run passes something unique to itself.

    The prefix is configuration rather than a context key on purpose: no unit
    publishes it, so nothing upstream could ever satisfy it as a requirement.
    It is the same split ``SaveDatasetUnit`` and ``SaveDatasetToPathUnit``
    already draw — a destination an upstream unit produced against one the
    caller names.
    """

    REQUIRES = ("model",)
    PROVIDES = ("model_path",)
    RUNTIME_PARAMS = ("artifact_prefix",)

    def validate(self, ctx: ExecutionContext) -> None:
        prefix = self.config["artifact_prefix"]

        if not isinstance(prefix, str) or not _SAFE_PREFIX.match(prefix):
            raise JobError(
                "The artifact prefix names a directory under the runs "
                "directory, so it can only contain letters, digits, hyphens "
                f"and underscores. Got: {prefix!r}"
            )

    def execute(self, ctx: ExecutionContext) -> None:
        import os

        from kink import di

        config = di["config"]

        model = ctx.require("model")

        # The fit units leave the model pointing at the partitions it was
        # fitted on, because the metric methods read ``x_data`` / ``y_data``
        # off the instance. A model whose ``save`` pickles ``self`` would then
        # write the whole dataset into the artifact: a 2 KB decision tree came
        # out as an 80 MB file that took 40 s to dump. Nothing reads these
        # attributes back off a loaded model, so they are detached for the
        # write only and put back right after -- the live object may still be
        # scored by whatever runs next.
        detached = {
            name: vars(model)[name]
            for name in ("x_data", "y_data")
            if name in vars(model)
        }
        for name in detached:
            setattr(model, name, None)

        try:
            model_path = os.path.join(
                config["RUNS_PATH"], self.config["artifact_prefix"]
            )
            # Written aside and moved into place, so a save that dies halfway
            # leaves the previous artifact intact instead of a truncated one
            # that the row still points at. The temporary path is handed to the
            # model rather than derived here because only the model knows
            # whether it writes a file or a directory of weights.
            with atomic_save_path(model_path) as tmp_path:
                model.save(str(tmp_path))
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Model saving failed",
            ) from e
        finally:
            for name, value in detached.items():
                setattr(model, name, value)

        ctx.put_ref("model_path", model_path)
