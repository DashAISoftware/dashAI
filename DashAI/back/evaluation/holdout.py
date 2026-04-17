import os
import pickle

from kink import di

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric, Run
from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory


class HoldoutEvaluationStrategy(BaseEvaluationStrategy):
    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        config = di["config"]
        plot_paths = []

        # set the data used for model training and evaluation
        self.model.x_data = x
        self.model.y_data = y

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

        else:
            # otherwise, just train the model with the provided data and return it
            self.model.train(x["train"], y["train"], x["validation"], y["validation"])

        # Calculate metrics at the end of training if not done already
        last_train_metric = (
            db.query(Metric)
            .filter_by(run_id=run.id, split="TRAIN", level="LAST")
            .first()
        )
        if not last_train_metric:
            self.model.calculate_metrics(
                split=SplitEnum.TRAIN,
                level=LevelEnum.LAST,
            )
        last_val_metric = (
            db.query(Metric)
            .filter_by(run_id=run.id, split="VALIDATION", level="LAST")
            .first()
        )
        if not last_val_metric:
            self.model.calculate_metrics(
                split=SplitEnum.VALIDATION,
                level=LevelEnum.LAST,
            )
        last_test_metric = (
            db.query(Metric)
            .filter_by(run_id=run.id, split="TEST", level="LAST")
            .first()
        )
        if not last_test_metric:
            self.model.calculate_metrics(
                split=SplitEnum.TEST,
                level=LevelEnum.LAST,
            )

        return self.model, plot_paths

    def evaluate(self, model, input_dataset, output_dataset, metric):
        # Train the model with the training set
        model.train(input_dataset["train"], output_dataset["train"])

        y_pred = model.predict(input_dataset["validation"])

        output_dataset_transformed = model.prepare_output(
            output_dataset["validation"], is_fit=False
        )

        # Calculate metric for train and validation data each trial
        model.calculate_metrics(split=SplitEnum.TRAIN, level=LevelEnum.TRIAL)
        model.calculate_metrics(split=SplitEnum.VALIDATION, level=LevelEnum.TRIAL)

        score = metric.score(output_dataset_transformed, y_pred)

        return model, score
