import importlib

from hyperopt import Trials, fmin, hp, rand, tpe  # noqa: F401

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.optimizers.base_optimizer import BaseOptimizer


class HyperOptSchema(BaseSchema):
    n_trials: schema_field(
        int_field(gt=0),
        placeholder=10,
        description="The parameter 'n_trials' is the quantity of trials"
        "per study. It must be of type positive integer.",
    )  # type: ignore
    sampler: schema_field(
        enum_field(enum=["tpe", "rand"]),
        placeholder="tpe",
        description="Coefficient for 'rbf', 'poly' and 'sigmoid' kernels"
        ". Must be in string format and can be 'scale' or 'auto'.",
    )  # type: ignore


class HyperOptOptimizer(BaseOptimizer):
    SCHEMA = HyperOptSchema

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "TranslationTask",
    ]

    def __init__(self, n_trials=None, sampler=None):
        self.n_trials = n_trials
        self.sampler = importlib.import_module(f"hyperopt.{sampler}").suggest

    def search_space(self, hyperparams_data):
        """
        Configure the search space.

        Args:
            hyperparams_data (dict[str, any]): Dict with the range values
            for the possible search space

        Returns
        -------
            search_space: Dict with the information for the search space .
        """
        search_space = {}

        for hyperparameter, values in hyperparams_data.items():
            if isinstance(values[0], int):
                search_space[hyperparameter] = hp.quniform(
                    hyperparameter, values[0], values[1], 1
                )
            elif isinstance(values[0], float):
                search_space[hyperparameter] = hp.uniform(
                    hyperparameter, values[0], values[1]
                )
        return search_space

    def optimize(self, model, input_dataset, output_dataset, parameters, metric, task):
        """
        Optimization process

        Args:
            model (class): class for the model from the current experiment
            input_dataset (dict): dict with train dataset
            output_dataset (dict): dict with validation dataset
            parameters (dict): dict with the information to create the search space
            metric (class): class for the metric to optimize
            task (string): Name of the current task

        Returns
        -------
            None
        """
        self.model = model
        self.input_dataset = input_dataset
        self.output_dataset = output_dataset
        self.parameters = parameters
        self.metric = metric["class"]
        search_space = self.search_space(self.parameters)

        if task == "TextClassificationTask":

            def objective(params):
                model_eval = self.model
                for key, value in params.items():
                    setattr(model_eval, key, value)
                model_eval.fit(
                    self.input_dataset["train"], self.output_dataset["train"]
                )
                y_pred = model_eval.predict(input_dataset["validation"])
                score = 1 * self.metric.score(output_dataset["validation"], y_pred)
                return score

        else:

            def objective(params):
                model_eval = self.model
                for key, value in params.items():
                    int_value = int(value)
                    setattr(model_eval, key, int_value)
                model_eval.fit(
                    self.input_dataset["train"], self.output_dataset["train"]
                )
                y_pred = model_eval.predict(input_dataset["validation"])
                score = 1 * self.metric.score(output_dataset["validation"], y_pred)
                return score

        trials = Trials()
        fmin(
            fn=objective,
            space=search_space,
            algo=self.sampler,
            max_evals=self.n_trials,
            trials=trials,
        )
        self.trials = trials

    def get_model(self):
        return self.model

    def get_trials_values(self):
        trials = []
        for trial in self.trials:
            if trial["result"]["status"] == "ok":
                params = {key: val[0] for key, val in trial["misc"]["vals"].items()}
                trials.append({"params": params, "value": trial["result"]["loss"]})
        return trials
