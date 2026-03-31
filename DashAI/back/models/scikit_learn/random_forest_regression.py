from sklearn.ensemble import RandomForestRegressor as _RandomForestRegressor

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


class RandomForestRegressionSchema(BaseSchema):
    """Random Forest Regressor for DashAI."""

    n_estimators: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 100,
            "lower_bound": 10,
            "upper_bound": 1000,
        },
        description=MultilingualString(
            en="The number of trees in the forest.",
            es="El número de árboles en el bosque.",
        ),
        alias=MultilingualString(en="N estimators", es="N estimadores"),
    )  # type: ignore

    criterion: schema_field(
        enum_field(enum=["squared_error", "absolute_error", "poisson"]),
        placeholder="squared_error",
        description=MultilingualString(
            en="The function to measure the quality of a split.",
            es="La función para medir la calidad de una división.",
        ),
        alias=MultilingualString(en="Criterion", es="Criterio"),
    )  # type: ignore

    max_depth: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en="The maximum depth of the tree.",
            es="La profundidad máxima del árbol.",
        ),
        alias=MultilingualString(en="Max depth", es="Profundidad máxima"),
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
        ),
        alias=MultilingualString(
            en="Min samples split", es="Mínimas muestras de división"
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
                "required to be at a leaf node."
            ),
            es=(
                "La fracción ponderada mínima de la suma total de pesos "
                "requerida para estar en una hoja."
            ),
        ),
        alias=MultilingualString(
            en="Min weight fraction leaf", es="Fracción de peso mínima para hoja"
        ),
    )  # type: ignore

    max_features: schema_field(
        union_type(
            optimizer_float_field(gt=0.0, le=1.0),
            enum_field(enum=["auto", "sqrt", "log2", None]),
        ),
        placeholder="sqrt",
        description=MultilingualString(
            en=("The number of features to consider when looking for the best split."),
            es=(
                "El número de características a considerar al buscar la mejor división."
            ),
        ),
        alias=MultilingualString(en="Max features", es="Máximas características"),
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

    bootstrap: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en="Whether bootstrap samples are used when building trees.",
            es="Si se usan muestras bootstrap al construir árboles.",
        ),
        alias=MultilingualString(en="Bootstrap", es="Bootstrap"),
    )  # type: ignore

    oob_score: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en=(
                "Whether to use out-of-bag samples to estimate the "
                "generalization score."
            ),
            es=(
                "Si se usan muestras out-of-bag para estimar "
                "la puntuación de generalización."
            ),
        ),
        alias=MultilingualString(en="OOB score", es="Puntuación OOB"),
    )  # type: ignore

    n_jobs: schema_field(
        union_type(optimizer_int_field(ge=1), none_type(int)),
        placeholder=None,
        description=MultilingualString(
            en="The number of jobs to run in parallel for both fit and predict.",
            es="El número de trabajos a ejecutar en paralelo para fit y predict.",
        ),
        alias=MultilingualString(en="N jobs", es="N trabajos"),
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

    warm_start: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en=(
                "When set to True, reuse the solution of the previous "
                "call to fit and add more estimators to the ensemble."
            ),
            es=(
                "Cuando se establece en True, reutiliza la solución de la llamada "
                "anterior a fit y agrega más estimadores al conjunto."
            ),
        ),
        alias=MultilingualString(en="Warm start", es="Inicio en caliente"),
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

    max_samples: schema_field(
        union_type(optimizer_float_field(gt=0.0, le=1.0), none_type(float)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "If bootstrap is True, the number of samples to draw from "
                "X to train each base estimator."
            ),
            es=(
                "Si bootstrap es True, el número de muestras a tomar de "
                "X para entrenar cada estimador base."
            ),
        ),
        alias=MultilingualString(en="Max samples", es="Máximas muestras"),
    )  # type: ignore


class RandomForestRegression(
    RegressionModel, SklearnLikeRegressor, _RandomForestRegressor
):
    """Random forest regressor that averages predictions from multiple decision trees.

    Reduces overfitting and variance compared to a single tree by combining the output
    of many randomized trees. Wraps scikit-learn's ``RandomForestRegressor``.
    """

    SCHEMA = RandomForestRegressionSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Random Forest",
        es="Bosque Aleatorio",
    )
    DESCRIPTION: str = MultilingualString(
        en="An ensemble learning method using multiple decision trees for regression.",
        es=(
            "Un método de aprendizaje en conjunto usando múltiples árboles de "
            "decisión para regresión."
        ),
    )
    COLOR: str = "#FF8A65"
    ICON: str = "Forest"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
