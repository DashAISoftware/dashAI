from sklearn.ensemble import GradientBoostingRegressor as _GBRegressor

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    float_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class GradientBoostingRSchema(BaseSchema):
    """Schema that configures the Gradient Boosting Regressor.

    Gradient Boosting is a sequential ensemble regression method that fits a new
    decision tree at each stage to the negative gradient (pseudo-residuals) of a
    differentiable loss function. The underlying implementation is
    ``sklearn.ensemble.GradientBoostingRegressor``.
    """

    loss: schema_field(
        enum_field(enum=["squared_error", "absolute_error", "huber", "quantile"]),
        placeholder="squared_error",
        description=MultilingualString(
            en="Loss function to be optimized.",
            es="Función de pérdida a optimizar.",
            pt="Função de perda a ser otimizada.",
            de="Zu optimierende Verlustfunktion.",
        ),
        alias=MultilingualString(en="Loss", es="Pérdida", pt="Perda", de="Verlust"),
    )  # type: ignore

    learning_rate: schema_field(
        optimizer_float_field(ge=0.01),
        placeholder={
            "optimize": False,
            "fixed_value": 0.1,
            "lower_bound": 0.01,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en="Learning rate shrinks the contribution of each tree.",
            es="La tasa de aprendizaje reduce la contribución de cada árbol.",
            pt="A taxa de aprendizado reduz a contribuição de cada árvore.",
            de="Die Lernrate verringert den Beitrag jedes Baums.",
        ),
        alias=MultilingualString(
            en="Learning rate",
            es="Tasa de aprendizaje",
            pt="Taxa de aprendizado",
            de="Lernrate",
        ),
    )  # type: ignore

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 10,
            "upper_bound": 1000,
        },
        description=MultilingualString(
            en="The number of boosting stages to be run.",
            es="El número de etapas de boosting a ejecutar.",
            pt="O número de etapas de boosting a executar.",
            de="Die Anzahl der auszuführenden Boosting-Stufen.",
        ),
        alias=MultilingualString(
            en="N estimators",
            es="N estimadores",
            pt="N estimadores",
            de="Anzahl Schätzer",
        ),
    )  # type: ignore

    subsample: schema_field(
        optimizer_float_field(ge=0.1, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 1.0,
            "lower_bound": 0.1,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "The fraction of samples to be used for fitting the "
                "individual base learners."
            ),
            es=(
                "La fracción de muestras a usar para ajustar los "
                "aprendices base individuales."
            ),
            pt=(
                "A fração de amostras a usar para ajustar os "
                "aprendizes base individuais."
            ),
            de=("Der Anteil der Stichproben zum Anpassen der einzelnen Basislerner."),
        ),
        alias=MultilingualString(
            en="Subsample", es="Submuestreo", pt="Subamostra", de="Teilstichprobe"
        ),
    )  # type: ignore

    criterion: schema_field(
        enum_field(enum=["friedman_mse", "mse", "mae"]),
        placeholder="friedman_mse",
        description=MultilingualString(
            en="The function to measure the quality of a split.",
            es="La función para medir la calidad de una división.",
            pt="A função para medir a qualidade de uma divisão.",
            de="Die Funktion zur Messung der Qualität einer Aufteilung.",
        ),
        alias=MultilingualString(
            en="Criterion", es="Criterio", pt="Critério", de="Kriterium"
        ),
    )  # type: ignore

    min_samples_split: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.5,
            "lower_bound": 0.1,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en="The minimum number of samples required to split an internal node.",
            es="El número mínimo de muestras requeridas para dividir un nodo interno.",
            pt="O número mínimo de amostras necessárias para dividir um nó interno.",
            de="Mindestanzahl von Stichproben zum Aufteilen eines internen Knotens.",
        ),
        alias=MultilingualString(
            en="Min samples split",
            es="Mínimas muestras de división",
            pt="Mínimas amostras de divisão",
            de="Minimale Aufteilungsstichproben",
        ),
    )  # type: ignore

    min_samples_leaf: schema_field(
        optimizer_float_field(gt=0.0, le=0.5),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 20,
        },
        description=MultilingualString(
            en="The minimum number of samples required to be at a leaf node.",
            es="El número mínimo de muestras requeridas para estar en una hoja.",
            pt="O número mínimo de amostras necessárias para estar em um nó folha.",
            de="Mindestanzahl von Stichproben an einem Blattknoten.",
        ),
        alias=MultilingualString(
            en="Min samples leaf",
            es="Mínimas muestras para hoja",
            pt="Mínimas amostras para folha",
            de="Minimale Stichproben für Blatt",
        ),
    )  # type: ignore

    min_weight_fraction_leaf: schema_field(
        float_field(ge=0.0, le=0.5),
        placeholder=0.0,
        description=MultilingualString(
            en=(
                "The minimum weighted fraction of the sum total of weights "
                "(of all the input samples) required to be at a leaf node."
            ),
            es=(
                "La fracción ponderada mínima de la suma total de pesos "
                "(de todas las muestras de entrada) requerida para estar en una hoja."
            ),
            pt=(
                "A fração ponderada mínima da soma total de pesos "
                "(de todas as amostras de entrada) necessária para estar em "
                "um nó folha."
            ),
            de=(
                "Der minimale gewichtete Anteil der Gesamtgewichte "
                "(aller Eingangsstichproben), der an einem Blattknoten erforderlich "
                "ist."
            ),
        ),
        alias=MultilingualString(
            en="Min weight fraction leaf",
            es="Fracción de peso mínima para hoja",
            pt="Fração mínima de peso para folha",
            de="Minimaler Gewichtsanteil für Blatt",
        ),
    )  # type: ignore

    max_depth: schema_field(
        none_type(optimizer_int_field(ge=1)),
        placeholder=3,
        description=MultilingualString(
            en="The maximum depth of the individual regression estimators.",
            es="La profundidad máxima de los estimadores de regresión individuales.",
            pt="A profundidade máxima dos estimadores de regressão individuais.",
            de="Die maximale Tiefe der einzelnen Regressionsschätzer.",
        ),
        alias=MultilingualString(
            en="Max depth",
            es="Profundidad máxima",
            pt="Profundidade máxima",
            de="Maximale Tiefe",
        ),
    )  # type: ignore

    min_impurity_decrease: schema_field(
        float_field(ge=0.0),
        placeholder=0.0,
        description=MultilingualString(
            en=(
                "A node will be split if this split induces a decrease of "
                "the impurity greater than or equal to this value."
            ),
            es=(
                "Un nodo se dividirá si esta división induce una disminución de "
                "la impureza mayor o igual a este valor."
            ),
            pt=(
                "Um nó será dividido se esta divisão induzir uma diminuição da "
                "impureza maior ou igual a este valor."
            ),
            de=(
                "Ein Knoten wird aufgeteilt, wenn diese Aufteilung eine Verringerung "
                "der Unreinheit größer oder gleich diesem Wert bewirkt."
            ),
        ),
        alias=MultilingualString(
            en="Min impurity decrease",
            es="Disminución mínima de impureza",
            pt="Diminuição mínima de impureza",
            de="Minimale Unreinheitsabnahme",
        ),
    )  # type: ignore

    random_state: schema_field(
        none_type(optimizer_int_field(ge=0)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The seed of the pseudo-random number generator to use "
                "when shuffling the data."
            ),
            es=(
                "La semilla del generador de números pseudoaleatorios a usar "
                "al mezclar los datos."
            ),
            pt=(
                "A semente do gerador de números pseudoaleatórios a usar "
                "ao embaralhar os dados."
            ),
            de=("Der Seed des Pseudozufallszahlengenerators beim Mischen der Daten."),
        ),
        alias=MultilingualString(
            en="Random state",
            es="Estado aleatorio",
            pt="Estado aleatório",
            de="Zufallszustand",
        ),
    )  # type: ignore

    max_features: schema_field(
        union_type(
            optimizer_float_field(gt=0.0, le=1.0),
            enum_field(enum=["sqrt", "log2", None]),
        ),
        placeholder=None,
        description=MultilingualString(
            en=("The number of features to consider when looking for the best split."),
            es=(
                "El número de características a considerar al buscar la mejor división."
            ),
            pt=("O número de características a considerar ao buscar a melhor divisão."),
            de=(
                "Die Anzahl der Merkmale, die bei der Suche nach der besten Aufteilung "
                "berücksichtigt werden."
            ),
        ),
        alias=MultilingualString(
            en="Max features",
            es="Máximas características",
            pt="Máximo de características",
            de="Maximale Merkmale",
        ),
    )  # type: ignore

    alpha: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.9,
            "lower_bound": 0.1,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en=(
                "The alpha-quantile of the Huber loss function and the "
                "quantile loss function."
            ),
            es=(
                "El alfa-cuantil de la función de pérdida de Huber y "
                "la función de pérdida cuantil."
            ),
            pt=(
                "O quantil alfa da função de perda de Huber e "
                "da função de perda quantil."
            ),
            de=(
                "Das Alpha-Quantil der Huber-Verlustfunktion und "
                "der Quantil-Verlustfunktion."
            ),
        ),
        alias=MultilingualString(en="Alpha", es="Alfa", pt="Alfa", de="Alpha"),
    )  # type: ignore

    verbose: schema_field(
        optimizer_int_field(ge=0),
        placeholder={
            "optimize": False,
            "fixed_value": 0,
            "lower_bound": 0,
            "upper_bound": 100,
        },
        description=MultilingualString(
            en="Enable verbose output.",
            es="Habilitar salida detallada.",
            pt="Habilitar saída detalhada.",
            de="Ausführliche Ausgabe aktivieren.",
        ),
        alias=MultilingualString(
            en="Verbose", es="Verboso", pt="Verboso", de="Ausführlich"
        ),
    )  # type: ignore

    max_leaf_nodes: schema_field(
        none_type(optimizer_int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en="Grow trees with max_leaf_nodes in best-first fashion.",
            es="Crecer árboles con max_leaf_nodes de manera best-first.",
            pt="Crescer árvores com max_leaf_nodes de maneira melhor-primeiro.",
            de="Bäume mit max_leaf_nodes nach dem Best-First-Verfahren wachsen lassen.",
        ),
        alias=MultilingualString(
            en="Max leaf nodes",
            es="Máximos nodos hoja",
            pt="Máximos nós folha",
            de="Maximale Blattknoten",
        ),
    )  # type: ignore

    warm_start: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en=(
                "When set to True, reuse the solution of the previous call "
                "to fit and add more estimators to the ensemble."
            ),
            es=(
                "Cuando se establece en True, reutiliza la solución de la llamada "
                "anterior a fit y agrega más estimadores al conjunto."
            ),
            pt=(
                "Quando definido como True, reutiliza a solução da chamada anterior "
                "a fit e adiciona mais estimadores ao conjunto."
            ),
            de=(
                "Wenn True, wird die Lösung des vorherigen fit-Aufrufs wiederverwendet "
                "und dem Ensemble weitere Schätzer hinzugefügt."
            ),
        ),
        alias=MultilingualString(
            en="Warm start",
            es="Inicio en caliente",
            pt="Início a quente",
            de="Warmer Start",
        ),
    )  # type: ignore

    validation_fraction: schema_field(
        optimizer_float_field(gt=0.0, le=1.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.1,
            "lower_bound": 0.1,
            "upper_bound": 0.5,
        },
        description=MultilingualString(
            en=(
                "The proportion of training data to set aside as "
                "validation set for early stopping."
            ),
            es=(
                "La proporción de datos de entrenamiento a reservar como "
                "conjunto de validación para detención temprana."
            ),
            pt=(
                "A proporção dos dados de treinamento a reservar como "
                "conjunto de validação para parada antecipada."
            ),
            de=(
                "Der Anteil der Trainingsdaten, der als Validierungsmenge "
                "für frühzeitigen Stopp zurückgehalten wird."
            ),
        ),
        alias=MultilingualString(
            en="Validation fraction",
            es="Fracción de validación",
            pt="Fração de validação",
            de="Validierungsanteil",
        ),
    )  # type: ignore

    n_iter_no_change: schema_field(
        none_type(optimizer_int_field(ge=1)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The number of iterations with no improvement to wait "
                "before stopping the training."
            ),
            es=(
                "El número de iteraciones sin mejora a esperar "
                "antes de detener el entrenamiento."
            ),
            pt=(
                "O número de iterações sem melhora a aguardar "
                "antes de interromper o treinamento."
            ),
            de=(
                "Die Anzahl der Iterationen ohne Verbesserung, die "
                "vor dem Trainingsabbruch abgewartet werden."
            ),
        ),
        alias=MultilingualString(
            en="N iterations no change",
            es="N iteraciones sin cambio",
            pt="N iterações sem mudança",
            de="N Iterationen ohne Änderung",
        ),
    )  # type: ignore

    tol: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0001,
            "lower_bound": 1e-5,
            "upper_bound": 1e-1,
        },
        description=MultilingualString(
            en="Tolerance for the early stopping.",
            es="Tolerancia para la detención temprana.",
            pt="Tolerância para a parada antecipada.",
            de="Toleranz für den frühzeitigen Stopp.",
        ),
        alias=MultilingualString(
            en="Tolerance", es="Tolerancia", pt="Tolerância", de="Toleranz"
        ),
    )  # type: ignore

    ccp_alpha: schema_field(
        optimizer_float_field(ge=0.0),
        placeholder={
            "optimize": False,
            "fixed_value": 0.0,
            "lower_bound": 0.0,
            "upper_bound": 1.0,
        },
        description=MultilingualString(
            en="Complexity parameter used for Minimal Cost-Complexity Pruning.",
            es="Parámetro de complejidad usado para poda de costo-complejidad mínima.",
            pt=(
                "Parâmetro de complexidade usado para poda de "
                "custo-complexidade mínima."
            ),
            de="Komplexitätsparameter für minimales Kosten-Komplexitäts-Pruning.",
        ),
        alias=MultilingualString(
            en="CCP alpha", es="CCP alfa", pt="CCP alfa", de="CCP Alpha"
        ),
    )  # type: ignore


