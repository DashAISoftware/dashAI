from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class ConverterColumn(BaseModel):
    idx: int = Field(..., description="Índice de la columna")
    columnName: str = Field(..., description="Nombre de la columna")  # noqa: N815
    valueType: Literal[  # noqa: N815
        "Float", "String", "Integer", "Categorical", "Image", "Text"
    ] = Field(  # noqa: N815
        ..., description="Tipo de valor de la columna"
    )

    dataType: Literal["float64", "int64", "string", "object", "bool"] = Field(  # noqa: N815
        ..., description="Tipo de dato de la columna"
    )


class DeleteConverterById(BaseModel):
    converter_id: int = Field(..., description="ID del convertidor a eliminar")


class BaseConverterParams(BaseModel):
    notebook_id: int = Field(..., description="ID del notebook.")
    columns: list[ConverterColumn] = Field(
        ..., min_length=1, description="Columnas a las que se aplica el convertidor. "
    )
    order: int = Field(1, ge=0, description="Orden del convertidor en el pipeline.")


class BaseConverterWithTargetParams(BaseConverterParams):
    target_column: ConverterColumn = Field(
        ...,
        description=(
            "Datos de la columna objetivo. El convertidor se aplicará a esta columna."
        ),
    )


class SaveDatasetWithConverterTransformationsParams(BaseModel):
    dataset_name: str = Field(
        ...,
        min_length=1,
        description="Nombre del nuevo dataset que se creará a partir del notebook.",
    )
    notebook_id: int = Field(
        ...,
        gt=0,
        description="ID del notebook del cual se copiará el dataset asociado.",
    )


class CreateBinarizerParams(BaseConverterParams):
    threshold: float = Field(
        0.0,
        description=(
            "Los valores por debajo o igual al umbral se reemplazan por 0; "
            "los superiores por 1."
        ),
    )


class CreateLabelEncoderParams(BaseConverterParams):
    pass


class CreateOneHotEncoderParams(BaseConverterParams):
    categories: str = Field(
        "auto", description="Las categorías de cada característica."
    )
    drop: Optional[str] = Field(
        None,
        description=(
            "Especifica una metodología para eliminar una categoría por característica."
        ),
    )
    dtype: Literal["int32", "int64"] = Field(
        "int64", description="Tipo de dato de salida deseado."
    )
    handle_unknown: Literal["error", "ignore", "infrequent_if_exist"] = Field(
        "error",
        description="Cómo manejar categorías desconocidas durante la transformación.",
    )
    min_frequency: Optional[Union[int, float]] = Field(
        None,
        description="Frecuencia mínima para considerar una categoría como frecuente.",
    )
    max_categories: Optional[int] = Field(
        None, ge=1, description="Número máximo de categorías a codificar."
    )
    feature_name_combiner: Literal["concat"] = Field(
        "concat", description="Método usado para combinar nombres de características."
    )


class CreateOrdinalEncoderParams(BaseConverterParams):
    categories: str = Field(
        "auto", description="Categorías (valores únicos) por característica."
    )
    dtype: Literal["int32", "int64"] = Field(
        "int64", description="Tipo de dato deseado."
    )
    handle_unknown: Literal["error", "use_encoded_value"] = Field(
        "error", description="Cómo manejar valores desconocidos."
    )
    unknown_value: Optional[int] = Field(
        None, description="El valor a usar para categorías desconocidas."
    )
    min_frequency: Optional[Union[int, float]] = Field(
        None,
        description="Frecuencia mínima para considerar una categoría como frecuente.",
    )
    max_categories: Optional[int] = Field(
        None, ge=1, description="Máximo de categorías a codificar."
    )


class CreateMaxAbsScalerParams(BaseConverterParams):
    pass


class CreateMinMaxScalerParams(BaseConverterParams):
    min_range: float = Field(
        0.0, ge=0.0, description="El valor mínimo del rango al que escalar los datos."
    )
    max_range: float = Field(
        1.0, ge=0.0, description="El valor máximo del rango al que escalar los datos."
    )
    clip: bool = Field(
        False, description="Si es True, recorta los datos al rango de características."
    )


class CreateNormalizerParams(BaseConverterParams):
    norm: Literal["l1", "l2", "max"] = Field(
        "l2", description="Norma a aplicar por fila."
    )


