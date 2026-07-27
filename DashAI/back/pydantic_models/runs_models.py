from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class OptimizerIntParam(BaseModel):
    optimize: bool = Field(
        ...,
        description=(
            "Este campo debe ser True en caso de que se ocupe el optimizador "
            "OptunaOptimizerParams o HyperOptOptimizerParams. En este caso se "
            "establecerá como posible valor optimizado del campo uno que esté "
            "entre los dos limites"
        ),
    )
    fixed_value: int = Field(description="Valor usado cuando optimize=False")
    lower_bound: int = Field(description="Limite inferior cuando optimize=True")
    upper_bound: int = Field(description="Limite superior cuando optimize=True")


class OptimizerFloatParam(BaseModel):
    optimize: bool = Field(
        ...,
        description=(
            "Este campo debe ser True en caso de que se ocupe el optimizador "
            "OptunaOptimizerParams o HyperOptOptimizerParams. En este caso se "
            "establecerá como posible valor optimizado del campo uno que esté "
            "entre los dos limites"
        ),
    )
    fixed_value: float = Field(description="Valor usado cuando optimize=False")
    lower_bound: float = Field(description="Limite inferior cuando optimize=True")
    upper_bound: float = Field(description="Limite superior cuando optimize=True")


class OptunaOptimizerParams(BaseModel):
    n_trials: int = Field(
        10,
        gt=0,
        description="La cantidad de pruebas por estudio. Debe ser un entero positivo.",
    )
    sampler: Literal[
        "TPESampler",
        "CmaEsSampler",
        "RandomSampler",
        "GridSampler",
        "GPSampler",
        "NSGAIISampler",
        "QMCSampler",
    ] = Field(
        default="TPESampler",
        description=(
            "El algoritmo de muestreo a usar para la optimización de hiperparámetros. "
            "Diferentes muestreadores usan diferentes estrategias para explorar el "
            "espacio de hiperparámetros."
        ),
    )
    pruner: Literal["MedianPruner", "None"] = Field(
        default="None",
        description=(
            "El podador a usar para detener tempranamente pruebas poco prometedoras. "
            "'MedianPruner' detiene pruebas bajo la mediana.'None' desactiva la poda."
        ),
    )


class HyperOptOptimizerParams(BaseModel):
    n_trials: int = Field(
        default=10, gt=0, description="Número de pruebas de optimización a ejecutar"
    )
    sampler: Literal["tpe", "rand"] = Field(
        "tpe",
        description=(
            "El algoritmo de muestreo a usar para la optimización de hiperparámetros. "
            "Debe ser 'tpe' (Tree-structured Parzen Estimator) o 'rand' (Aleatorio)."
        ),
    )


class LoggingMixin(BaseModel):
    log_train_every_n_epochs: Optional[int] = Field(
        1,
        description=(
            "Registrar métricas del split de entrenamiento cada n épocas. Si es None, "
            "no registrará por época."
        ),
    )
    log_train_every_n_steps: Optional[int] = Field(
        None,
        description=(
            "Registrar métricas del split de entrenamiento cada n pasos. Si es None, "
            "no registrará por paso."
        ),
    )
    log_validation_every_n_epochs: Optional[int] = Field(
        1,
        description=(
            "Registrar métricas del split de validación cada n épocas. Si es None, "
            "no registrará por época."
        ),
    )
    log_validation_every_n_steps: Optional[int] = Field(
        None,
        description=(
            "Registrar métricas del split de validación cada n pasos. Si es None, "
            "no registrará por paso."
        ),
    )


class BaseSequenceModelParams(LoggingMixin):
    num_train_epochs: int = Field(
        default=1, ge=1, description="Número total de épocas de entrenamiento"
    )
    batch_size: int = Field(
        default=16,
        ge=1,
        description="Tamaño del lote por núcleo GPU/TPU/CPU para entrenamiento.",
    )
    learning_rate: float = Field(
        default=3e-5,
        ge=0.0,
        description="Tasa de aprendizaje inicial para el optimizer AdamW",
    )
    device: Literal["CPU", "GPU"] = Field(
        default="CPU",
        description=(
            "Hardware en el que se ejecuta el entrenamiento. "
            "Si está disponible, se recomienda GPU por razones de eficiencia. "
            "De lo contrario, use CPU."
        ),
    )
    weight_decay: float = Field(
        default=0.01,
        ge=0.0,
        description=(
            "Weight decay es una técnica de regularización usada en el entrenamiento "
            "de redes neuronales para prevenir sobreajuste. En el contexto del "
            "optimizador AdamW, el parámetro 'weight_decay' es la tasa a la cual los "
            "pesos de todas las capas se reducen durante el entrenamiento, siempre "
            "que esta tasa no sea cero."
        ),
    )


