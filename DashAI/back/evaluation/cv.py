import os
from copyreg import pickle

import numpy as np
from kink import di

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Run
from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory


class CrossValidationEvaluationStrategy(BaseEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        config = di["config"]
        plot_paths = []

        # Execute HPO if optimizer and there are parameters to optimize
        if self.optimizer and self.run_optimizable_parameters:
            self._do_hpo(x, y, factory, run, db)

            # Generate hyperparameter plot
            trials = self.optimizer.get_trials_values()
            plot_filenames, plots = self.optimizer.create_plots(
                trials,
                run.id,
                n_params=len(self.run_optimizable_parameters),
                goal_metric=self.goal_metric,
            )
            for filename, plot in zip(plot_filenames, plots):
                plot_path = os.path.join(config["RUNS_PATH"], filename)
                with open(plot_path, "wb") as file:
                    pickle.dump(plot, file)
                    plot_paths.append(plot_path)

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

    def evaluate(self, model, input_dataset, output_dataset, metric, **kwargs):
        fold_index = kwargs.get("fold_index")
        folds_results = []

        # Suponiendo que el último fold es el conjunto completo
        for i in range(len(input_dataset) - 1):
            x_fold = input_dataset[i]
            y_fold = output_dataset[i]

            # Aquí se entrenaría el modelo con x_fold e y_fold y se calcula la métrica
            self.model.x_data = x_fold
            self.model.y_data = y_fold

            model.train(x_fold["train"], y_fold["train"])

            y_pred = model.predict(x_fold["test"])

            output_dataset_transformed = model.prepare_output(
                y_fold["test"], is_fit=False
            )

            if fold_index is None:
                model.calculate_metrics(
                    split=SplitEnum.TRAIN, level=LevelEnum.TRIAL, fold_index=i
                )
                model.calculate_metrics(
                    split=SplitEnum.TEST, level=LevelEnum.TRIAL, fold_index=i
                )
            else:
                model.calculate_metrics(
                    split=SplitEnum.TRAIN,
                    level=LevelEnum.TRIAL,
                    fold_index=fold_index,
                    inner_fold_index=i,
                )
                model.calculate_metrics(
                    split=SplitEnum.TEST,
                    level=LevelEnum.TRIAL,
                    fold_index=fold_index,
                    inner_fold_index=i,
                )

            score = metric.score(output_dataset_transformed, y_pred)
            folds_results.append(score)

        # Retorna el promedio de las métricas de los folds
        return np.mean(folds_results)
