from sklearn.ensemble import GradientBoostingClassifier as _GradientBoostingClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    none_type,
    optimizer_float_field,
    optimizer_int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class GradientBoostingClassifierSchema(BaseSchema):
    """Schema that configures the Gradient Boosting Classifier.

    Gradient Boosting is a sequential ensemble classification method that fits a new
    decision tree at each stage to the negative gradient of a differentiable loss
    function. The underlying implementation is
    ``sklearn.ensemble.GradientBoostingClassifier``.
    """

    loss: schema_field(
        enum_field(enum=["log_loss", "exponential"]),
        placeholder="log_loss",
        description=MultilingualString(
            en=(
                "The loss function to be optimized. 'log_loss' refers to binomial and "
                "multinomial deviance; 'exponential' is equivalent to AdaBoost."
            ),
            es=(
                "La función de pérdida a optimizar. 'log_loss' refiere a la desviación "
                "binomial y multinomial; 'exponential' es equivalente a AdaBoost."
            ),
            pt=(
                "A função de perda a ser otimizada. 'log_loss' refere-se ao desvio "
                "binomial e multinomial; 'exponential' é equivalente ao AdaBoost."
            ),
            de=(
                "Die zu optimierende Verlustfunktion. 'log_loss' bezieht sich auf "
                "binomiale und "
                "multinomiale Abweichung; 'exponential' ist äquivalent zu AdaBoost."
            ),
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
            de="Die Lernrate reduziert den Beitrag jedes Baums.",
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
            "upper_bound": 500,
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

    max_depth: schema_field(
        none_type(optimizer_int_field(ge=1)),
        placeholder=3,
        description=MultilingualString(
            en="Maximum depth of the individual regression estimators.",
            es="Profundidad máxima de los estimadores de regresión individuales.",
            pt="Profundidade máxima dos estimadores de regressão individuais.",
            de="Maximale Tiefe der einzelnen Regressions-Schätzer.",
        ),
        alias=MultilingualString(
            en="Max depth",
            es="Profundidad máxima",
            pt="Profundidade máxima",
            de="Maximale Tiefe",
        ),
    )  # type: ignore

    min_samples_split: schema_field(
        optimizer_int_field(ge=2),
        placeholder={
            "optimize": False,
            "fixed_value": 2,
            "lower_bound": 2,
            "upper_bound": 20,
        },
        description=MultilingualString(
            en="The minimum number of samples required to split an internal node.",
            es="El número mínimo de muestras requeridas para dividir un nodo interno.",
            pt="O número mínimo de amostras necessárias para dividir um nó interno.",
            de=(
                "Die Mindestanzahl von Stichproben, die zum Aufteilen eines internen "
                "Knotens erforderlich ist."
            ),
        ),
        alias=MultilingualString(
            en="Min samples split",
            es="Mínimas muestras de división",
            pt="Mínimas amostras de divisão",
            de="Minimale Aufteilungsstichproben",
        ),
    )  # type: ignore

    min_samples_leaf: schema_field(
        optimizer_int_field(ge=1),
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
            de=(
                "Die Mindestanzahl von Stichproben, die an einem Blattknoten "
                "erforderlich sind."
            ),
        ),
        alias=MultilingualString(
            en="Min samples leaf",
            es="Mínimas muestras para hoja",
            pt="Mínimas amostras para folha",
            de="Minimale Stichproben für Blatt",
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
                "The fraction of samples to be used for fitting each base learner. "
                "Values less than 1.0 lead to stochastic gradient boosting."
            ),
            es=(
                "La fracción de muestras usadas para ajustar cada aprendiz base. "
                "Valores menores a 1.0 llevan al gradient boosting estocástico."
            ),
            pt=(
                "A fração de amostras usadas para ajustar cada aprendiz base. "
                "Valores menores que 1.0 levam ao gradient boosting estocástico."
            ),
            de=(
                "Der Anteil der Stichproben, der für jeden Basislernenden verwendet "
                "wird. "
                "Werte unter 1.0 führen zu stochastischem Gradient Boosting."
            ),
        ),
        alias=MultilingualString(
            en="Subsample", es="Submuestreo", pt="Subamostra", de="Teilstichprobe"
        ),
    )  # type: ignore

    random_state: schema_field(
        none_type(optimizer_int_field(ge=0)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "The seed of the pseudo-random number generator. Pass an int for "
                "reproducible output, or None to not set a specific seed."
            ),
            es=(
                "La semilla del generador de números pseudoaleatorios. Pase un int "
                "para salida reproducible, o None para no fijar una semilla."
            ),
            pt=(
                "A semente do gerador de números pseudoaleatórios. Passe um int para "
                "saída reproduzível, ou None para não definir uma semente específica."
            ),
            de=(
                "Der Seed des Pseudozufallszahlengenerators. Übergeben Sie eine ganze "
                "Zahl für "
                "reproduzierbare Ausgaben oder None, um keinen bestimmten Seed "
                "festzulegen."
            ),
        ),
        alias=MultilingualString(
            en="Random state",
            es="Estado aleatorio",
            pt="Estado aleatório",
            de="Zufallszustand",
        ),
    )  # type: ignore


class GradientBoostingClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _GradientBoostingClassifier
):
    """Gradient boosting classifier that builds an ensemble of trees sequentially.

    Gradient Boosting builds an additive model stage by stage. At each stage a
    shallow decision tree is fitted to the negative gradient of the chosen loss
    function. A ``learning_rate`` shrinkage factor scales each tree's contribution,
    trading slower learning for better generalisation.

    Key hyperparameters include ``n_estimators``, ``learning_rate``, ``max_depth``,
    ``subsample``, and ``loss``. The implementation wraps scikit-learn's
    ``GradientBoostingClassifier``.

    References
    ----------
    - [1] Friedman, J.H. (2001). "Greedy function approximation: a gradient boosting
           machine." Annals of Statistics, 29(5), 1189-1232.
    - [2] https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html
    """

    SCHEMA = GradientBoostingClassifierSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Gradient Boosting Classifier",
        es="Clasificador Gradient Boosting",
        pt="Classificador por Gradient Boosting",
        de="Gradient-Boosting-Klassifikator",
    )
    DESCRIPTION: str = MultilingualString(
        en="Ensemble that builds trees sequentially to correct previous errors.",
        es=(
            "Conjunto que construye árboles secuencialmente para corregir "
            "errores previos."
        ),
        pt=(
            "Conjunto que constrói árvores sequencialmente para corrigir "
            "erros anteriores."
        ),
        de=(
            "Ensemble, das Bäume sequenziell aufbaut, um vorherige Fehler zu "
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
            Hyperparameter values forwarded to the parent sklearn wrapper.
        """
        super().__init__(**kwargs)