class SVCParams(BaseModel):
    C: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=0.0, upper_bound=10.0
        ),
        description=(
            "El parámetro 'C' es un parámetro de regularización. La fuerza de "
            "la regularización es inversamente proporcional a C"
        ),
    )
    coef0: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=1.0, upper_bound=10.0
        ),
        description=(
            "El parámetro 'coef0' es un término independiente en la función del kernel."
            "Solo es significativo para los kernels poly y sigmoid."
        ),
    )
    degree: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=1.0, upper_bound=10.0
        ),
        description=(
            "El parámetro 'grado' solo es significativo para el kernel 'poly'."
        ),
    )
    gamma: Literal["scale", "auto"] = Field(
        "scale",
        description="Coeficiente para los kernels 'rbf', 'poly' y 'sigmoid'.",
    )
    kernel: Literal["linear", "poly", "rbf", "sigmoid"] = Field(
        "rbf", description="Tipo de kernel usado en el algoritmo"
    )
    max_iter: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=-1, lower_bound=-1, upper_bound=10
        ),
        description=(
            "El parámetro 'max_iter' determina el límite de iteraciones para el "
            "solucionador. Debe ser un entero positivo o -1 para indicar sin límite."
        ),
    )
    shrinking: bool = Field(
        True,
        description=(
            "El parámetro 'reducción' determina si se utiliza una heurística "
            "de reducción."
        ),
    )
    tol: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=1.0, upper_bound=10.0
        ),
        description="Tolerancia para el criterio de detención",
    )


class DecisionTreeClassifierParams(BaseModel):
    criterion: Literal["entropy", "gini", "log_loss"] = Field(
        "entropy",
        description=(
            "La función para medir la calidad de una división. Los criterios "
            "soportados son 'gini' para la impureza de Gini y 'log_loss' y "
            "'entropy' para la ganancia de información de Shannon."
        ),
    )
    max_depth: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=10),
        description=(
            "La profundidad máxima del árbol. Si es None, los nodos se expanden hasta "
            "que todas las hojas sean puras o hasta que todas las hojas contengan "
            "menos de min_samples_split muestras."
        ),
    )
    min_samples_split: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=5),
        description=(
            "El número mínimo de muestras requeridas para dividir un nodo interno."
        ),
    )
    min_samples_leaf: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=5),
        description="El número mínimo de muestras requeridas para estar en una hoja.",
    )
    max_features: Optional[Union[Literal["sqrt", "log2"], float]] = Field(
        None,
        description=(
            "El número de características a considerar al buscar la mejor división. "
            "Si es float, entonces max_features es un porcentaje del "
            "total de características."
        ),
    )


class DummyClassifierParams(BaseModel):
    strategy: Literal["most_frequent", "prior", "stratified", "uniform"] = Field(
        default="prior", description="Estrategia a utilizar para generar predicciones"
    )


class HistGradientBoostingClassifierParams(BaseModel):
    learning_rate: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.1, lower_bound=0.1, upper_bound=1.0
        ),
        description=(
            "La tasa de aprendizaje, también conocida como shrinkage. Se utiliza como "
            "factor multiplicativo para los valores de las hojas. Use 1 para "
            "no aplicar shrinkage."
        ),
    )
    max_iter: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=100, lower_bound=100, upper_bound=250
        ),
        description=(
            "El número máximo de iteraciones del proceso de boosting, "
            "es decir, el número máximo de árboles para clasificación binaria."
        ),
    )
    max_depth: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=10),
        description=(
            "La profundidad máxima de cada árbol. La profundidad es el número de "
            "aristas desde la raíz hasta la hoja más profunda. Por defecto, la "
            "profundidad no está restringida."
        ),
    )
    max_leaf_nodes: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=31, lower_bound=10, upper_bound=40
        ),
        description=(
            "El número máximo de hojas para cada árbol. Debe ser estrictamente "
            "mayor que 1. Si es None, no hay límite máximo."
        ),
    )
    min_samples_leaf: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=20, lower_bound=2, upper_bound=25
        ),
        description=("El número mínimo de muestras requeridas para estar en una hoja."),
    )
    l2_regularization: OptimizerFloatParam = Field(
        default=OptimizerFloatParam(
            optimize=False, fixed_value=0.0, lower_bound=0.0, upper_bound=1.0
        ),
        description=(
            "El parámetro de regularización L2. Use 0 para no aplicar regularización."
        ),
    )


