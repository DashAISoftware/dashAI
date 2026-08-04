from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric, Run
from DashAI.back.evaluation.base_evaluation_strategy import BaseEvaluationStrategy
from DashAI.back.models.model_factory import ModelFactory


class HoldoutEvaluationStrategy(BaseEvaluationStrategy):
    """Evaluation strategy implementing holdout (train/validation/test split)
    validation.

    This strategy divides the dataset into three mutually exclusive partitions:
    training, validation, and test. The training set is used for model training,
    the validation set for HPO, and the test set for final evaluation.

    The strategy handles metric aggregation at multiple levels:
    - TRIAL level: Metrics during HPO trials on validation set
    - LAST level: Final metrics computed on all three partitions after training
    """

    def __init__(
        self, model, optimizer, run_optimizable_parameters, goal_metric, **kwargs
    ):
        """Initialize the holdout evaluation strategy.

        Parameters
        ----------
        model : BaseModel
            The machine learning model to be trained and evaluated.
        optimizer : BaseOptimizer
            Hyperparameter optimizer (None if no HPO is needed).
        run_optimizable_parameters : dict or list
            Parameters to optimize during HPO.
        goal_metric : dict (obtained from Metric component registry)
            The metric to optimize in HPO trials.
        **kwargs
            Additional keyword arguments (ignored).
        """
        super().__init__(model, optimizer, run_optimizable_parameters, goal_metric)

    def execute(self, x, y, factory: ModelFactory, run: Run, db):
        """Execute holdout validation: train on training set, optimize with validation,
        evaluate on test.

        Trains a model on the training partition and optionally performs hyperparameter
        optimization using the validation set. Finally evaluates the trained model on
        all three partitions (train, validation, test) and returns the model with plots.

        Parameters
        ----------
        x : DatasetDict
            DatasetDict with data partitions:
            {"train": X_train, "validation": X_val, "test": X_test}
        y : DatasetDict
            DatasetDict with label partitions:
            {"train": y_train, "validation": y_val, "test": y_test}
        factory : ModelFactory
            Factory for creating and updating model instances with new hyperparameters.
        run : Run
            Database run instance for storing results and configuration.
        db : Session
            SQLAlchemy database session for persisting metrics.

        Returns
        -------
        tuple
            (trained_model, plot_paths) where:
            - trained_model : BaseModel - The trained model
            - plot_paths : list[str] - Paths to HPO visualization plot files
        """
        plot_paths = []

        # set the data used for model training and evaluation
        self.model.x_data = x
        self.model.y_data = y

        # Execute HPO if optimizer and there are parameters to optimize
        if self.optimizer and self.run_optimizable_parameters:
            self._do_hpo(x, y, factory, run, db)
            plot_paths = self._generate_hpo_plots(run)

        # Train the model with the provided data and return it
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
        """Evaluate model on validation set during HPO trials.

        Trains the model on the training set and computes the metric on the validation
        set. Used as the objective function during hyperparameter optimization.

        Parameters
        ----------
        model : BaseModel
            The model instance to evaluate with specific hyperparameters.
        input_dataset : DatasetDict
            DatasetDict with data partitions
            {"train": X_train, "validation": X_val, "test": X_test}.
        output_dataset : DatasetDict
            DatasetDict with label partitions
            {"train": y_train, "validation": y_val, "test": y_test}.
        metric : Metric
            The metric function to compute on predictions.

        Returns
        -------
        float
            The metric score value for this hyperparameter combination.
        """
        # Train the model with the training set
        model.train(input_dataset["train"], output_dataset["train"])

        # Evaluate the model on the validation set
        y_pred = model.predict(input_dataset["validation"])

        output_dataset_transformed = model.prepare_output(
            output_dataset["validation"], is_fit=False
        )

        # Calculate metric for train and validation data each trial
        model.calculate_metrics(split=SplitEnum.TRAIN, level=LevelEnum.TRIAL)
        model.calculate_metrics(split=SplitEnum.VALIDATION, level=LevelEnum.TRIAL)

        # Compute the objective metric score on the validation set
        score = metric.score(output_dataset_transformed, y_pred)

        return score
