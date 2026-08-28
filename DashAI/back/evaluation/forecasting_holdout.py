"""Holdout evaluation for models that forecast a series from its own history."""

from DashAI.back.core.enums.metrics import SplitEnum
from DashAI.back.evaluation.holdout import SinglePartitionEvaluationStrategy


class ForecastingHoldoutEvaluationStrategy(SinglePartitionEvaluationStrategy):
    """Holdout evaluation that treats validation as history rather than a sample.

    Two things the ordinary holdout strategy assumes are wrong for a
    forecaster, and both of them are decisions about evaluation rather than
    about any model.

    **The training partition is not scored.** Scoring it would mean asking the
    model about dates it was fitted on. That is an in-sample fit statistic,
    which is a real diagnostic but is not comparable with a forecast made
    several steps out; showing the two side by side in one results table
    invites exactly that comparison. Only validation and test are recorded.

    **The kept model is fitted through validation.** For most tasks the
    validation partition is a held out sample that has to stay out of the fit.
    For a forecaster it is simply the most recent stretch of the series, and
    the stretch nearest to whatever comes next. Leaving it out makes the model
    reach across the whole validation window before arriving at the first test
    row, so the test metrics describe a longer horizon than the one being
    asked about.

    The validation metrics are still measured on a model fitted on training
    data alone, which is what makes them honest: they are recorded before the
    refit. So the two columns in the results table answer different questions,
    and both answer them fairly.

        validation metrics  <- model fitted on train
        test metrics        <- model fitted on train + validation

    Hyperparameter search is untouched. Its trials are scored on validation,
    so they must not be fitted on it.
    """

    COMPATIBLE_COMPONENTS = ["ForecastingTask"]
    SCORED_SPLITS: tuple = (SplitEnum.VALIDATION, SplitEnum.TEST)

    def execute(self, x, y, run, db):
        """Score validation on a trial fit, then refit and score test.

        Parameters
        ----------
        x : DatasetDict
            Input partitions, keyed by split name.
        y : DatasetDict
            Target partitions, keyed by split name.
        run : Run
            Database model representing the current run.
        db : Session
            SQLAlchemy session used to persist metrics.

        Returns
        -------
        tuple
            The trained model and the paths of any HPO plots.
        """
        plot_paths = []
        model = self.model

        model.x_data = x
        model.y_data = y

        if self.optimizer and self.run_optimizable_parameters:
            self._report_progress(0.2, "Hyperparameter optimization")
            model = self._do_hpo(model, x, y, run, db)
            plot_paths = self._generate_hpo_plots(run)

        # Fitted on training data only, so the validation score below measures
        # a model that has not seen the rows it is being scored on.
        self._report_progress(0.5, "Training")
        model.train(x["train"], y["train"])

        self._report_progress(0.8, "Computing validation metrics")
        self._calculate_metrics_if_missing(model, run, db, SplitEnum.VALIDATION)

        # Now the model that gets kept: the same configuration, refitted with
        # the validation rows included, since for a series they are history.
        self._report_progress(0.9, "Refitting on train and validation")
        self._fit_final_model(model, x, y)

        self._report_progress(0.95, "Computing test metrics")
        self._calculate_metrics_if_missing(model, run, db, SplitEnum.TEST)

        return model, plot_paths

    def _fit_final_model(self, model, x, y):
        """Fit the kept model on the training and validation rows together.

        Parameters
        ----------
        model : BaseModel
            The model to fit.
        x : DatasetDict
            Input partitions.
        y : DatasetDict
            Target partitions.
        """
        validation_x = x.get("validation")
        validation_y = y.get("validation")

        if validation_x is None or validation_y is None or len(validation_x) == 0:
            model.train(x["train"], y["train"])
            return

        extend = type(model)._extend
        model.train(extend(x["train"], validation_x), extend(y["train"], validation_y))