class KNeighborsClassifierParams(BaseModel):
    n_neighbors: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=5, lower_bound=5, upper_bound=10),
        description=(
            "Es el número de vecinos a considerar en cada entrada "
            "para la clasificación."
        ),
    )
    weights: Literal["uniform", "distance"] = Field(
        "uniform", description="El parámetro debe ser 'uniform' o 'distance'."
    )
    algorithm: Literal["auto", "ball_tree", "kd_tree", "brute"] = Field(
        "auto",
        description="El parámetro debe ser 'auto', 'ball_tree', 'kd_tree' o 'brute'.",
    )


class LogisticRegressionParams(BaseModel):
    penalty: Literal["l2", "l1", "elasticnet"] = Field(
        "l2", description="Especifica la norma de la penalización"
    )
    tol: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.0, lower_bound=0.0, upper_bound=5.0
        ),
        description="Tolerancia para el criterio de detención",
    )
    C: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=1.0, upper_bound=7.0
        ),
        description=(
            "Inverso de la fuerza de regularización, valores más pequeños "
            "especifican una regularización más fuerte. Debe ser un número positivo."
        ),
    )
    max_iter: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=100, lower_bound=50, upper_bound=250
        ),
        description=(
            "Número máximo de iteraciones para que los solucionadores converjan."
        ),
    )


class RandomForestClassifierParams(BaseModel):
    n_estimators: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=100, lower_bound=50, upper_bound=200
        ),
        description=(
            "El parámetro 'n_estimators' corresponde al número de árboles "
            "de decisión. Debe ser un entero mayor o igual a 1."
        ),
    )
    max_depth: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=2, lower_bound=2, upper_bound=10),
        description=(
            "El parámetro corresponde a la profundidad máxima del árbol. "
            "Debe ser un entero mayor o igual a 1."
        ),
    )
    min_samples_split: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=2, lower_bound=2, upper_bound=10),
        description=(
            "Este parámetro establece el número mínimo de muestras requeridas "
            "para dividir un nodo interno. Debe ser un número mayor o igual a 2."
        ),
    )
    min_samples_leaf: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=10),
        description=(
            "Este parámetro establece el número mínimo de muestras requeridas "
            "para estar en una hoja. Debe ser un número mayor o igual a 1."
        ),
    )
    max_leaf_nodes: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=2, lower_bound=2, upper_bound=10),
        description=(
            "Este parámetro establece el número máximo de nodos hoja. Debe ser un"
            "entero mayor o igual a 2."
        ),
    )
    random_state: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=0, lower_bound=0, upper_bound=10),
        description="Este parámetro debe ser un entero mayor o igual a 0.",
    )


class GradientBoostingRParams(BaseModel):
    loss: Literal["squared_error", "absolute_error", "huber", "quantile"] = Field(
        "squared_error", description="Función de pérdida a optimizar. "
    )
    learning_rate: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.1, lower_bound=0.01, upper_bound=1.0
        ),
        description="La tasa de aprendizaje reduce la contribución de cada árbol.",
    )
    n_estimators: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=100, lower_bound=10, upper_bound=1000
        ),
        description=(
            "El número de etapas de boosting a ejecutar.  Debe ser mayor o igual a 1."
        ),
    )
    subsample: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=0.1, upper_bound=1.0
        ),
        description=(
            "La fracción de muestras a usar para ajustar los aprendices "
            "base individuales. Debe ser un valor mayor o igual a 0.1 y "
            "menor o igual a 1"
        ),
    )
    criterion: Literal["friedman_mse", "mse", "mae"] = Field(
        "friedman_mse", description="La función para medir la calidad de una división."
    )
    min_samples_split: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.5, lower_bound=0.1, upper_bound=1.0
        ),
        description=(
            "El número mínimo de muestras requeridas para dividir un nodo interno."
        ),
    )
    min_samples_leaf: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1, lower_bound=0.01, upper_bound=0.5
        ),
        description=(
            "El número mínimo de muestras requeridas para estar en una hoja.  "
            "Si se decide optimizar el campo, el limite inferior debe ser mayor "
            "estricto que 0.0 y menor estricto que 0.5.  Si no se ocupa optimizador, "
            "el valor fijo debe ser mayor o igual 1."
        ),
    )
    min_weight_fraction_leaf: float = Field(
        0.0,
        description=(
            "La fracción ponderada mínima de la suma total de pesos "
            "(de todas las muestras de entrada) requerida para estar en una hoja."
        ),
    )
    max_depth: Optional[OptimizerIntParam] = Field(
        None,
        description=(
            "La profundidad máxima de los estimadores de regresión individuales."
        ),
    )
    min_impurity_decrease: float = Field(
        0.0,
        description=(
            "Un nodo se dividirá si esta división induce una disminución "
            "de la impureza mayor o igual a este valor."
        ),
    )
    random_state: Optional[OptimizerIntParam] = Field(
        None,
        description=(
            "La semilla del generador de números pseudoaleatorios a usar al "
            "mezclar los datos."
        ),
    )
    max_features: Optional[Union[OptimizerFloatParam, Literal["sqrt", "log2"]]] = Field(
        None,
        description=(
            "El número de características a considerar al buscar la mejor división."
        ),
    )
    alpha: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.9, lower_bound=0.1, upper_bound=1.0
        ),
        description=(
            "El alfa-cuantil de la función de pérdida de Huber y la función "
            "de pérdida cuantil."
        ),
    )
    verbose: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=0, lower_bound=0, upper_bound=100
        ),
        description="Habilitar salida detallada.",
    )
    max_leaf_nodes: Optional[OptimizerIntParam] = Field(
        None, description="Crecer árboles con max_leaf_nodes de manera best-first."
    )
    warm_start: bool = Field(
        False,
        description=(
            "Cuando se establece en True, reutiliza la solución de la llamada "
            "anterior a fit y agrega más estimadores al conjunto."
        ),
    )
    validation_fraction: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.1, lower_bound=0.05, upper_bound=0.5
        ),
        description=(
            "La proporción de datos de entrenamiento a reservar como conjunto "
            "de validación para detención temprana."
        ),
    )
    n_iter_no_change: Optional[OptimizerIntParam] = Field(
        None,
        description=(
            "El número de iteraciones sin mejora a esperar antes de "
            "detener el entrenamiento."
        ),
    )
    tol: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.0001, lower_bound=1e-6, upper_bound=0.1
        ),
        description="Tolerancia para la detención temprana.",
    )
    ccp_alpha: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.0, lower_bound=0.0, upper_bound=1.0
        ),
        description=(
            "Parámetro de complejidad usado para poda de costo-complejidad mínima."
        ),
    )


