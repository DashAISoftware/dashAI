"""Unit that computes and stores the final metrics of a trained model."""

import logging

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    list_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import Metric
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

log = logging.getLogger(__name__)

DEFAULT_SPLITS = ["TRAIN", "VALIDATION", "TEST"]


class EvaluateModelSchema(BaseSchema):
    splits: schema_field(
        list_field(enum_field(enum=DEFAULT_SPLITS)),
        placeholder=DEFAULT_SPLITS,
        description=MultilingualString(
            en="Data splits the model is evaluated on.",
            es="Particiones de datos sobre las que se evalúa el modelo.",
            pt="Partições de dados sobre as quais o modelo é avaliado.",
            de="Datenteilmengen, auf denen das Modell ausgewertet wird.",
            zh="用于评估模型的数据划分。",
        ),
        alias=MultilingualString(
            en="Splits",
            es="Particiones",
            pt="Partições",
            de="Teilmengen",
            zh="数据划分",
        ),
    )  # type: ignore


class EvaluateModelUnit(BaseUnit):
    """Compute the final metrics of a trained model, once per split.

    The unit is idempotent: a split whose final metrics were already logged
    (for instance by a model that evaluates itself while training) is skipped.

    Which metrics are computed is decided by the model, not by this unit:
    ``ModelFactory`` attaches the metric classes to the model instance, and
    ``BaseModel.calculate_metrics`` is ``final``. That method persists the
    rows through a session of its own, so these writes are not part of the
    transaction the calling job controls.
    """

    SCHEMA = EvaluateModelSchema

    REQUIRES = ("model", "run_id")

    def execute(self, ctx: ExecutionContext) -> None:
        from kink import di

        session_factory = di["session_factory"]

        model = ctx.require("model")
        # ctx.require, not ctx.get: run_id is what the idempotency query below
        # filters on. A silently-None run_id would match no existing metric
        # row regardless of what was actually logged, and — if the model
        # were also somehow detached from its run — calculate_metrics would
        # then no-op (base_model.py's ``if not metrics or not self.run_id``),
        # so the unit would "succeed" having written nothing.
        run_id = ctx.require("run_id")
        splits = [SplitEnum[name] for name in self.config.get("splits", DEFAULT_SPLITS)]

        try:
            for split in splits:
                with session_factory() as db:
                    already_logged = (
                        db.query(Metric)
                        .filter_by(run_id=run_id, split=split, level=LevelEnum.LAST)
                        .first()
                    )
                if already_logged:
                    continue

                model.calculate_metrics(split=split, level=LevelEnum.LAST)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Metric calculation failed {e}",
            ) from e
