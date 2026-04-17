import numpy as np

from DashAI.back.dependencies.database.models import Run
from DashAI.back.evaluation.cv import CrossValidationEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.splitters.base_splitter import BaseSplitter


class NestedCrossValidationStrategy(CrossValidationEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)
        self.inner_splitter: BaseSplitter = kwargs.get("inner_splitter")

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        plot_paths = []

        outer_score_mean, outer_score_std = self.nested_cv(
            self.model, x, y, self.goal_metric
        )

        self._do_hpo(x, y, factory, run, db)

        return self.model, plot_paths

    def nested_cv(self, model, input_dataset, output_dataset, metric):
        # Implement the logic to evaluate the model using nested cross-validation
        # This will involve using self.inner_splitter
        # to create inner folds and evaluating the model on those folds

        metric = metric["class"]

        outer_scores = []

        for i in range(len(input_dataset) - 1):
            x_train_outer = input_dataset[i]["train"]
            y_train_outer = output_dataset[i]["train"]
            x_test_outer = input_dataset[i]["test"]
            y_test_outer = output_dataset[i]["test"]

            # Use inner_splitter to create inner folds
            inner_x, inner_y, _ = self.inner_splitter.split(
                x_train_outer, y_train_outer
            )

            # Evaluate the model on the inner folds
            # best model is the best model obtained from the inner fold in all trials
            best_model, _ = self.optimizer.optimize(
                model,
                inner_x,
                inner_y,
                self.run_optimizable_parameters,
                self.goal_metric,
                strategy=self.evaluate,
            )

            y_pred = best_model.predict(x_test_outer)
            output_dataset_transformed = best_model.prepare_output(
                y_test_outer, is_fit=False
            )

            score = metric.score(output_dataset_transformed, y_pred)

            outer_scores.append(score)

            # return the average and std of the scores obtained in the outer folds
        return np.mean(outer_scores), np.std(outer_scores)