class CreateStandardScalerParams(BaseConverterParams):
    with_mean: bool = Field(
        True, description="Si es True, centra los datos antes de escalar."
    )
    with_std: bool = Field(
        True,
        description=(
            "Si es True, escala los datos a varianza unitaria o de forma "
            "equivalente, desviación estándar."
        ),
    )


class CreateFastICAParams(BaseConverterParams):
    n_components: Optional[int] = Field(
        None, ge=1, description="Componentes independientes a extraer."
    )
    algorithm: Literal["parallel", "deflation"] = Field(
        "parallel", description="Algoritmo ICA: 'parallel' o 'deflation'."
    )
    whiten: Optional[Union[Literal["arbitrary-variance", "unit-variance"], bool]] = (
        Field(
            "unit-variance", description="Campo para seleccionar el tipo de blanqueo."
        )
    )

    fun: Literal["logcosh", "exp", "cube"] = Field(
        "logcosh", description="Función de la función g (entropía negativa)."
    )
    fun_args: Optional[str] = Field(None, description="Argumentos para la función g.")
    max_iter: int = Field(200, ge=1, description="Máximo de iteraciones a realizar.")
    tol: float = Field(
        1e-4, ge=0.0, description="Tolerancia en la actualización en cada iteración."
    )
    w_init: Optional[str] = Field(
        None, description="Estimación inicial de la matriz de separación."
    )
    whiten_solver: Literal["eigh", "svd"] = Field(
        "svd", description="El solver a usar para el blanqueo."
    )
    random_state: Optional[Union[int, Literal["RandomState"]]] = Field(
        None,
        description=(
            "Usado para inicializar w_init cuando no se especifica, con "
            "una distribución normal. Pasa un entero para resultados reproducibles."
        ),
    )


class CreateIncrementalPCAParams(BaseConverterParams):
    n_components: Optional[int] = Field(
        2, ge=1, description="Número de componentes a conservar."
    )
    whiten: bool = Field(
        False,
        description=(
            "Si es True, las componentes se escalan para asegurar salidas no "
            "correlacionadas con varianzas unitarias."
        ),
    )
    batch_size: Optional[int] = Field(
        None, ge=1, description="Número de muestras a usar por lote. "
    )


class CreateNystroemParams(BaseConverterParams):
    kernel: Optional[str] = Field(
        "rbf", description="Tipo de kernel usado para la aproximación."
    )
    gamma: Optional[float] = Field(
        None,
        gt=0.0,
        description=(
            "Parámetro gamma para los kernel RBF, laplaciano, polinomial, "
            "chi2, exponencial y sigmoide."
        ),
    )
    coef0: Optional[float] = Field(
        None, description="Parámetro coef0 para los kernels polinomial y sigmoide."
    )
    degree: Optional[float] = Field(
        None, ge=1.0, description="El grado del kernel polinomial. "
    )
    kernel_params: Optional[str] = Field(
        None, description="Parámetros adicionales para la función kernel."
    )
    n_components: int = Field(
        2, ge=1, description="El número de características a construir."
    )
    random_state: Optional[Union[int, Literal["RandomState"]]] = Field(
        None,
        description=(
            "Semilla del generador pseudoaleatorio usado al mezclar "
            "los datos. Pasa un entero para resultados reproducibles."
        ),
    )
    n_jobs: Optional[int] = Field(
        None, description="Número de trabajos a ejecutar en paralelo. "
    )


