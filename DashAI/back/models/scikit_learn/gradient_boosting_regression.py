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
        ),
        alias=MultilingualString(en="Loss", es="Pérdida", pt="Perda"),
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
        ),
        alias=MultilingualString(
            en="Learning rate", es="Tasa de aprendizaje", pt="Taxa de aprendizado"
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
        ),
        alias=MultilingualString(
            en="N estimators", es="N estimadores", pt="N estimadores"
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
        ),
        alias=MultilingualString(en="Subsample", es="Submuestreo", pt="Subamostra"),
    )  # type: ignore

    criterion: schema_field(
        enum_field(enum=["friedman_mse", "mse", "mae"]),
        placeholder="friedman_mse",
        description=MultilingualString(
            en="The function to measure the quality of a split.",
            es="La función para medir la calidad de una división.",
            pt="A função para medir a qualidade de uma divisão.",
        ),
        alias=MultilingualString(en="Criterion", es="Criterio", pt="Critério"),
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
        ),
        alias=MultilingualString(
            en="Min samples split",
            es="Mínimas muestras de división",
            pt="Mínimas amostras de divisão",
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
        ),
        alias=MultilingualString(
            en="Min samples leaf",
            es="Mínimas muestras para hoja",
            pt="Mínimas amostras para folha",
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
        ),
        alias=MultilingualString(
            en="Min weight fraction leaf",
            es="Fracción de peso mínima para hoja",
            pt="Fração mínima de peso para folha",
        ),
    )  # type: ignore

    max_depth: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=3,
        description=MultilingualString(
            en="The maximum depth of the individual regression estimators.",
            es="La profundidad máxima de los estimadores de regresión individuales.",
            pt="A profundidade máxima dos estimadores de regressão individuais.",
        ),
        alias=MultilingualString(
            en="Max depth", es="Profundidad máxima", pt="Profundidade máxima"
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
        ),
        alias=MultilingualString(
            en="Min impurity decrease",
            es="Disminución mínima de impureza",
            pt="Diminuição mínima de impureza",
        ),
    )  # type: ignore

    random_state: schema_field(
        union_type(optimizer_int_field(ge=0), none_type(int)),
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
        ),
        alias=MultilingualString(
            en="Random state", es="Estado aleatorio", pt="Estado aleatório"
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
        ),
        alias=MultilingualString(
            en="Max features",
            es="Máximas características",
            pt="Máximo de características",
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
        ),
        alias=MultilingualString(en="Alpha", es="Alfa", pt="Alfa"),
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
        ),
        alias=MultilingualString(en="Verbose", es="Verboso", pt="Verboso"),
    )  # type: ignore

    max_leaf_nodes: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en="Grow trees with max_leaf_nodes in best-first fashion.",
            es="Crecer árboles con max_leaf_nodes de manera best-first.",
            pt="Crescer árvores com max_leaf_nodes de maneira melhor-primeiro.",
        ),
        alias=MultilingualString(
            en="Max leaf nodes", es="Máximos nodos hoja", pt="Máximos nós folha"
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
        ),
        alias=MultilingualString(
            en="Warm start", es="Inicio en caliente", pt="Início a quente"
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
        ),
        alias=MultilingualString(
            en="Validation fraction",
            es="Fracción de validación",
            pt="Fração de validação",
        ),
    )  # type: ignore

    n_iter_no_change: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
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
        ),
        alias=MultilingualString(
            en="N iterations no change",
            es="N iteraciones sin cambio",
            pt="N iterações sem mudança",
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
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia", pt="Tolerância"),
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
        ),
        alias=MultilingualString(en="CCP alpha", es="CCP alfa", pt="CCP alfa"),
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
