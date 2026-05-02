from functools import partial

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Run
from DashAI.back.evaluation.cv import CrossValidationEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.splitters.fold_splitter import FoldSplitter


class NestedCrossValidationStrategy(CrossValidationEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)
        self.inner_splitter: FoldSplitter = kwargs.get("inner_splitter")

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        plot_paths = []

        self.nested_cv(self.model, x, y)
        self._do_hpo(x, y, factory, run, db)

        # Suponiendo que el último fold es el conjunto completo
        for i in range(len(x) - 1):
            x_fold = x[i]
            y_fold = y[i]

            self.model.x_data = x_fold
            self.model.y_data = y_fold

            self.model.train(x_fold["train"], y_fold["train"])

            self.model.calculate_metrics(
                split=SplitEnum.TRAIN, level=LevelEnum.FOLD, fold_index=i
            )
            self.model.calculate_metrics(
                split=SplitEnum.TEST, level=LevelEnum.FOLD, fold_index=i
            )

        self.model.train(x[-1]["train"], y[-1]["train"])

        return self.model, plot_paths

    def nested_cv(self, model, input_dataset, output_dataset):
        # Implement the logic to evaluate the model using nested cross-validation
        # This will involve using self.inner_splitter
        # to create inner folds and evaluating the model on those folds

        for i in range(len(input_dataset) - 1):
            x_outer = input_dataset[i]
            y_outer = output_dataset[i]

            # Use inner_splitter to create inner folds
            inner_x, inner_y, _ = self.inner_splitter.split(
                x_outer["train"], y_outer["train"]
            )

            strategy_with_context = partial(self.evaluate, fold_index=i)
            # Evaluate the model on the inner folds
            # best model is the best model obtained from the inner fold in all trials
            self.model, _ = self.optimizer.optimize(
                model,
                inner_x,
                inner_y,
                self.run_optimizable_parameters,
                self.goal_metric,
                strategy=strategy_with_context,
            )

            self.model.x_data = x_outer
            self.model.y_data = y_outer

            self.model.train(x_outer["train"], y_outer["train"])

            self.model.calculate_metrics(
                split=SplitEnum.TEST, level=LevelEnum.OUTER_FOLD, fold_index=i
            )
            self.model.calculate_metrics(
                split=SplitEnum.TRAIN, level=LevelEnum.OUTER_FOLD, fold_index=i
            )
