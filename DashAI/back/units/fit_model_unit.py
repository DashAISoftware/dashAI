"""Unit that fits a model, optionally searching for its hyperparameters."""

import logging
from typing import TYPE_CHECKING

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

if TYPE_CHECKING:
    from DashAI.back.optimizers.base_optimizer import BaseOptimizer

log = logging.getLogger(__name__)


class FitModelSchema(BaseSchema):
    optimizer: schema_field(
        component_field(parent="BaseOptimizer"),
        placeholder={"component": "OptunaOptimizer", "params": {}},
        description=MultilingualString(
            en="Optimizer used to search for hyperparameters, along with its own "
            "configuration. Only used when the model declares optimizable "
            "parameters.",
            es="Optimizador usado para buscar hiperparámetros, junto con su propia "
            "configuración. Solo se usa cuando el modelo declara parámetros "
            "optimizables.",
            pt="Otimizador usado para procurar hiperparâmetros, junto com a sua "
            "própria configuração. Só é usado quando o modelo declara parâmetros "
            "otimizáveis.",
            de="Optimierer für die Hyperparametersuche samt seiner eigenen "
            "Konfiguration. Wird nur verwendet, wenn das Modell optimierbare "
            "Parameter deklariert.",
            zh="用于搜索超参数的优化器及其自身配置。仅当模型声明了可优化参数时使用。",
        ),
        alias=MultilingualString(
            en="Optimizer",
            es="Optimizador",
            pt="Otimizador",
            de="Optimierer",
            zh="优化器",
        ),
    )  # type: ignore
    goal_metric: schema_field(
        string_field(),
        placeholder="Accuracy",
        description=MultilingualString(
            en="Metric the hyperparameter search optimizes.",
            es="Métrica que optimiza la búsqueda de hiperparámetros.",
            pt="Métrica que a procura de hiperparâmetros otimiza.",
            de="Metrik, die die Hyperparametersuche optimiert.",
            zh="超参数搜索所优化的指标。",
        ),
        alias=MultilingualString(
            en="Goal metric",
            es="Métrica objetivo",
            pt="Métrica objetivo",
            de="Zielmetrik",
            zh="目标指标",
        ),
    )  # type: ignore