class MLPRegressionParams(LoggingMixin):
    hidden_size: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=5, lower_bound=1, upper_bound=15),
        description="Número de neuronas en la capa oculta",
    )
    activation: Literal["relu", "tanh", "sigmoid", "identity"] = Field(
        "relu", description="Función de activación"
    )
    learning_rate: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.001, lower_bound=1e-6, upper_bound=1.0
        ),
        description="Tasa de aprendizaje inicial para el optimizador.",
    )
    epochs: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=5, lower_bound=1, upper_bound=15),
        description=(
            "Número total de pasadas de entrenamiento sobre el conjunto de datos."
        ),
    )
    batch_size: Optional[int] = Field(
        32,
        description=(
            "Número de muestras por actualización de gradiente "
            "durante el entrenamiento. Si es mayor que el tamaño del "
            "dataset o None, se usa el dataset completo."
        ),
    )
    device: Literal["CPU", "GPU"] = Field(
        default="CPU", description="Dispositivo de hardware usado para entrenamiento"
    )


class RandomForestRegressionParams(BaseModel):
    n_estimators: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=100, lower_bound=10, upper_bound=1000
        ),
        description="Número de árboles en el bosque",
    )
    criterion: Literal["squared_error", "absolute_error", "poisson"] = Field(
        "squared_error", description="Función para medir la calidad de la división"
    )
    max_depth: Optional[int] = Field(
        None, description="Profundidad máxima de cada árbol (None = sin límite)"
    )
    min_samples_split: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=2, lower_bound=2, upper_bound=20),
        description=(
            "El número mínimo de muestras requeridas para dividir un nodo interno."
        ),
    )
    min_samples_leaf: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=20),
        description=("El número mínimo de muestras requeridas para estar en una hoja."),
    )
    min_weight_fraction_leaf: float = Field(
        0.0,
        description=(
            "La fracción ponderada mínima de la suma total de pesos requerida "
            "para estar en una hoja."
        ),
    )
    max_features: Optional[Literal["auto", "sqrt", "log2"]] = Field(
        "sqrt",
        description=(
            "El número de características a considerar al buscar la mejor división."
        ),
    )
    max_leaf_nodes: Optional[int] = Field(
        None, description="Crecer árboles con max_leaf_nodes de manera best-first."
    )
    min_impurity_decrease: float = Field(
        0.0,
        description=(
            "Un nodo se dividirá si esta división induce una disminución "
            "de la impureza mayor o igual a este valor."
        ),
    )
    bootstrap: bool = Field(
        True, description="Si se usan muestras bootstrap al construir árboles."
    )
    oob_score: bool = Field(
        False,
        description=(
            "Si se usan muestras out-of-bag para estimar la puntuación "
            "de generalización."
        ),
    )
    n_jobs: Optional[int] = Field(
        None,
        description="El número de trabajos a ejecutar en paralelo para fit y predict.",
    )
    random_state: Optional[int] = Field(
        None,
        description=(
            "La semilla del generador de números pseudoaleatorios a usar al "
            "mezclar los datos."
        ),
    )
    warm_start: bool = Field(
        False,
        description=(
            "Cuando se establece en True, reutiliza la solución de la "
            "llamada anterior a fit y agrega más estimadores al conjunto."
        ),
    )
    ccp_alpha: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.0, lower_bound=0.0, upper_bound=0.1
        ),
        description=(
            "Parámetro de complejidad usado para poda de "
            "costo-complejidad mínima.  Mayor o igual a 0.0"
        ),
    )
    max_samples: Optional[float] = Field(
        None,
        description=(
            "Si bootstrap es True, el número de muestras a tomar de X para "
            "entrenar cada estimador base."
        ),
    )