class GradientBoostingR(RegressionModel, SklearnLikeRegressor, _GBRegressor):
    """Gradient boosting regressor that builds
    an ensemble of decision trees sequentially.

    Gradient Boosting builds an additive model in a forward stage-wise fashion. At
    each stage a shallow decision tree is fitted to the negative gradient of the
    chosen loss function with respect to the current ensemble prediction. A
    ``learning_rate`` shrinkage factor scales the contribution of each new tree,
    trading a slower learning process for better generalisation.

    Key hyperparameters include ``n_estimators`` (number of boosting stages),
    ``learning_rate``, ``max_depth``, ``subsample`` (fraction of training samples
    per tree, enabling stochastic gradient boosting), ``loss``, and
    ``min_samples_split``. The implementation wraps scikit-learn's
    ``GradientBoostingRegressor``.

    References
    ----------
    - [1] Friedman, J.H. (2001). "Greedy function approximation: a gradient
           boosting machine." Annals of Statistics, 29(5), 1189-1232.
           https://doi.org/10.1214/aos/1013203451
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html
    """

    SCHEMA = GradientBoostingRSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Gradient Boosting Regression",
        es="Regresión Gradient Boosting",
        pt="Regressor por Gradient Boosting",
        de="Gradient-Boosting-Regression",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Ensemble method that builds trees sequentially to correct previous errors."
        ),
        es=(
            "Método de conjunto que construye árboles secuencialmente para corregir "
            "errores anteriores."
        ),
        pt=(
            "Método de conjunto que constrói árvores sequencialmente para corrigir "
            "erros anteriores."
        ),
        de=(
            "Ensemble-Methode, die Bäume sequenziell aufbaut, um vorherige Fehler zu "
            "korrigieren."
        ),
    )
    COLOR: str = "#4CAF50"
    ICON: str = "AutoGraph"

    def __init__(self, **kwargs) -> None:
        """Initialise the model by forwarding all kwargs to the parent class.

        Parameters
        ----------
        **kwargs : dict
            Hyperparameter values forwarded to the parent sklearn wrapper.  See
            the associated schema class for available keys and their defaults.
        """
        super().__init__(**kwargs)