class CreatePCAParams(BaseConverterParams):
    n_components: Optional[Union[int, float, str]] = Field(
        2,
        description=(
            "Número de componentes a conservar. Si es None, se conservan "
            "todas las componentes."
        ),
    )
    whiten: bool = Field(
        False,
        description=(
            "Si es True, las componentes se escalan para asegurar salidas no "
            "correlacionadas con varianzas unitarias. Puede mejorar "
            "estimadores posteriores."
        ),
    )
    svd_solver: Literal["auto", "full", "covariance_eigh", "arpack", "randomized"] = (
        Field(
            "auto",
            description=(
                "Método para la descomposición propia. 'auto' elige el más "
                "apropiado según los datos."
            ),
        )
    )
    tol: float = Field(
        0.0,
        ge=0.0,
        description="Tolerancia para valores singulares cuando svd_solver == 'arpack'.",
    )
    iterated_power: Union[int, Literal["auto"]] = Field(
        "auto",
        description="Número de iteraciones para el método de potencia cuando "
        "svd_solver == 'randomized'. >= 1 o 'auto' para elegir automáticamente.",
    )
    n_oversamples: int = Field(
        10,
        ge=1,
        description=(
            "Número de iteraciones de potencia cuando svd_solver == 'randomized'. "
        ),
    )
    power_iteration_normalizer: Optional[Literal["auto", "QR", "LU"]] = Field(
        None, description="Cómo se calcula el normalizador de iteración de potencia"
    )
    random_state: Optional[Union[int, Literal["RandomState"]]] = Field(
        None,
        description=(
            "Usado con los métodos 'arpack' o 'randomized'. Pasa un entero "
            "para resultados reproducibles."
        ),
    )


class CreateTruncatedSVDParams(BaseConverterParams):
    n_components: int = Field(
        2, gt=0, description="Dimensionalidad deseada de los datos de salida. "
    )
    algorithm: Literal["arpack", "randomized"] = Field(
        "randomized",
        description=(
            "Método SVD a utilizar. Valores permitidos: 'arpack' o 'randomized'."
        ),
    )
    n_iter: int = Field(
        5, gt=0, description="Número de iteraciones para el método SVD aleatorizado. "
    )
    n_oversamples: int = Field(
        10,
        gt=0,
        description=(
            "Número de iteraciones de potencia utilizadas en el "
            "método SVD aleatorizado."
        ),
    )
    power_iteration_normalizer: Literal["auto", "QR", "LU", "none"] = Field(
        "auto", description="Método para normalizar los eigenvectores. "
    )
    random_state: Optional[int] = Field(
        None,
        description=(
            "Semilla para el SVD aleatorizado. Pasa un entero para resultados "
            "reproducibles, o None para no determinista."
        ),
    )
    tol: float = Field(0.0, ge=0.0, description="Tolerancia para el solver ARPACK.")


class CreateVarianceThresholdParams(BaseConverterParams):
    threshold: float = Field(
        0.0,
        ge=0.0,
        description=(
            "Se eliminarán las características con una varianza inferior a este umbral."
        ),
    )


class CreateCharacterReplacerParams(BaseConverterParams):
    char_to_replace: str = Field(
        "", description="El carácter o subcadena a reemplazar. No puede estar vacío."
    )
    replacement_char: Optional[str] = Field(
        None,
        description=(
            "El carácter o subcadena con el que reemplazar. Si es nulo, se eliminará "
            "'char_to_replace'."
        ),
    )


class CreateColumnRemoverParams(BaseConverterParams):
    pass


class CreateKNNImputerParams(BaseConverterParams):
    n_neighbors: int = Field(
        5,
        ge=1,
        description=("Número de vecinos más cercanos a usar para la imputación."),
    )
    weights: Literal["uniform", "distance"] = Field(
        "uniform", description="Función de peso a usar para la imputación."
    )
    metric: Literal["nan_euclidean"] = Field(
        "nan_euclidean", description="Métrica a usar para la imputación."
    )
    add_indicator: bool = Field(
        False, description="Si es True, se apilará un MissingIndicator sobre la salida."
    )
    keep_empty_features: bool = Field(
        False, description="Si es True, se mantendrán las características vacías."
    )


class CreateMissingIndicatorParams(BaseConverterParams):
    pass


class CreateNanRemoverParams(BaseConverterParams):
    pass


class CreateSimpleImputerParams(BaseConverterParams):
    strategy: Literal["mean", "median", "most_frequent", "constant"] = Field(
        "mean", description="Estrategia de imputación."
    )
    fill_value: Optional[Union[int, float, str]] = Field(
        None, description="El valor para reemplazar los valores faltantes."
    )
    add_indicator: bool = Field(
        False, description="Si es True, se apilará un MissingIndicator sobre la salida."
    )
    keep_empty_features: bool = Field(
        False, description="Si es True, se mantendrán las características vacías."
    )