class RidgeRegressionParams(BaseModel):
    alpha: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=10),
        description=(
            "Fuerza de regularización; debe ser un float positivo. Valores "
            "más grandes especifican una regularización más fuerte."
        ),
    )
    fit_intercept: bool = Field(
        True,
        description=(
            "Si se debe calcular el intercepto para este modelo. Si se establece "
            "en False, no se usará intercepto en los cálculos "
            "(ej., se espera que los datos estén centrados)."
        ),
    )
    copy_X: bool = Field(  # noqa: N815
        True, description="Si es True, X será copiado; si no, puede ser sobrescrito."
    )
    max_iter: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=100, lower_bound=10, upper_bound=10000
        ),
        description=(
            "Número máximo de iteraciones para el solucionador de gradiente conjugado."
        ),
    )
    tol: OptimizerFloatParam = Field(
        default=OptimizerFloatParam(
            optimize=False, fixed_value=0.001, lower_bound=1e-5, upper_bound=0.1
        ),
        description="Precisión de la solución",
    )
    solver: Literal["auto", "svd", "cholesky", "lsqr", "sparse_cg", "sag", "saga"] = (
        Field(
            "auto",
            description=(
                "Solucionador a usar en el cálculo. 'auto' elige el "
                "solucionador automáticamente basado en el tipo de datos."
            ),
        )
    )
    positive: bool = Field(
        False,
        description=(
            "Cuando se establece en True, fuerza los coeficientes a ser positivos."
        ),
    )
    random_state: Optional[OptimizerIntParam] = Field(
        None,
        description=(
            "La semilla del generador de números pseudoaleatorios a usar "
            "al mezclar los datos. Pase un int para salida reproducible entre "
            "múltiples llamadas, o None para no establecer una semilla específica."
        ),
    )


class LinearSVRParams(BaseModel):
    epsilon: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.0, lower_bound=0.0, upper_bound=1.0
        ),
        description=(
            "Parámetro epsilon que especifica el tubo-epsilon dentro del cual "
            "no se asocia ninguna penalización."
        ),
    )
    tol: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=0.0001, lower_bound=1e-5, upper_bound=0.1
        ),
        description="Tolerancia para el criterio de detención",
    )
    C: OptimizerIntParam = Field(
        OptimizerIntParam(optimize=False, fixed_value=1, lower_bound=1, upper_bound=10),
        description=(
            "Parámetro de regularización. La fuerza de la regularización "
            "inversamente proporcional a C."
        ),
    )
    loss: Literal["epsilon_insensitive", "squared_epsilon_insensitive"] = Field(
        "epsilon_insensitive",
        description=(
            "Especifica la función de pérdida. 'epsilon_insensitive' es "
            "la pérdida estándar de SVR."
        ),
    )
    fit_intercept: bool = Field(
        True, description="Si se calcula el intercepto del modelo"
    )
    intercept_scaling: OptimizerFloatParam = Field(
        OptimizerFloatParam(
            optimize=False, fixed_value=1.0, lower_bound=1.0, upper_bound=10.0
        ),
        description=(
            "Cuando fit_intercept es True, el vector de instancia x se convierte en "
            "[x, self.intercept_scaling] en el problema primal."
        ),
    )
    dual: bool = Field(
        True,
        description=(
            "Selecciona el algoritmo para resolver el problema de "
            "optimización dual o primal."
        ),
    )
    verbose: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=0, lower_bound=0, upper_bound=100
        ),
        description=(
            "Habilitar salida detallada. Note que esta configuración "
            "aprovecha una configuración de tiempo de ejecución por proceso en libsvm."
        ),
    )
    random_state: Optional[OptimizerIntParam] = Field(
        None,
        description=(
            "La semilla del generador de números pseudoaleatorios a usar al "
            "mezclar los datos."
        ),
    )
    max_iter: OptimizerIntParam = Field(
        OptimizerIntParam(
            optimize=False, fixed_value=1000, lower_bound=100, upper_bound=10000
        ),
        description="El número máximo de iteraciones a ejecutar.",
    )


