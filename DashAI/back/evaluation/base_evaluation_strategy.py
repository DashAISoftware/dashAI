from typing import Final

from DashAI.back.dependencies.database.models import Run
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.optimizers.base_optimizer import BaseOptimizer


class BaseEvaluationStrategy:
    TYPE: Final[str] = "EvaluationStrategy"

    def __init__(
        self,
        model: BaseModel,
        optimizer: BaseOptimizer,
        run_optimizable_parameters,
        goal_metric,
        **kwargs,
    ):
        self.model: BaseModel = model
        self.optimizer: BaseOptimizer = optimizer
        self.run_optimizable_parameters = run_optimizable_parameters
        self.goal_metric = goal_metric

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        raise NotImplementedError("Subclasses must implement this method")

    def evaluate(self, model: BaseModel, x, y, metric_name):
        raise NotImplementedError("Subclasses must implement this method")

    def _do_hpo(self, x, y, factory: ModelFactory, run: Run, db):
        from sqlalchemy.orm.attributes import flag_modified

        self.model, best_params = self.optimizer.optimize(
            self.model,
            x,
            y,
            self.run_optimizable_parameters,
            self.goal_metric,
            strategy=self.evaluate,
        )

        old_parameters = run.parameters.copy()
        updated_parameters = factory.update_parameters(old_parameters, best_params)

        run.parameters = updated_parameters
        flag_modified(run, "parameters")
        db.commit()