class FitModelUnit(BaseUnit):
    """Train a model, running a hyperparameter search when there is one to run.

    Hyperparameter optimization is a fitting strategy rather than a separate
    step: it returns a fitted model, and the trial plots are a by-product only
    that branch produces. Both paths therefore live in this unit.

    ``validate`` resolves the optimizer and the goal metric so an impossible
    configuration is rejected before the job reports that training started.

    The optimizer is configured as a component field, so its value is
    ``{"component": <name>, "params": {...}}`` and the front renders the
    chosen optimizer's own form underneath.
    """

    SCHEMA = FitModelSchema

    # run_id and artifact_prefix are configuration, not context: no unit
    # publishes them, so nothing upstream could ever satisfy them as REQUIRES.
    # See the artifact_prefix section of DAG_ENGINE.md.
    REQUIRES = (
        "model",
        "factory",
        "optimizable_parameters",
        "model_parameters",
        "x",
        "y",
        "task",
    )
    PROVIDES = ("model", "plot_paths")
    RUNTIME_PARAMS = ("run_id", "artifact_prefix")

    def __init__(self, **config) -> None:
        super().__init__(**config)
        self._optimizer = None
        self._goal_metric = None

    def _resolve_search(self):
        """Resolve the optimizer and the goal metric, memoized on this unit.

        Kept on the instance rather than in the context on purpose. These are
        this unit's own state, not something it hands to another unit: two
        ``FitModelUnit`` instances sharing a context — a DAG with two training
        nodes — would otherwise overwrite each other's optimizer, and the
        second one would silently run the first one's.
        """
        if self._optimizer is not None:
            return self._optimizer, self._goal_metric

        from kink import di

        component_registry = di["component_registry"]
        goal_metric_name: str = self.config["goal_metric"]
        optimizer_name: str = self.config["optimizer"]["component"]

        try:
            # The whole registry entry, not the class: the optimizer reads
            # metadata["maximize"] from it to pick a direction.
            goal_metric = component_registry[goal_metric_name]
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Metric is not compatible with the Task. {e}",
            ) from e

        try:
            optimizer_class = component_registry[optimizer_name]["class"]
            optimizer: "BaseOptimizer" = optimizer_class(
                **self.config["optimizer"]["params"]
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Error instantiating optimizer {optimizer_name}, {e}",
            ) from e

        self._goal_metric = goal_metric
        self._optimizer = optimizer
        return optimizer, goal_metric

    def validate(self, ctx: ExecutionContext) -> None:
        # ctx.require, not ctx.get: "optimizable_parameters" is one of this
        # unit's REQUIRES, so its absence means BuildModelUnit hasn't run yet
        # — a call-order mistake, not "there is nothing to optimize". Only an
        # empty value (the key present, genuinely no optimizable parameters)
        # skips the optimizer/goal-metric checks below, so no registry lookup
        # is needed either.
        if not ctx.require("optimizable_parameters"):
            return

        self._resolve_search()

    def execute(self, ctx: ExecutionContext) -> None:
        import os
        import pickle

        from kink import di

        config = di["config"]

        model = ctx.require("model")
        x = ctx.require("x")
        y = ctx.require("y")
        run_id = self.config["run_id"]
        optimizable_parameters = ctx.require("optimizable_parameters")

        plot_paths = []
        try:
            if not optimizable_parameters:
                model.train(x["train"], y["train"], x["validation"], y["validation"])
            else:
                # Memoized: validate() resolved these already, and resolving
                # again here would be the same lookup.
                optimizer, goal_metric = self._resolve_search()
                factory = ctx.require("factory")

                optimizer.optimize(
                    model,
                    x,
                    y,
                    optimizable_parameters,
                    goal_metric,
                    ctx.require("task"),
                )
                model = optimizer.get_model()
                best_params = optimizer.get_best_params()

                self._assert_model_keeps_its_runtime_state(model)

                # ctx.require already hands back an isolated copy of the
                # stored parameter tree, so update_parameters is free to
                # mutate it without touching the Run row it came from.
                old_parameters = ctx.require("model_parameters")
                ctx.put_ref(
                    "best_parameters",
                    factory.update_parameters(old_parameters, best_params),
                )

                # Generate hyperparameter plot
                from DashAI.back.core.artifacts import normalize_artifacts

                trials = optimizer.get_trials_values()
                plot_filenames, plots = optimizer.create_plots(
                    trials,
                    run_id,
                    n_params=len(optimizable_parameters),
                    goal_metric=goal_metric,
                    artifact_prefix=self.config["artifact_prefix"],
                )
                normalized_plots = normalize_artifacts(plots)
                for filename, plot in zip(
                    plot_filenames, normalized_plots, strict=False
                ):
                    plot_path = os.path.join(config["RUNS_PATH"], filename)
                    with open(plot_path, "wb") as file:
                        pickle.dump(plot, file)
                        plot_paths.append(plot_path)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Model training failed {e}",
            ) from e

        ctx.put("model", model)
        ctx.put_ref("plot_paths", plot_paths)

    @staticmethod
    def _assert_model_keeps_its_runtime_state(model) -> None:
        """Fail loudly if the optimizer returned a model that cannot be scored.

        ``ModelFactory`` attaches the data splits and the metric classes to the
        model instance, and optimizers are expected to return that same
        instance. If one ever returns a fresh object instead, scoring it finds
        nothing to score and the caller ends up with no metrics rather than an
        error.

        The check is on the data, not on the run id. Keying it to ``run_id``
        made it a no-op for every caller that has no run -- a pipeline, where
        ``run_id`` is always None -- which is exactly the caller with no other
        signal that anything went wrong: it would finish with an empty metrics
        artifact. What both callers need is the same, so this asks for that
        instead.
        """
        if getattr(model, "x_data", None) is None:
            raise JobError(
                "The optimizer returned a model detached from its data: metrics "
                "could not be computed for it. Optimizers must return the same "
                "model instance they received."
            )