class LinearRegressionParams(BaseModel):
    fit_intercept: bool = Field(
        True,
        description=(
            "Si se debe calcular el intercepto para este modelo. Si se establece "
            "en False, no se usará intercepto en los cálculos "
            "(ej., se espera que los datos estén centrados)."
        ),
    )
    copy_X: bool = Field(  # noqa: N815
        True, description="Si es True, X será copiado; si no, puede ser sobrescrito."
    )
    n_jobs: Optional[int] = Field(
        None,
        description=(
            "El número de trabajos a usar para el cálculo. None significa 1 "
            "trabajo, mientras que -1 significa usar todos los procesadores."
        ),
    )
    positive: bool = Field(
        False,
        description=(
            "Cuando se establece en True, fuerza los coeficientes a ser positivos."
        ),
    )


class DistilBertTransformerParams(BaseSequenceModelParams):
    pass


class ModernBertTransformerParams(BaseSequenceModelParams):
    pass


class DebertaV3TransformerParams(BaseSequenceModelParams):
    pass


class ComponentConfig(BaseModel):
    component: Literal[
        "SVC",
        "DecisionTreeClassifier",
        "DummyClassifier",
        "HistGradientBoostingClassifier",
        "KNeighborsClassifier",
        "LogisticRegression",
        "RandomForestClassifier",
    ] = Field(
        ...,
        description=(
            "Nombre de clase del modelo con la que se quiere realizar la "
            "tarea de clasificación de texto bolsa de palabras."
        ),
    )
    params: Union[
        SVCParams,
        DecisionTreeClassifierParams,
        DummyClassifierParams,
        HistGradientBoostingClassifierParams,
        KNeighborsClassifierParams,
        LogisticRegressionParams,
        RandomForestClassifierParams,
    ] = Field(
        ...,
        description=(
            "Hiperparámetros para el modelo elegido para realizar la "
            "tarea de clasificación de texto bolsa de palabras. La estructura depende "
            "de model_name — use la clase Params correspondiente."
        ),
    )


class TabularClassifierParams(BaseModel):
    comp: ComponentConfig


class TabularClassifierModel(BaseModel):
    component: Literal["TabularClassificationModel"]
    params: TabularClassifierParams


class TabularClassifierField(BaseModel):
    properties: TabularClassifierModel


class BagOfWordsTextClassificationParams(BaseModel):
    tabular_classifier: TabularClassifierField = Field(
        ...,
        description=(
            "Configuración del modelo a usar para la tarea de clasificación "
            "de texto bolsa de palabras."
        ),
    )
    ngram_min_n: int = Field(
        default=1, ge=1, description="Límite inferior del rango de n-gramas"
    )
    ngram_max_n: int = Field(
        default=1, ge=1, description="Límite superior del rango de n-gramas"
    )


class BaseTranslationParams(BaseSequenceModelParams):
    batch_size: int = Field(
        default=4, ge=1, description="Tamaño del lote por dispositivo GPU/CPU"
    )
    learning_rate: float = Field(
        default=2e-5,
        ge=0.0,
        description="Tasa de aprendizaje inicial para el optimizer AdamW",
    )


class OpusMtEnESTransformerParams(BaseTranslationParams):
    pass


class OpusMtEsEnTransformerParams(BaseTranslationParams):
    pass


class NllbTransformerParams(BaseTranslationParams):
    source_language: str = Field(
        default="spa_Latn",
        description=(
            "Código de idioma de origen para el tokenizer NLLB. "
            "Ejemplo: spa_Latn para español."
        ),
    )
    target_language: str = Field(
        default="eng_Latn",
        description=(
            "Código de idioma destino NLLB en formato <iso639>_<Script>. "
            "Ej: 'eng_Latn' para inglés, 'fra_Latn' para francés."
        ),
    )


MODEL_NAMES = Literal[
    # Clasificación tabular
    "SVC",
    "DecisionTreeClassifier",
    "DummyClassifier",
    "HistGradientBoostingClassifier",
    "KNeighborsClassifier",
    "LogisticRegression",
    # Regresión
    "RandomForestClassifier",
    "GradientBoostingR",
    "MLPRegression",
    "RandomForestRegression",
    "RidgeRegression",
    "LinearSVR",
    "LinearRegression",
    # Clasificación de texto
    "DistilBertTransformer",
    "ModernBertTransformer",
    "DebertaV3Transformer",
    "BagOfWordsTextClassificationModel",
    # Traducción
    "OpusMtEnESTransformer",
    "OpusMtEsENTransformer",
    "NllbTransformer",
]

