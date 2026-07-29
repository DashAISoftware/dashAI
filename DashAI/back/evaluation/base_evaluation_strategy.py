import os
import pickle
from abc import ABCMeta, abstractmethod
from typing import Final, List

from kink import di

from DashAI.back.core.artifacts import normalize_artifacts
from DashAI.back.dependencies.database.models import Run
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.optimizers.base_optimizer import BaseOptimizer


class BaseEvaluationStrategy(metaclass=ABCMeta):
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

    @abstractmethod
    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
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

    def _generate_hpo_plots(self, run: Run) -> List[str]:
        """Generate and pickle the hyperparameter optimization plots to disk.

        Shared by every evaluation strategy that runs HPO, so the plot
        generation logic only needs to be maintained in one place.

        Parameters
        ----------
        run : Run
            The run the plots belong to (used for the plot filenames).

        Returns
        -------
        list[str]
            Paths to the pickled plot files, in the order produced by the
            optimizer.
        """
        config = di["config"]
        plot_paths: List[str] = []

        trials = self.optimizer.get_trials_values()
        plot_filenames, plots = self.optimizer.create_plots(
            trials,
            run.id,
            n_params=len(self.run_optimizable_parameters),
            goal_metric=self.goal_metric,
        )
        normalized_plots = normalize_artifacts(plots)
        for filename, plot in zip(plot_filenames, normalized_plots, strict=False):
            plot_path = os.path.join(config["RUNS_PATH"], filename)
            with open(plot_path, "wb") as file:
                pickle.dump(plot, file)
                plot_paths.append(plot_path)

        return plot_paths
