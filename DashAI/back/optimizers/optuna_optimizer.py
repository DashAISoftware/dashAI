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
            pt=("A quantidade de tentativas por estudo. Deve ser um inteiro positivo."),
            de=(
                "Die Anzahl der Versuche pro Studie. Muss eine positive ganze Zahl "
                "sein."
            ),
            zh="每次研究的试验次数，必须为正整数。",
        ),
        alias=MultilingualString(
            en="N trials",
            es="N pruebas",
            pt="N tentativas",
            de="N Versuche",
            zh="试验次数",
        ),
    )  # type: ignore
    sampler: schema_field(
        enum_field(
            enum=[
                "TPESampler",
                "CmaEsSampler",
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
            pt=(
                "O algoritmo de amostragem a usar para a otimização de "
                "hiperparâmetros. Diferentes amostradores usam diferentes "
                "estratégias para explorar o espaço de hiperparâmetros."
            ),
            de=(
                "Der Abtastalgorithmus für die Hyperparameter-Optimierung. "
                "Verschiedene Abtaster verwenden unterschiedliche Strategien "
                "zur Erkundung des Hyperparameter-Raums."
            ),
            zh=(
                "用于超参数优化的采样算法。不同的采样器使用不同的策略来探索超参数空间。"
            ),
        ),
        alias=MultilingualString(
            en="Sampler",
            es="Muestreador",
            pt="Amostrador",
            de="Abtaster",
            zh="采样器",
        ),
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
            pt=(
                "O podador a usar para parada antecipada de tentativas pouco "
                "promissoras. 'MedianPruner' para tentativas abaixo da mediana. "
                "'None' desativa a poda."
            ),
            de=(
                "Der Pruner für den vorzeitigen Abbruch aussichtsloser Versuche. "
                "'MedianPruner' stoppt Versuche unterhalb des Mittelwerts. "
                "'None' deaktiviert das Pruning."
            ),
            zh=(
                "用于提前停止无希望试验的剪枝器。"
                "'MedianPruner' 停止低于中位数的试验。'None' 禁用剪枝。"
            ),
        ),
        alias=MultilingualString(
            en="Pruner",
            es="Podador",
            pt="Podador",
            de="Pruner",
            zh="剪枝器",
        ),
    )  # type: ignore


class OptunaOptimizer(BaseOptimizer):
    DISPLAY_NAME: str = MultilingualString(
        en="Optuna Optimizer",
        es="Optimizador Optuna",
        pt="Otimizador Optuna",
        de="Optuna-Optimierer",
        zh="Optuna 优化器",
    )
    DESCRIPTION: str = MultilingualString(
        en="Hyperparameter optimization using Optuna library.",
        es="Optimización de hiperparámetros usando la librería Optuna.",
        pt="Otimização de hiperparâmetros usando a biblioteca Optuna.",
        de="Hyperparameter-Optimierung mit der Optuna-Bibliothek.",
        zh="使用 Optuna 库进行超参数优化。",
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

        # Write the best values back onto the objects that actually declare them.
        # `self.parameters` holds (owner, key, bounds, dtype) tuples built by
        # ModelFactory, where `owner` may be a nested sub-component rather than the
        # top-level model. Assigning to the wrapper instead leaves the sub-component
        # holding whatever the last trial set, so the model that gets retrained and
        # serialized is the last one tried, not the best one. This mirrors what
        # `objective` already does above.
        best_params = study.best_params
        for obj, key, _bounds, _dtype in self.parameters:
            if key in best_params:
                setattr(obj, key, best_params[key])
        self.model.train(self.input_dataset["train"], self.output_dataset["train"])
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