class CreateBagOfWordsParams(BaseConverterParams):
    max_features: int = Field(
        1000,
        gt=0,
        description=(
            "Número máximo de características (palabras más frecuentes) a conservar."
        ),
    )
    lowercase: bool = Field(
        True,
        description="Si es True, se convierte todo a minúsculas antes de tokenizar.",
    )
    stop_words: Optional[Literal["english"]] = Field(
        None, description="Conjunto de stopwords a eliminar."
    )
    lower_bound_ngrams: int = Field(
        1,
        gt=0,
        le=5,
        description="Límite inferior de n-grams. Debe ser <= al límite superior.",
    )
    upper_bound_ngrams: int = Field(
        1,
        gt=0,
        le=5,
        description="Límite superior de n-grams. Debe ser >= al límite inferior.",
    )


class CreateEmbeddingParams(BaseConverterParams):
    model_name: Literal[
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "sentence-transformers/all-distilroberta-v1",
        "bert-base-uncased",
        "bert-large-uncased",
        "bert-base-multilingual-cased",
        "distilbert-base-uncased",
        "roberta-base",
        "roberta-large",
        "distilroberta-base",
    ] = Field(
        "sentence-transformers/all-MiniLM-L6-v2",
        description="Nombre del modelo preentrenado a usar.",
    )
    max_length: int = Field(
        512, ge=1, description="Longitud máxima de secuencia para la tokenización."
    )
    batch_size: int = Field(
        32, ge=1, description="Número de muestras a procesar a la vez."
    )
    device: Literal["cuda", "cpu"] = Field(
        "cpu", description="Dispositivo a usar para el cómputo."
    )
    pooling_strategy: Literal["mean", "cls", "max"] = Field(
        "mean",
        description="Estrategia para agrupar embeddings de tokens en uno de oración.",
    )


class CreateTFIDFParams(BaseConverterParams):
    max_features: int = Field(
        1000,
        gt=0,
        description=(
            "Número máximo de características (términos más frecuentes) a conservar."
        ),
    )
    lowercase: bool = Field(
        True, description="Si True, convierte a minúsculas antes de tokenizar."
    )
    stop_words: Optional[Literal["english"]] = Field(
        None, description="Conjunto de stopwords a eliminar. Usa 'english' o None."
    )
    lower_bound_ngrams: int = Field(
        1,
        gt=0,
        le=5,
        description=(
            "Límite inferior de n-grams a extraer. Debe ser <= al límite superior."
        ),
    )
    upper_bound_ngrams: int = Field(
        1,
        gt=0,
        le=5,
        description=(
            "Límite superior de n-grams a extraer. Debe ser >= al límite inferior."
        ),
    )


class CreateTokenizerParams(BaseConverterParams):
    model_name: Literal[
        "bert-base-uncased",
        "bert-large-uncased",
        "distilbert-base-uncased",
        "roberta-base",
        "roberta-large",
        "distilroberta-base",
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2",
    ] = Field(
        "bert-base-uncased",
        description="Nombre del modelo de tokenización preentrenado.",
    )
    max_length: int = Field(
        512, ge=1, description="Longitud máxima de secuencia para la tokenización."
    )
    batch_size: int = Field(
        32, ge=1, description="Número de muestras a procesar a la vez."
    )
    device: Literal["cuda", "cpu"] = Field(
        "cpu", description="Dispositivo a usar para el cómputo."
    )


class CreateAdditiveChi2SamplerParams(BaseConverterParams):
    sample_steps: int = Field(
        2, ge=1, description="Número de pasos de muestreo (mezcla) a realizar."
    )
    sample_interval: Optional[float] = Field(
        None,
        ge=1.0,
        description="Número de muestras generadas entre cada muestra original.",
    )


class CreatePolynomialFeaturesParams(BaseConverterParams):
    degree: int = Field(
        2, ge=1, description="El grado de las características polinomiales."
    )
    interaction_only: bool = Field(
        False,
        description=(
            "Si es True, solo se producen características de interacción: "
            "productos de hasta 'degree' características de entrada distintas."
        ),
    )
    include_bias: bool = Field(
        True,
        description=(
            "Si es True (por defecto), incluye una columna de sesgo (columna "
            "de unos que actúa como término independiente)."
        ),
    )
    poly_order: Literal["C", "F"] = Field(
        "C",
        description=(
            "Orden del arreglo de salida en el caso denso. El orden 'F' es más "
            "rápido de calcular, pero puede ralentizar estimadores posteriores."
        ),
    )


