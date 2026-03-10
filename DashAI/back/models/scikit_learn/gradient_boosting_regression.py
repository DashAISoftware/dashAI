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
    """Gradient Boosting for regression."""

    loss: schema_field(
        enum_field(enum=["squared_error", "absolute_error", "huber", "quantile"]),
        placeholder="squared_error",
        description=MultilingualString(
            en="Loss function to be optimized.",
            es="Función de pérdida a optimizar.",
        ),
        alias=MultilingualString(en="Loss", es="Pérdida"),
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
        ),
        alias=MultilingualString(en="Learning rate", es="Tasa de aprendizaje"),
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
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
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
        ),
        alias=MultilingualString(en="Subsample", es="Submuestreo"),
    )  # type: ignore

    criterion: schema_field(
        enum_field(enum=["friedman_mse", "mse", "mae"]),
        placeholder="friedman_mse",
        description=MultilingualString(
            en="The function to measure the quality of a split.",
            es="La función para medir la calidad de una división.",
        ),
        alias=MultilingualString(en="Criterion", es="Criterio"),
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
        ),
        alias=MultilingualString(
            en="Min samples split", es="Mínimas muestras de división"
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
        ),
        alias=MultilingualString(
            en="Min samples leaf", es="Mínimas muestras para hoja"
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
        ),
        alias=MultilingualString(
            en="Min weight fraction leaf", es="Fracción de peso mínima para hoja"
        ),
    )  # type: ignore

    max_depth: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=3,
        description=MultilingualString(
            en="The maximum depth of the individual regression estimators.",
            es="La profundidad máxima de los estimadores de regresión individuales.",
        ),
        alias=MultilingualString(en="Max depth", es="Profundidad máxima"),
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
        ),
        alias=MultilingualString(
            en="Min impurity decrease", es="Disminución mínima de impureza"
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
        ),
        alias=MultilingualString(en="Random state", es="Estado aleatorio"),
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
        ),
        alias=MultilingualString(en="Max features", es="Máximas características"),
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
        ),
        alias=MultilingualString(en="Alpha", es="Alfa"),
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
        ),
        alias=MultilingualString(en="Verbose", es="Verboso"),
    )  # type: ignore

    max_leaf_nodes: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en="Grow trees with max_leaf_nodes in best-first fashion.",
            es="Crecer árboles con max_leaf_nodes de manera best-first.",
        ),
        alias=MultilingualString(en="Max leaf nodes", es="Máximos nodos hoja"),
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
        ),
        alias=MultilingualString(en="Warm start", es="Inicio en caliente"),
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
        ),
        alias=MultilingualString(en="Validation fraction", es="Fracción de validación"),
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
        ),
        alias=MultilingualString(
            en="N iterations no change", es="N iteraciones sin cambio"
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
        ),
        alias=MultilingualString(en="Tolerance", es="Tolerancia"),
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
        ),
        alias=MultilingualString(en="CCP alpha", es="CCP alfa"),
    )  # type: ignore


class GradientBoostingR(RegressionModel, SklearnLikeRegressor, _GBRegressor):
    """Scikit-learn's Ridge Regression wrapper for DashAI."""

    SCHEMA = GradientBoostingRSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Gradient Boosting Regression",
        es="Regresión Gradient Boosting",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Ensemble method that builds trees sequentially to correct previous errors."
        ),
        es=(
            "Método de conjunto que construye árboles secuencialmente para corregir "
            "errores anteriores."
        ),
    )
    COLOR: str = "#4CAF50"
    ICON: str = "AutoGraph"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
