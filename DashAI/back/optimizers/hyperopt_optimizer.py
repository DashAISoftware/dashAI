from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.optimizers.base_optimizer import BaseOptimizer


class HyperOptSchema(BaseSchema):
    n_trials: schema_field(
        int_field(gt=0),
        placeholder=10,
        description=MultilingualString(
            en=(
                "The quantity of trials per study. It must be of type positive integer."
            ),
            es=("La cantidad de pruebas por estudio. Debe ser un entero positivo."),
            pt=("A quantidade de tentativas por estudo. Deve ser um inteiro positivo."),
        ),
        alias=MultilingualString(en="N trials", es="N pruebas", pt="N tentativas"),
    )  # type: ignore
    sampler: schema_field(
        enum_field(enum=["tpe", "rand"]),
        placeholder="tpe",
        description=MultilingualString(
            en=(
                "The sampler algorithm to use for hyperparameter optimization. "
                "Must be 'tpe' (Tree-structured Parzen Estimator) or 'rand' (Random)."
            ),
            es=(
                "El algoritmo de muestreo a usar para la optimización de "
                "hiperparámetros. Debe ser 'tpe' (Tree-structured Parzen Estimator) "
                "o 'rand' (Aleatorio)."
            ),
            pt=(
                "O algoritmo de amostragem a usar para a otimização de "
                "hiperparâmetros. Deve ser 'tpe' (Tree-structured Parzen Estimator) "
                "ou 'rand' (Aleatório)."
            ),
        ),
        alias=MultilingualString(en="Sampler", es="Muestreador", pt="Amostrador"),
    )  # type: ignore


class HyperOptOptimizer(BaseOptimizer):
    DISPLAY_NAME: str = MultilingualString(
        en="HyperOpt Optimizer",
        es="Optimizador HyperOpt",
        pt="Otimizador HyperOpt",
    )
    DESCRIPTION: str = MultilingualString(
        en="Hyperparameter optimization using HyperOpt library.",
        es="Optimización de hiperparámetros usando la librería HyperOpt.",
        pt="Otimização de hiperparâmetros usando a biblioteca HyperOpt.",
    )
    COLOR: str = "#FF5722"
    SCHEMA = HyperOptSchema

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "TranslationTask",
    ]

    def __init__(self, n_trials=None, sampler=None):
        self.n_trials = n_trials
        self.sampler = sampler

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
        from hyperopt import hp

        search_space = {}

        for _, hyperparameter, values, dtype in hyperparams_data:
            if dtype == "integer":
                search_space[hyperparameter] = hp.quniform(
                    hyperparameter, values[0], values[1], 1
                )
            elif dtype == "number":
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
        import importlib

        from hyperopt import Trials, fmin

        self.model = model
        self.input_dataset = input_dataset
        self.output_dataset = output_dataset
        self.parameters = parameters
        self.metric = metric["class"]

        sampler = importlib.import_module(f"hyperopt.{self.sampler}").suggest

        param_mapping = {key: (obj, key) for obj, key, _, _ in self.parameters}

        search_space = self.search_space(self.parameters)

        def objective(params):
            for param_name, value in params.items():
                obj, key = param_mapping[param_name]
                setattr(obj, key, value)

            self.model.train(self.input_dataset["train"], self.output_dataset["train"])
            y_pred = self.model.predict(input_dataset["validation"])

            # Calculate metric for train and validation data each trial
            self.model.calculate_metrics(split=SplitEnum.TRAIN, level=LevelEnum.TRIAL)
            self.model.calculate_metrics(
                split=SplitEnum.VALIDATION, level=LevelEnum.TRIAL
            )

            output_dataset_transformed = self.model.prepare_output(
                output_dataset["validation"], is_fit=False
            )

            score = self.metric.score(output_dataset_transformed, y_pred)

            return -score if metric["metadata"]["maximize"] else score

        trials = Trials()
        fmin(
            fn=objective,
            space=search_space,
            algo=sampler,
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

    def get_best_params(self):
        """Return the best parameters found during optimization."""
        best_trial = min(
            self.trials, key=lambda t: t["result"].get("loss", float("inf"))
        )
        return {key: val[0] for key, val in best_trial["misc"]["vals"].items()}