class CreateRBFSamplerParams(BaseConverterParams):
    gamma: Union[Literal["scale"], float] = Field(
        "scale", description="Parámetro del kernel RBF."
    )
    n_components: int = Field(
        100, ge=1, description="El número de características a construir."
    )
    random_state: Optional[Union[int, Literal["RandomState"]]] = Field(
        0,
        description=(
            "Generador pseudoaleatorio para controlar pesos y desplazamientos "
            "aleatorios al ajustar los datos. Pasa un entero para obtener "
            "resultados reproducibles."
        ),
    )


class CreateSkewedChi2SamplerParams(BaseConverterParams):
    skewedness: float = Field(
        1.0, gt=0.0, description="El parámetro de sesgo del kernel chi-cuadrado."
    )
    n_components: int = Field(
        100,
        ge=1,
        description=(
            "Número de muestras de Monte Carlo por característica original. Equivale "
            "a la dimensionalidad del espacio de características calculado."
        ),
    )
    random_state: Optional[Union[int, Literal["RandomState"]]] = Field(
        None,
        description=(
            "Generador pseudoaleatorio para controlar la generación de pesos y "
            "desplazamientos aleatorios al ajustar los datos. Pasa un entero para "
            "obtener resultados reproducibles."
        ),
    )


class CreateGenericUnivariateSelectParams(BaseConverterWithTargetParams):
    mode: Literal["percentile", "k_best", "fpr", "fdr", "fwe"] = Field(
        "percentile",
        description=(
            "Selecciona características según un percentil de las "
            "puntuaciones más altas."
        ),
    )
    param: Optional[Union[int, float, Literal["all"]]] = Field(
        1e-5, description="Parámetro del modo."
    )


class CreateSelectFdrParams(BaseConverterWithTargetParams):
    alpha: float = Field(
        0.05,
        ge=0.0,
        le=1.0,
        description=(
            "El p-valor sin corregir más alto para que una característica "
            "sea conservada."
        ),
    )


class CreateSelectFprParams(BaseConverterWithTargetParams):
    alpha: float = Field(
        0.05,
        ge=0.0,
        le=1.0,
        description="El p-valor más alto para conservar características.",
    )


class CreateSelectFweParams(BaseConverterWithTargetParams):
    alpha: float = Field(
        0.05,
        ge=0.0,
        le=1.0,
        description=(
            "El p-valor sin corregir más alto para que una característica "
            "sea conservada."
        ),
    )


class CreateSelectKBestParams(BaseConverterWithTargetParams):
    k: Union[int, Literal["all"]] = Field(
        10, description="Número de características superiores a seleccionar."
    )


class CreateSelectPercentileParams(BaseConverterWithTargetParams):
    percentile: int = Field(
        10, ge=1, le=100, description="Porcentaje de características a conservar."
    )


class CreateRandomUnderSamplerParams(BaseConverterWithTargetParams):
    sampling_strategy: Union[float, Literal["auto"]] = Field(
        "auto",
        description=(
            "Estrategia de muestreo (float o 'auto') para reducir la clase mayoritaria."
        ),
    )
    random_state: Optional[int] = Field(
        None, description="Semilla para reproducibilidad."
    )


class CreateSMOTEParams(BaseConverterWithTargetParams):
    sampling_strategy: Union[float, Literal["auto"]] = Field(
        "auto",
        description=(
            "Estrategia de muestreo (float o 'auto') para determinar el tamaño "
            "de la clase minoritaria."
        ),
    )
    random_state: Optional[int] = Field(
        None, description="Semilla para reproducibilidad."
    )
    k_neighbors: int = Field(
        5, ge=1, description="Número de vecinos para generar muestras sintéticas."
    )


class CreateSMOTEENNParams(BaseConverterWithTargetParams):
    sampling_strategy: Union[float, Literal["auto"]] = Field(
        "auto",
        description=(
            "Estrategia de muestreo para aplicar SMOTE y limpiar el conjunto de datos."
        ),
    )
    random_state: Optional[int] = Field(
        None, description="Semilla usada para reproducibilidad."
    )
    k_neighbors: int = Field(
        5, ge=1, description="Número de vecinos utilizados por SMOTE."
    )