GOAL_METRIC = Literal[
    "Accuracy",
    "CohenKappa",
    "F1",
    "HammingDistance",
    "LogLoss",
    "Precision",
    "Recall",
    "ROCAUC",
    "ExplainedVariance",
    "MAE",
    "MedianAbsoluteError",
    "MSE",
    "R2",
    "RMSE",
    "",
]

MODEL_PARAMS = Union[
    SVCParams,
    DecisionTreeClassifierParams,
    DummyClassifierParams,
    HistGradientBoostingClassifierParams,
    KNeighborsClassifierParams,
    LogisticRegressionParams,
    RandomForestClassifierParams,
    GradientBoostingRParams,
    MLPRegressionParams,
    RandomForestRegressionParams,
    RidgeRegressionParams,
    LinearSVRParams,
    LinearRegressionParams,
    DistilBertTransformerParams,
    ModernBertTransformerParams,
    DebertaV3TransformerParams,
    BagOfWordsTextClassificationParams,
    OpusMtEnESTransformerParams,
    OpusMtEsEnTransformerParams,
    NllbTransformerParams,
]


class AddModelParams(BaseModel):
    model_session_id: int = Field(
        ..., description="ID de la sesión de modelo a la que se agregará el modelo"
    )
    model_name: MODEL_NAMES = Field(
        ...,
        description=(
            "Nombre de clase del modelo a agregar. Determina la estructura "
            "requerida del campo 'parameters'."
        ),
    )
    run_name: str = Field(
        ...,
        description="Nombre identificador único para este modelo dentro de la sesión",
    )
    parameters: MODEL_PARAMS = Field(
        ...,
        description=(
            "Hiperparámetros para el modelo elegido. La estructura depende "
            "de model_name — use la clase Params correspondiente."
        ),
    )
    optimizer_name: Literal["OptunaOptimizer", "HyperOptOptimizer", ""] = Field(
        ...,
        description=(
            "Optimizer de hiperparámetros a usar.  Dejar vacío en caso "
            "de no usar optimizador."
        ),
    )
    optimizer_parameters: Union[
        OptunaOptimizerParams, HyperOptOptimizerParams, None
    ] = Field(
        ...,
        description=(
            "Configuración del optimizer de hiperparámetros.  Dejar como None "
            "en caso de no requerir ocupar optimizador."
        ),
    )
    goal_metric: GOAL_METRIC = Field(
        ...,
        description=(
            "Nombre de la métrica objetivo para guiar la optimización de "
            "hiperparámetros. Dejar un string vacío '' si no se ocupa un "
            "optimizador de hiperparámetros. Completar con alguno de los "
            "valores en caso de especificar optimizador."
        ),
    )
    description: str = Field(
        default="", description="Descripción opcional para este modelo"
    )

    @model_validator(mode="after")
    def check_params_match_model(self):
        expected_class = {
            "SVC": SVCParams,
            "DecisionTreeClassifier": DecisionTreeClassifierParams,
            "DummyClassifier": DummyClassifierParams,
            "HistGradientBoostingClassifier": HistGradientBoostingClassifierParams,
            "KNeighborsClassifier": KNeighborsClassifierParams,
            "LogisticRegression": LogisticRegressionParams,
            "RandomForestClassifier": RandomForestClassifierParams,
            "GradientBoostingR": GradientBoostingRParams,
            "MLPRegression": MLPRegressionParams,
            "RandomForestRegression": RandomForestRegressionParams,
            "RidgeRegression": RidgeRegressionParams,
            "LinearSVR": LinearSVRParams,
            "LinearRegression": LinearRegressionParams,
            "DistilBertTransformer": DistilBertTransformerParams,
            "ModernBertTransformer": ModernBertTransformerParams,
            "DebertaV3Transformer": DebertaV3TransformerParams,
            "BagOfWordsTextClassificationModel": BagOfWordsTextClassificationParams,
            "OpusMtEnESTransformer": OpusMtEnESTransformerParams,
            "OpusMtEsENTransformer": OpusMtEsEnTransformerParams,
            "NllbTransformer": NllbTransformerParams,
        }[self.model_name]

        if isinstance(self.parameters, expected_class):
            return self

        try:
            data = self.parameters.model_dump()
            new_params = expected_class.model_validate(data)
            self.parameters = new_params
            return self
        except Exception as e:
            raise ValueError(
                f"Los parámetros proporcionados no son válidos para el modelo "
                f"{self.model_name}. Se recibió tipo {type(self.parameters).__name__} "
                f"y no se pudo convertir a {expected_class.__name__}. Error: {e}"
            ) from e

    @model_validator(mode="after")
    def validate_optimizer_consistency(self) -> "AddModelParams":
        """
        Validación cruzada para asegurar coherencia entre:
        - Campos con optimize=True en los parámetros
        - Selección de optimizer_name
        - Configuración de optimizer_parameters
        - Selección de goal_metric válido
        """

        has_optimize_true = self._has_any_optimize_true()

        if has_optimize_true:
            self._validate_optimizer_required()
        else:
            self._validate_no_optimizer_configured()

        if self.optimizer_name != "":
            self._validate_optimizer_parameters_match()

        return self

    def _has_any_optimize_true(self) -> bool:
        """
        Recorre recursivamente todos los campos de parameters y detecta si
        alguno tiene optimize=True
        """

        def check_optimize(obj: Any) -> bool:
            if isinstance(obj, (OptimizerFloatParam, OptimizerIntParam)):
                return obj.optimize
            elif isinstance(obj, BaseModel):
                for field_name, field_value in obj.__dict__.items():  # noqa: B007
                    if check_optimize(field_value):
                        return True
            elif isinstance(obj, dict):
                for value in obj.values():
                    if check_optimize(value):
                        return True
            return False

        return check_optimize(self.parameters)

    def _validate_optimizer_required(self) -> None:
        """
        Cuando hay optimize=True en algún parámetro, se requiere: optimizer_name,
        optimizer_parameters y goal_metric válido
        """
        errors = []

        if self.optimizer_name == "":
            errors.append(
                "Se detectaron parámetros con 'optimize=True'. Debe proporcionar un "
                "'optimizer_name' válido ('OptunaOptimizer' o 'HyperOptOptimizer')."
            )
        if self.optimizer_parameters is None:
            errors.append(
                "Se detectaron parámetros con 'optimize=True'. Debe proporcionar "
                "'optimizer_parameters' configurados correctamente."
            )
        if self.goal_metric == "":
            errors.append(
                "Se detectaron parámetros con 'optimize=True'. Debe seleccionar un "
                "'goal_metric' válido (no puede estar vacío)."
            )

        if errors:
            raise ValueError(
                "Configuración de optimización incompleta:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    def _validate_no_optimizer_configured(self) -> None:
        """
        Cuando NO hay optimize=True, se debe asegurar que no haya un optimizador
        parcialmente configurado
        """
        if (
            self.optimizer_name == ""
            and self.optimizer_parameters is None
            and self.goal_metric == ""
        ):
            return

        errors = []

        if self.optimizer_name != "":
            errors.append(
                "No se detectaron parámetros con 'optimize=True', pero se proporcionó "
                "'optimizer_name'. Déjelo vacío si no desea optimizar."
            )

        if self.optimizer_parameters is not None:
            errors.append(
                "No se detectaron parámetros con 'optimize=True', pero se proporcionó "
                "'optimizer_parameters'. Déjelo como None si no desea optimizar."
            )

        if self.goal_metric != "":
            errors.append(
                "No se detectaron parámetros con 'optimize=True', pero se proporcionó "
                "'goal_metric'. Déjelo vacío si no desea optimizar."
            )

        if errors:
            raise ValueError(
                "Configuración de optimización incompleta (parcialmente configurada "
                "sin parámetros a optimizar):\n" + "\n".join(f"  - {e}" for e in errors)
            )

    def _validate_optimizer_parameters_match(self) -> None:
        """
        Valida que el tipo de optimizer_parameters sea compatible con el
        optimizer_name seleccionado.
        """
        if self.optimizer_name == "OptunaOptimizer":
            if not isinstance(self.optimizer_parameters, OptunaOptimizerParams):
                raise ValueError(
                    f"Optimizer 'OptunaOptimizer' requiere 'optimizer_parameters' de "
                    f"tipo OptunaOptimizerParams, pero se recibió "
                    f"{type(self.optimizer_parameters).__name__}."
                )

            elif self.optimizer_name == "HyperOptOptimizer" and not isinstance(
                self.optimizer_parameters, HyperOptOptimizerParams
            ):
                raise ValueError(
                    f"Optimizer 'HyperOptOptimizer' requiere 'optimizer_parameters' "
                    f"de tipo HyperOptOptimizerParams, pero se recibió "
                    f"{type(self.optimizer_parameters).__name__}."
                )
