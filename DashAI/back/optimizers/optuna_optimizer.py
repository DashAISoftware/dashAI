from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.optimizers.base_optimizer import BaseOptimizer


class OptunaSchema(BaseSchema):
    n_trials: schema_field(
        int_field(gt=0),
        placeholder=10,
        description=MultilingualString(
            en=(
                "The quantity of trials per study. It must be of type positive integer."
            ),
            es=("La cantidad de pruebas por estudio. Debe ser un entero positivo."),
        ),
        alias=MultilingualString(en="N trials", es="N pruebas"),
    )  # type: ignore
    sampler: schema_field(
        enum_field(
            enum=[
                "TPESampler",
                "CmaEsSampler",
                "GridSampler",
                "GPSampler",
                "NSGAIISampler",
                "QMCSampler",
                "RandomSampler",
            ]
        ),
        placeholder="TPESampler",
        description=MultilingualString(
            en=(
                "The sampler algorithm to use for hyperparameter optimization. "
                "Different samplers use different strategies for exploring the "
                "hyperparameter space."
            ),
            es=(
                "El algoritmo de muestreo a usar para la optimización de "
                "hiperparámetros. Diferentes muestreadores usan diferentes "
                "estrategias para explorar el espacio de hiperparámetros."
            ),
        ),
        alias=MultilingualString(en="Sampler", es="Muestreador"),
    )  # type: ignore
    pruner: schema_field(
        enum_field(enum=["MedianPruner", "None"]),
        placeholder="None",
        description=MultilingualString(
            en=(
                "The pruner to use for early stopping of unpromising trials. "
                "'MedianPruner' stops trials below the median. 'None' disables pruning."
            ),
            es=(
                "El podador a usar para detener tempranamente pruebas poco "
                "prometedoras. 'MedianPruner' detiene pruebas bajo la mediana. "
                "'None' desactiva la poda."
            ),
        ),
        alias=MultilingualString(en="Pruner", es="Podador"),
    )  # type: ignore


class OptunaOptimizer(BaseOptimizer):
    DISPLAY_NAME: str = MultilingualString(
        en="Optuna Optimizer",
        es="Optimizador Optuna",
    )
    DESCRIPTION: str = MultilingualString(
        en="Hyperparameter optimization using Optuna library.",
        es="Optimización de hiperparámetros usando la librería Optuna.",
    )
    COLOR: str = "#E91E63"
    SCHEMA = OptunaSchema

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "TranslationTask",
        "RegressionTask",
    ]

    def __init__(self, n_trials=None, sampler=None, pruner=None):
        self.n_trials = n_trials
        self.sampler = sampler
        self.pruner = pruner

    def optimize(self, model, input_dataset, output_dataset, parameters, metric, task):
        """
        Optimization process

        Args:
            model (class): class for the model from the current experiment
            dataset (dict): dict with the data to train and validation
            parameters (dict): dict with the information to create the search space
            metric (class): class for the metric to optimize

        Returns
        -------
            None
        """
        import optuna

        sampler = getattr(optuna.samplers, self.sampler)

        self.model = model
        self.input_dataset = input_dataset
        self.output_dataset = output_dataset
        self.parameters = parameters
        direction = "maximize" if metric["metadata"]["maximize"] else "minimize"
        study = optuna.create_study(
            direction=direction, sampler=sampler(), pruner=self.pruner
        )

        self.metric = metric["class"]

        def objective(trial):
            # Set value for each hyperparameter and for each model
            # (either self or submodels nested inside)
            for obj, key, bounds, dtype in self.parameters:
                if dtype == "number":
                    value = trial.suggest_float(key, bounds[0], bounds[1], log=False)
                elif dtype == "integer":
                    value = trial.suggest_int(key, bounds[0], bounds[1], log=False)
                else:
                    raise ValueError(f"Unsupported parameter type for {key} : {dtype}")
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

            return score

        study.optimize(objective, n_trials=self.n_trials)

        best_params = study.best_params
        best_model = self.model
        for hyperparameter, value in best_params.items():
            setattr(best_model, hyperparameter, value)
        best_model.train(self.input_dataset["train"], self.output_dataset["train"])
        self.model = best_model
        self.study = study

    def get_model(self):
        return self.model

    def get_trials_values(self):
        import optuna

        trials = []
        for trial in self.study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                trials.append({"params": trial.params, "value": trial.value})
        return trials

    def get_best_params(self):
        """Return the best parameters found during optimization."""
        return self.study.best_params
