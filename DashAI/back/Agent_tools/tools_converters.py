import json
import time
from typing import Any, Literal, Optional, Union

import requests
from langchain.tools import tool
from langchain_core.tools import BaseTool

from DashAI.back.Agent_tools.utils import create_converter_and_enqueue
from DashAI.back.core.utils import MultilingualString
from DashAI.back.pydantic_models.converters_models import (
    ConverterColumn,
    CreateAdditiveChi2SamplerParams,
    CreateBagOfWordsParams,
    CreateBinarizerParams,
    CreateCharacterReplacerParams,
    CreateColumnRemoverParams,
    CreateEmbeddingParams,
    CreateFastICAParams,
    CreateGenericUnivariateSelectParams,
    CreateIncrementalPCAParams,
    CreateKNNImputerParams,
    CreateLabelEncoderParams,
    CreateMaxAbsScalerParams,
    CreateMinMaxScalerParams,
    CreateMissingIndicatorParams,
    CreateNanRemoverParams,
    CreateNormalizerParams,
    CreateNystroemParams,
    CreateOneHotEncoderParams,
    CreateOrdinalEncoderParams,
    CreatePCAParams,
    CreatePolynomialFeaturesParams,
    CreateRandomUnderSamplerParams,
    CreateRBFSamplerParams,
    CreateSelectFdrParams,
    CreateSelectFprParams,
    CreateSelectFweParams,
    CreateSelectKBestParams,
    CreateSelectPercentileParams,
    CreateSimpleImputerParams,
    CreateSkewedChi2SamplerParams,
    CreateSMOTEENNParams,
    CreateSMOTEParams,
    CreateStandardScalerParams,
    CreateTFIDFParams,
    CreateTokenizerParams,
    CreateTruncatedSVDParams,
    CreateVarianceThresholdParams,
    DeleteConverterById,
    SaveDatasetWithConverterTransformationsParams,
)


@tool(
    "get_converters",
    description=(
        "Descubre todos los tipos de conversores disponibles en DashAI para "
        "transformar y procesar datos."
    ),
    extras={
        "display_name": MultilingualString(
            en="List Available Converters on DashAI",
            es="Listar conversores ejecutados en DashAI",
        )
    },
)
def get_converters() -> str:
    """Get available converters in DashAI.

    Retrieves the list of converter components available in DashAI for
    transforming and processing datasets.

    Parameters
    ----------
    None

    Returns
    -------
    str
        List of available converters when the request is successful.
        Otherwise, returns an error message describing the failure.
    """
    endpoint = "http://localhost:8000/api/v1/component/"
    params = {"select_types": ["Converter"]}
    try:
        response = requests.get(
            endpoint,
            params=params,
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 200:
            return response.json()
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los converters: {exc}"


@tool(
    "delete_converter_by_id",
    args_schema=DeleteConverterById,
    description=(
        "Elimina un convertidor creado en el notebook usando su converter_id. "
        "El convertidor y sus transformaciones se removerán del notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Delete Converter by ID", es="Eliminar convertidor por ID"
        )
    },
)
def delete_converter_by_id(converter_id: int) -> str:
    """Delete a converter from DashAI.

    Removes an existing converter and its associated transformations from a
    notebook using the converter identifier.

    Parameters
    ----------
    converter_id : int
        Identifier of the converter to delete.

    Returns
    -------
    str
        Confirmation message if the converter is successfully deleted.
        Otherwise, returns an error message describing the failure.
    """
    endpoint = f"http://localhost:8000/api/v1/converter/{converter_id}"
    try:
        response = requests.delete(
            endpoint, headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return (
                f"Se ha ejecutado de manera exitosa la eliminacion del convertidor "
                f"{converter_id} de la plataforma"
            )
        return (
            f"Error al eliminar el convertidor: {response.status_code}.  El detalle "
            f"es: {response.json()['detail']}"
        )
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error durante la eliminacion del convertidor: {exc}"


@tool(
    "save_dataset_with_converter_transformations",
    args_schema=SaveDatasetWithConverterTransformationsParams,
    description=(
        "Guarda una copia del dataset asociado a un notebook como un nuevo dataset "
        "independiente en la aplicación para poder trabajar con el. Esta herramienta "
        "debe ser empleada al momento de querer guardar una copia de un dataset que "
        "tiene modificaciones efectuadas con convertidores en la aplicación"
    ),
    extras={
        "display_name": MultilingualString(
            en="Save Dataset with Converter Transformations",
            es="Guardar dataset con transformaciones de convertidores",
        )
    },
)
def save_dataset_with_converter_transformations(
    dataset_name: str, notebook_id: int
) -> str:
    """Save a dataset with converter transformations applied.

    Creates a new independent dataset from the dataset associated with a
    notebook, preserving the transformations performed through converters.
    The dataset creation process is queued as a background job and its
    execution status is monitored until completion or failure.

    Parameters
    ----------
    dataset_name : str
        Name assigned to the new dataset created from the notebook data.
    notebook_id : int
        Identifier of the notebook containing the dataset and converter
        transformations to be saved.

    Returns
    -------
    str
        Information about the created dataset and the associated processing
        job. Returns the final dataset status if processing completes
        successfully or fails. Otherwise, returns information indicating that
        the process continues in the background.
    """
    dataset_endpoint = "http://localhost:8000/api/v1/dataset/"
    payload = {"name": dataset_name, "notebook_id": notebook_id}

    try:
        response = requests.post(
            dataset_endpoint, json=payload, headers={"Content-Type": "application/json"}
        )
        if response.status_code not in (200, 201):
            return (
                f"Error al crear el dataset: {response.status_code} - {response.text}"
            )
        created_dataset = response.json()
        dataset_id = created_dataset.get("id")
    except requests.exceptions.RequestException as exc:
        return f"Error de conexión al crear el dataset: {exc}"

    job_endpoint = "http://localhost:8000/api/v1/job/"
    kwargs_json = json.dumps(
        {"dataset_id": dataset_id, "notebook_id": notebook_id, "url": "", "params": {}}
    )
    job_payload = {
        "job_type": (None, "DatasetJob"),
        "stop_when_queue_empties": (None, "true"),
        "kwargs": (None, kwargs_json),
    }

    try:
        job_response = requests.post(job_endpoint, files=job_payload)
        if job_response.status_code not in (200, 201):
            return (
                f"Dataset creado (id={dataset_id}) pero falló el "
                f"encolamiento: {job_response.status_code} - {job_response.text}"
            )

    except requests.exceptions.RequestException as exc:
        return f"Dataset creado (id={dataset_id}) pero falló el encolamiento: {exc}"

    try:
        requests.post("http://localhost:8000/api/v1/job/start/")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            "No se pudo iniciar el procesamiento de jobs en segundo plano."
        ) from e

    for _ in range(7):
        time.sleep(5)
        try:
            status_response = requests.get(
                f"http://localhost:8000/api/v1/dataset/{dataset_id}",
                headers={"Content-Type": "application/json"},
            )
            if status_response.status_code == 200:
                dataset_status = status_response.json().get("status")
                if dataset_status == 3:
                    return {
                        "dataset": status_response.json(),
                        "job": job_response.json(),
                        "message": f"Dataset '{dataset_name}' creado y copiado "
                        f"exitosamente desde el notebook {notebook_id}.",
                    }
                if dataset_status == 4:
                    return (
                        f"El dataset '{dataset_name}' fue creado pero terminó "
                        f"con error al copiarse desde el notebook {notebook_id}."
                    )

        except requests.exceptions.RequestException:
            pass

    return {
        "dataset": created_dataset,
        "job": job_response.json(),
        "message": (
            f"Dataset '{dataset_name}' creado y encolado exitosamente para "
            f"copiarse desde el notebook {notebook_id}. El proceso continúa en "
            f"segundo plano."
        ),
    }


@tool(
    "create_binarizer",
    args_schema=CreateBinarizerParams,
    description=(
        "Convierte características numéricas a valores binarios según un "
        "umbral. Valores > threshold -> 1, resto -> 0."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Binarizer", es="Ejecutar convertidor Binarizador"
        )
    },
)
def create_binarizer(
    notebook_id: int, columns: list[ConverterColumn], order: int, threshold: float
) -> Any:
    """Create and execute a binarizer converter.

    Creates a Binarizer converter in a notebook and enqueues its execution.
    The converter transforms numerical features into binary values according
    to a threshold, assigning ``1`` to values greater than the threshold and
    ``0`` otherwise.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where the binarization transformation will be applied.
    order : int
        Execution order of the converter within the notebook transformation
        pipeline.
    threshold : float
        Threshold value used to convert numerical values into binary values.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="Binarizer",
        notebook_id=notebook_id,
        columns=columns,
        params={"threshold": threshold},
        order=order,
    )


@tool(
    "create_label_encoder",
    args_schema=CreateLabelEncoderParams,
    description=(
        "Codifica columnas categóricas como enteros consecutivos (0, 1, 2...)."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Label Encoder",
            es="Ejecutar convertidor Codificador de Etiquetas",
        )
    },
)
def create_label_encoder(
    notebook_id: int, columns: list[ConverterColumn], order: int
) -> Any:
    """Create and execute a label encoder converter.

    Creates a LabelEncoder converter in a notebook and enqueues its execution.
    The converter transforms categorical values into consecutive integer
    representations.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns containing categorical values to encode.
    order : int
        Execution order of the converter within the notebook transformation
        pipeline.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="LabelEncoder",
        notebook_id=notebook_id,
        columns=columns,
        params={},
        order=order,
    )


@tool(
    "create_one_hot_encoder",
    args_schema=CreateOneHotEncoderParams,
    description=(
        "Codifica columnas categóricas como vectores binarios one-hot. Genera "
        "una columna binaria por cada categoría."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute One-Hot Encoder",
            es="Ejecutar convertidor Codificador One-Hot",
        )
    },
)
def create_one_hot_encoder(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    categories: str,
    drop: Optional[str],
    dtype: str,
    handle_unknown: str,
    min_frequency: Optional[Union[int, float]],
    max_categories: Optional[int],
    feature_name_combiner: str,
) -> Any:
    """Create and execute a one-hot encoder converter.

    Creates a OneHotEncoder converter in a notebook and enqueues its execution.
    The converter transforms categorical features into binary vectors by
    generating one binary feature for each category.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where the encoding transformation will be applied.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    categories : str
        Category selection strategy used by the encoder. By default, categories
        are automatically detected.
    drop : str | None
        Strategy used to remove one category per feature during encoding.
        If ``None``, no category is dropped.
    dtype : str
        Output data type generated by the encoder. Supported values are
        ``"int32"`` and ``"int64"``.
    handle_unknown : str
        Strategy used to handle unknown categories during transformation.
        Supported values are ``"error"``, ``"ignore"``, and
        ``"infrequent_if_exist"``.
    min_frequency : int | float | None
        Minimum frequency required for a category to be considered frequent.
        Categories below this threshold can be grouped as infrequent.
    max_categories : int | None
        Maximum number of categories to encode. Must be greater than or equal
        to 1 when specified.
    feature_name_combiner : str
        Method used to generate names for encoded features. Currently only
        ``"concat"`` is supported.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="OneHotEncoder",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "categories": categories,
            "drop": drop,
            "dtype": dtype,
            "handle_unknown": handle_unknown,
            "min_frequency": min_frequency,
            "max_categories": max_categories,
            "feature_name_combiner": feature_name_combiner,
        },
        order=order,
    )


@tool(
    "create_ordinal_encoder",
    args_schema=CreateOrdinalEncoderParams,
    description=(
        "Codifica categorías como enteros ordinales. A diferencia de "
        "LabelEncoder, procesa todas las columnas del scope a la vez."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Ordinal Encoder",
            es="Ejecutar convertidor Codificador Ordinal",
        )
    },
)
def create_ordinal_encoder(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    categories: str,
    dtype: str,
    handle_unknown: str,
    unknown_value: Optional[int],
    min_frequency: Optional[Union[int, float]],
    max_categories: Optional[int],
) -> Any:
    """Create and execute an ordinal encoder converter.

    Creates an OrdinalEncoder converter in a notebook and enqueues its
    execution. The converter transforms categorical features into ordinal
    integer representations by assigning an integer value to each category.

    Unlike LabelEncoder, this converter processes multiple input columns
    simultaneously while preserving the categorical relationship of each
    feature.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns containing categorical values to encode. At least one
        column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    categories : str
        Strategy used to determine categories for each feature. By default,
        categories are automatically detected.
    dtype : str
        Data type used for the encoded output values. Supported values are
        ``"int32"`` and ``"int64"``.
    handle_unknown : str
        Strategy used to handle unknown categories during transformation.
        Supported values are ``"error"`` and ``"use_encoded_value"``.
    unknown_value : int | None
        Encoded value assigned to unknown categories when
        ``handle_unknown="use_encoded_value"`` is selected.
    min_frequency : int | float | None
        Minimum frequency required for a category to be considered frequent.
    max_categories : int | None
        Maximum number of categories to encode. Must be greater than or equal
        to 1 when specified.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="OrdinalEncoder",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "categories": categories,
            "dtype": dtype,
            "handle_unknown": handle_unknown,
            "unknown_value": unknown_value,
            "min_frequency": min_frequency,
            "max_categories": max_categories,
        },
        order=order,
    )


@tool(
    "create_max_abs_scaler",
    args_schema=CreateMaxAbsScalerParams,
    description=(
        "Escala cada característica dividiéndola por su valor absoluto máximo "
        "observado, de modo que los valores transformados queden dentro del "
        "intervalo [0, 1].  En la documentación oficial aparece que queda en "
        "el intervalo [-1, 1], pero esto no es posible."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Max Abs Scaler",
            es="Ejecutar convertidor Escalador Max Abs",
        )
    },
)
def create_max_abs_scaler(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
) -> Any:
    """Create and execute a MaxAbsScaler converter.

    Creates a MaxAbsScaler converter in a notebook and enqueues its execution.
    The converter scales each feature by dividing it by its maximum absolute
    value, preserving sparsity and the original shape of the data.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where the scaling transformation will be applied.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="MaxAbsScaler",
        notebook_id=notebook_id,
        columns=columns,
        params={},
        order=order,
    )


@tool(
    "create_min_max_scaler",
    args_schema=CreateMinMaxScalerParams,
    description=(
        "Escala cada característica a un rango fijo [min_range, max_range] "
        "(por defecto [0, 1]) mediante una transformación lineal basada en los "
        "valores mínimo y máximo observados durante el ajuste. Conserva las "
        "relaciones relativas entre los datos, pero es sensible a valores "
        "atípicos, ya que la escala depende de los extremos observados. "
        "Resulta útil cuando los modelos requieren entradas acotadas, como "
        "redes neuronales, k-NN o datos de imágenes normalizados."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Min-Max Scaler",
            es="Ejecutar convertidor Escalador Min-Max",
        )
    },
)
def create_min_max_scaler(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    min_range: float,
    max_range: float,
    clip: bool,
) -> Any:
    """Create and execute a MinMaxScaler converter.

    Creates a MinMaxScaler converter in a notebook and enqueues its execution.
    The converter scales each feature into a fixed range using the minimum and
    maximum observed values during fitting.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where the scaling transformation will be applied.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    min_range : float
        Minimum value of the output range. Must be greater than or equal to 0.
    max_range : float
        Maximum value of the output range. Must be greater than or equal to 0.
    clip : bool
        Whether transformed values should be clipped to the configured output
        range.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="MinMaxScaler",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "min_range": min_range,
            "max_range": max_range,
            "clip": clip,
        },
        order=order,
    )


@tool(
    "create_normalizer",
    args_schema=CreateNormalizerParams,
    description=(
        "Normaliza cada muestra de forma independiente para que tenga una "
        "norma unitaria según el criterio seleccionado. Puede utilizar la norma "
        "Euclídea (l2), que preserva relaciones basadas en similitud coseno; la norma "
        "Manhattan (l1), adecuada cuando la dirección del vector es más relevante que "
        "las magnitudes relativas de sus componentes; o la norma Máxima (max o L), que "
        "escala los valores respecto al mayor valor absoluto y garantiza que el "
        "resultado quede dentro del intervalo [-1, 1]. A diferencia de otros "
        "escaladores que transforman cada característica por separado, este método "
        "opera sobre cada muestra completa, por lo que resulta especialmente útil "
        "en tareas de clasificación, agrupamiento y análisis de texto basadas en "
        "producto escalar o similitud coseno."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Normalizer", es="Ejecutar convertidor Normalizador"
        )
    },
)
def create_normalizer(
    notebook_id: int, columns: list[ConverterColumn], order: int, norm: str
) -> Any:
    """Create and execute a normalizer converter.

    Creates a Normalizer converter in a notebook and enqueues its execution.
    The converter normalizes each sample independently so that its norm is
    equal to one according to the selected normalization strategy.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where the normalization transformation will be applied.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    norm : str
        Norm used for row-wise normalization. Supported values are
        ``"l1"``, ``"l2"``, and ``"max"``.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="Normalizer",
        notebook_id=notebook_id,
        columns=columns,
        params={"norm": norm},
        order=order,
    )


@tool(
    "create_standard_scaler",
    args_schema=CreateStandardScalerParams,
    description=(
        "Estandariza columnas a media cero y varianza unitaria (z-score). El "
        "escalador más común para modelos basados en distancia.  Estandariza "
        "las características para que tengan media cero y varianza unitaria. "
        "Es una de las técnicas de preprocesamiento más utilizadas en modelos "
        "sensibles a la escala de las variables, aunque puede verse afectada "
        "por valores atípicos extremos."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Standard Scaler",
            es="Ejecutar convertidor Escalador Estándar",
        )
    },
)
def create_standard_scaler(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    with_mean: bool,
    with_std: bool,
) -> Any:
    """Create and execute a StandardScaler converter.

    Creates a StandardScaler converter in a notebook and enqueues its
    execution. The converter standardizes numerical features by removing the
    mean and scaling to unit variance.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where the standardization transformation will be
        applied. At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    with_mean : bool
        Whether to center the data before scaling.
    with_std : bool
        Whether to scale the data to unit variance.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="StandardScaler",
        notebook_id=notebook_id,
        columns=columns,
        params={"with_mean": with_mean, "with_std": with_std},
        order=order,
    )


@tool(
    "create_fast_ica",
    args_schema=CreateFastICAParams,
    description=(
        "Descompone los datos en componentes estadísticamente independientes mediante "
        "Independent Component Analysis (ICA) usando el algoritmo FastICA. El método "
        "asume que las observaciones son mezclas lineales de señales latentes "
        "independientes y no gaussianas, y estima dichas fuentes maximizando la "
        "no gaussianidad de los componentes extraídos. Se utiliza habitualmente para "
        "separación ciega de señales, eliminación de artefactos en bioseñales y "
        "extracción de características. La cantidad de componentes obtenidos se "
        "controla mediante n_components, y los datos pueden blanquearse (whitening) "
        "automáticamente antes de la descomposición."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Fast ICA", es="Ejecutar convertidor ICA Rápido"
        )
    },
)
def create_fast_ica(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    n_components: Optional[int],
    algorithm: str,
    whiten: Optional[str],
    fun: str,
    fun_args: Optional[str],
    max_iter: int,
    tol: float,
    w_init: Optional[str],
    whiten_solver: Literal["eigh", "svd"],
    random_state: Optional[Union[int, Literal["RandomState"]]],
) -> Any:
    """Create and execute a FastICA converter.

    Creates a FastICA converter in a notebook and enqueues its execution.
    The converter performs Independent Component Analysis to decompose data
    into statistically independent components.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns used for independent component extraction.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    n_components : int | None
        Number of independent components to extract.
    algorithm : str
        ICA optimization algorithm. Supported values are ``"parallel"`` and
        ``"deflation"``.
    whiten : str | None
        Whitening strategy used before component extraction.
    fun : str
        Function used to approximate neg-entropy. Supported values are
        ``"logcosh"``, ``"exp"``, and ``"cube"``.
    fun_args : str | None
        Additional arguments for the approximation function.
    max_iter : int
        Maximum number of iterations performed by the algorithm.
    tol : float
        Tolerance used to determine convergence.
    w_init : str | None
        Initial estimate of the unmixing matrix.
    whiten_solver : str
        Solver used for whitening. Supported values are ``"eigh"`` and
        ``"svd"``.
    random_state : int | "RandomState" | None
        Random seed or random state configuration used for reproducible
        initialization.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="FastICA",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "n_components": n_components,
            "algorithm": algorithm,
            "whiten": whiten,
            "fun": fun,
            "fun_args": fun_args,
            "max_iter": max_iter,
            "tol": tol,
            "w_init": w_init,
            "whiten_solver": whiten_solver,
            "random_state": random_state,
        },
        order=order,
    )


@tool(
    "create_incremental_pca",
    args_schema=CreateIncrementalPCAParams,
    description=(
        "Reduce la dimensionalidad usando PCA Incremental (IPCA), una variante "
        "online de PCA que procesa los datos en mini-batches y combina sus "
        "estimaciones SVD para aproximar el PCA de lote completo, con un uso de "
        "memoria constante. Útil para datasets demasiado grandes para caber en "
        "memoria, permite ajuste out-of-core mediante partial_fit, y opcionalmente "
        "normaliza (whitening) los componentes a varianza unitaria. Envuelve el "
        "IncrementalPCA de scikit-learn."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Incremental PCA",
            es="Ejecutar convertidor PCA Incremental",
        )
    },
)
def create_incremental_pca(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    n_components: Optional[int],
    whiten: bool,
    batch_size: Optional[int],
) -> Any:
    """Create and execute an Incremental PCA converter.

    Creates an IncrementalPCA converter in a notebook and enqueues its
    execution. The converter reduces dimensionality using an online PCA
    approach based on mini-batches, allowing processing of datasets that do
    not fit entirely in memory.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns used for dimensionality reduction. At least one column
        must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    n_components : int | None
        Number of components to preserve. Must be greater than or equal to 1
        when specified.
    whiten : bool
        Whether to scale components to produce uncorrelated outputs with unit
        variance.
    batch_size : int | None
        Number of samples processed in each mini-batch. Must be greater than
        or equal to 1 when specified.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="IncrementalPCA",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "n_components": n_components,
            "whiten": whiten,
            "batch_size": batch_size,
        },
        order=order,
    )


@tool(
    "create_nystroem",
    args_schema=CreateNystroemParams,
    description=(
        "Construye una representación explícita de baja dimensión que aproxima el "
        "kernel seleccionado mediante el método de Nyström. Esto permite aplicar "
        "algoritmos lineales escalables para aproximar métodos kernel. La calidad "
        "de la aproximación mejora al aumentar n_components, y la dimensión de salida "
        "pasa a ser exactamente n_components."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Nystroem", es="Ejecutar convertidor Nystroem"
        )
    },
)
def create_nystroem(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    kernel: Optional[str],
    gamma: Optional[float],
    coef0: Optional[float],
    degree: Optional[float],
    kernel_params: Optional[str],
    n_components: int,
    random_state: Optional[Union[int, Literal["RandomState"]]],
    n_jobs: Optional[int],
) -> Any:
    """Create and execute a Nystroem converter.

    Creates a Nystroem converter in a notebook and enqueues its execution.
    The converter builds a low-dimensional explicit feature representation
    that approximates a selected kernel function, allowing kernel methods to
    be applied using scalable linear algorithms.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns used for the kernel approximation. At least one column
        must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    kernel : str | None
        Kernel function used for the approximation. Defaults to ``"rbf"``.
    gamma : float | None
        Kernel coefficient used by RBF, Laplacian, polynomial, chi2,
        exponential, and sigmoid kernels. Must be greater than zero when
        specified.
    coef0 : float | None
        Independent term used by polynomial and sigmoid kernels.
    degree : float | None
        Degree of the polynomial kernel. Must be greater than or equal to 1
        when specified.
    kernel_params : str | None
        Additional parameters passed to the kernel function.
    n_components : int
        Number of generated features in the explicit approximation. Must be
        greater than or equal to 1.
    random_state : int | "RandomState" | None
        Random seed configuration used for reproducible component selection.
    n_jobs : int | None
        Number of parallel jobs used during execution.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="Nystroem",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "kernel": kernel,
            "gamma": gamma,
            "coef0": coef0,
            "degree": degree,
            "kernel_params": kernel_params,
            "n_components": n_components,
            "random_state": random_state,
            "n_jobs": n_jobs,
        },
        order=order,
    )


@tool(
    "create_pca",
    args_schema=CreatePCAParams,
    description=(
        "Reduce la dimensionalidad de los datos mediante Análisis de Componentes "
        "Principales (PCA), proyectándolos sobre un conjunto de componentes "
        "ortogonales que capturan la mayor parte de la variabilidad observada. Los "
        "componentes se ordenan según la varianza explicada y permiten comprimir la "
        "información, facilitar la visualización de datos de alta dimensión "
        "y reducir el ruido de forma no supervisada."
        "Si las columnas seleccionadas contienen valores NaN, el PCA no podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el PCA"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute PCA", es="Ejecutar convertidor PCA"
        )
    },
)
def create_pca(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    n_components: Optional[Union[int, float, str]],
    whiten: bool,
    svd_solver: str,
    tol: float,
    iterated_power: Union[int, Literal["auto"]],
    n_oversamples: int,
    power_iteration_normalizer: Optional[Literal["auto", "QR", "LU"]],
    random_state: Optional[Union[int, Literal["RandomState"]]],
) -> Any:
    """Create and execute a PCA converter.

    Creates a Principal Component Analysis (PCA) converter in a notebook and
    enqueues its execution. The converter reduces dimensionality by projecting
    data into orthogonal components ordered according to their explained
    variance.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns used for dimensionality reduction. At least one column
        must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    n_components : int | float | str | None
        Number of components to preserve. Can represent an absolute number,
        explained variance ratio, or solver-specific configuration.
    whiten : bool
        Whether to scale components to produce uncorrelated outputs with unit
        variance.
    svd_solver : str
        Solver used for singular value decomposition.
    tol : float
        Tolerance used by iterative solvers. Must be greater than or equal to
        zero.
    iterated_power : int | "auto"
        Number of power iterations used by randomized SVD or automatic
        selection strategy.
    n_oversamples : int
        Number of additional random vectors used by randomized SVD.
        Must be greater than or equal to 1.
    power_iteration_normalizer : str | None
        Normalization strategy used during power iterations.
    random_state : int | "RandomState" | None
        Random seed configuration used by randomized solvers.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="PCA",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "n_components": n_components,
            "whiten": whiten,
            "svd_solver": svd_solver,
            "tol": tol,
            "iterated_power": iterated_power,
            "n_oversamples": n_oversamples,
            "power_iteration_normalizer": power_iteration_normalizer,
            "random_state": random_state,
        },
        order=order,
    )


@tool(
    "create_truncated_svd",
    args_schema=CreateTruncatedSVDParams,
    description=(
        "Reduce la dimensionalidad mediante Descomposición en Valores Singulares "
        "Truncada (Truncated SVD), conservando los componentes más relevantes "
        "de los datos. A diferencia de PCA, no centra las variables antes de la "
        "transformación, lo que la hace especialmente adecuada para matrices dispersas "
        "como TF-IDF o representaciones bag-of-words. En minería de texto se conoce "
        "comúnmente como Análisis Semántico Latente (LSA)."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Truncated SVD", es="Ejecutar convertidor SVD Truncada"
        )
    },
)
def create_truncated_svd(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    n_components: int,
    algorithm: str,
    n_iter: int,
    n_oversamples: int,
    power_iteration_normalizer: Literal["auto", "QR", "LU", "none"],
    random_state: Optional[int],
    tol: float,
) -> Any:
    """Create and execute a Truncated SVD converter.

    Creates a Truncated SVD converter in a notebook and enqueues its
    execution. The converter reduces dimensionality by extracting the most
    relevant singular components without centering the input data, making it
    suitable for sparse representations such as TF-IDF or bag-of-words.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns used for dimensionality reduction. At least one column
        must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    n_components : int
        Desired output dimensionality. Must be greater than zero.
    algorithm : str
        SVD algorithm used during decomposition. Supported values are
        ``"arpack"`` and ``"randomized"``.
    n_iter : int
        Number of iterations for randomized SVD. Must be greater than zero.
    n_oversamples : int
        Number of additional samples used by randomized SVD. Must be greater
        than zero.
    power_iteration_normalizer : str
        Normalization strategy used during power iterations.
    random_state : int | None
        Random seed used for randomized decomposition.
    tol : float
        Tolerance used by the ARPACK solver. Must be greater than or equal to
        zero.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="TruncatedSVD",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "n_components": n_components,
            "algorithm": algorithm,
            "n_iter": n_iter,
            "n_oversamples": n_oversamples,
            "power_iteration_normalizer": power_iteration_normalizer,
            "random_state": random_state,
            "tol": tol,
        },
        order=order,
    )


@tool(
    "create_variance_threshold",
    args_schema=CreateVarianceThresholdParams,
    description=(
        "Elimina características cuya varianza sea inferior a un umbral definido. "
        "Por defecto, elimina las variables constantes (mismo valor en todas las "
        "muestras). Es un método de selección de características no supervisado, "
        "basado únicamente en la varianza marginal de cada variable (no usa "
        "etiquetas de clase), útil como filtro rápido y eficiente para reducir "
        "dimensionalidad antes de aplicar modelos o técnicas de selección "
        "supervisada más avanzadas como SelectKBest o RFECV."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Variance Threshold",
            es="Ejecutar convertidor Umbral de Varianza",
        )
    },
)
def create_variance_threshold(
    notebook_id: int, columns: list[ConverterColumn], order: int, threshold: float
) -> Any:
    """Create and execute a variance threshold converter.

    Creates a VarianceThreshold converter in a notebook and enqueues its
    execution. The converter removes features whose variance is below the
    configured threshold, providing an unsupervised feature selection method.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns evaluated for variance filtering. At least one column
        must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    threshold : float
        Minimum variance required for a feature to be retained. Must be
        greater than or equal to zero.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="VarianceThreshold",
        notebook_id=notebook_id,
        columns=columns,
        params={"threshold": threshold},
        order=order,
    )


@tool(
    "create_character_replacer",
    args_schema=CreateCharacterReplacerParams,
    description=(
        "Reemplaza un carácter o cadena de texto en columnas de texto del dataset. "
        "Útil para limpiar caracteres especiales o separadores."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Character Replacer",
            es="Ejecutar convertidor Reemplazador de Caracteres",
        )
    },
)
def create_character_replacer(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    char_to_replace: str,
    replacement_char: Optional[str],
) -> Any:
    """Create and execute a character replacer converter.

    Creates a CharacterReplacer converter in a notebook and enqueues its
    execution. The converter replaces a character or text sequence in selected
    text columns.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset text columns where replacement will be applied. At least one
        column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    char_to_replace : str
        Character or substring to replace. Must not be empty.
    replacement_char : str | None
        Replacement character or substring. If ``None``, the target sequence
        is removed.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="CharacterReplacer",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "char_to_replace": char_to_replace,
            "replacement_char": replacement_char,
        },
        order=order,
    )


@tool(
    "create_column_remover",
    args_schema=CreateColumnRemoverParams,
    description=(
        "Elimina del dataset las columnas especificadas en columns. "
        "Debe indicarse al menos una columna."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Column Remover",
            es="Ejecutar convertidor Eliminador de Columnas",
        )
    },
)
def create_column_remover(
    notebook_id: int, columns: list[ConverterColumn], order: int
) -> Any:
    """Create and execute a column remover converter.

    Creates a ColumnRemover converter in a notebook and enqueues its execution.
    The converter removes the selected columns from the dataset.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns to remove. At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="ColumnRemover",
        notebook_id=notebook_id,
        columns=columns,
        params={},
        order=order,
    )


@tool(
    "create_knn_imputer",
    args_schema=CreateKNNImputerParams,
    description=(
        "Imputa valores faltantes utilizando el promedio de los K vecinos más "
        "cercanos. A diferencia de los métodos basados en una estadística global "
        "por columna, estima cada valor a partir de muestras similares, preservando "
        "mejor la estructura y las relaciones locales de los datos.  Solo es válido "
        "este metodo con características numéricas."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute KNN Imputer", es="Ejecutar convertidor Imputador KNN"
        )
    },
)
def create_knn_imputer(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    n_neighbors: int,
    weights: Literal["uniform", "distance"],
    metric: Literal["nan_euclidean"],
    add_indicator: bool,
    keep_empty_features: bool,
) -> Any:
    """Create and execute a KNN imputer converter.

    Creates a KNNImputer converter in a notebook and enqueues its execution.
    The converter replaces missing values using information from the nearest
    neighboring samples.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset numerical columns where missing values will be imputed.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    n_neighbors : int
        Number of nearest neighbors used for imputation. Must be greater than
        or equal to 1.
    weights : str
        Weighting strategy for neighbors. Supported values are
        ``"uniform"`` and ``"distance"``.
    metric : str
        Distance metric used for nearest neighbor calculation. Currently
        supports ``"nan_euclidean"``.
    add_indicator : bool
        Whether to append missing-value indicator features to the output.
    keep_empty_features : bool
        Whether columns containing only missing values should be preserved.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="KNNImputer",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "n_neighbors": n_neighbors,
            "weights": weights,
            "metric": metric,
            "add_indicator": add_indicator,
            "keep_empty_features": keep_empty_features,
        },
        order=order,
    )


@tool(
    "create_missing_indicator",
    args_schema=CreateMissingIndicatorParams,
    description=(
        "Agrega columnas binarias que indican qué valores estaban ausentes en el "
        "dataset. Útil para que el modelo aprenda patrones de ausencia."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Missing Indicator",
            es="Ejecutar convertidor Indicador de Valores Faltantes",
        )
    },
)
def create_missing_indicator(
    notebook_id: int, columns: list[ConverterColumn], order: int
) -> Any:
    """Create and execute a missing indicator converter.

    Creates a MissingIndicator converter in a notebook and enqueues its
    execution. The converter adds binary features indicating whether values
    were missing in the selected columns.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where missing-value indicators will be generated.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="MissingIndicator",
        notebook_id=notebook_id,
        columns=columns,
        params={},
        order=order,
    )


@tool(
    "create_nan_remover",
    args_schema=CreateNanRemoverParams,
    description=(
        "Elimina filas que contengan valores NaN en las columnas del scope. "
        "Útil cuando la tasa de valores faltantes es baja.  "
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute NaN Remover",
            es="Ejecutar convertidor Eliminador de NaN",
        )
    },
)
def create_nan_remover(
    notebook_id: int, columns: list[ConverterColumn], order: int
) -> Any:
    """Create and execute a NaN remover converter.

    Creates a NanRemover converter in a notebook and enqueues its execution.
    The converter removes rows containing missing values in the selected
    columns.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns used to identify rows containing missing values.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="NanRemover",
        notebook_id=notebook_id,
        columns=columns,
        params={},
        order=order,
    )


@tool(
    "create_simple_imputer",
    args_schema=CreateSimpleImputerParams,
    description=(
        "Imputa valores faltantes con media, mediana, moda o una constante. "
        "La estrategia más sencilla y rápida de imputación."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Simple Imputer",
            es="Ejecutar convertidor Imputador Simple",
        )
    },
)
def create_simple_imputer(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    strategy: Literal["mean", "median", "most_frequent", "constant"],
    fill_value: Optional[Union[int, float, str]],
    add_indicator: bool,
    keep_empty_features: bool,
) -> Any:
    """Create and execute a Simple Imputer converter.

    Creates a SimpleImputer converter in a notebook and enqueues its execution.
    The converter replaces missing values in the selected columns using a
    specified strategy such as mean, median, most frequent value, or a constant.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Dataset columns where missing values will be imputed.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    strategy : {"mean", "median", "most_frequent", "constant"}
        Strategy used to replace missing values.
    fill_value : int, float, str or None
        Value used when the "constant" strategy is selected.
        Ignored for other strategies.
    add_indicator : bool
        Whether to append a MissingIndicator feature to the transformed output.
    keep_empty_features : bool
        Whether columns containing only missing values should be kept after
        transformation.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SimpleImputer",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "strategy": strategy,
            "fill_value": fill_value,
            "add_indicator": add_indicator,
            "keep_empty_features": keep_empty_features,
        },
        order=order,
    )


@tool(
    "create_bag_of_words",
    args_schema=CreateBagOfWordsParams,
    description=(
        "Convierte documentos de texto en una representación numérica basada en la "
        "frecuencia de aparición de palabras o secuencias de palabras (n-gramas). "
        "Cada característica corresponde a un término del vocabulario aprendido, "
        "mientras que los valores indican cuántas veces aparece en cada documento. "
        "Este enfoque ignora el orden y la estructura gramatical del texto."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Bag of Words", es="Ejecutar convertidor Bag of Words"
        )
    },
)
def create_bag_of_words(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    max_features: int,
    lowercase: bool,
    stop_words: Optional[Literal["english"]],
    lower_bound_ngrams: int,
    upper_bound_ngrams: int,
) -> Any:
    """Create and execute a Bag of Words converter.

    Creates a BagOfWords converter in a notebook and enqueues its execution.
    The converter transforms text documents into numerical representations
    based on term frequency using a vocabulary learned from the input data.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Text columns to transform into numerical features.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    max_features : int
        Maximum number of vocabulary terms to retain.
    lowercase : bool
        Whether to convert text to lowercase before tokenization.
    stop_words : {"english"} or None
        Stop words collection to remove during preprocessing.
    lower_bound_ngrams : int
        Minimum n-gram size to extract.
    upper_bound_ngrams : int
        Maximum n-gram size to extract.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="BagOfWordsConverter",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "max_features": max_features,
            "lowercase": lowercase,
            "stop_words": stop_words,
            "lower_bound_ngrams": lower_bound_ngrams,
            "upper_bound_ngrams": upper_bound_ngrams,
        },
        order=order,
    )


@tool(
    "create_embedding",
    args_schema=CreateEmbeddingParams,
    description=(
        "Genera embeddings densos de texto usando modelos de HuggingFace. Representa "
        "el significado semántico de cada texto como un vector."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Embedding", es="Ejecutar convertidor Embedding"
        )
    },
)
def create_embedding(
    notebook_id: int,
    columns: list[ConverterColumn],
    model_name: str,
    order: int,
    max_length: int,
    batch_size: int,
    device: Literal["cuda", "cpu"],
    pooling_strategy: Literal["mean", "cls", "max"],
) -> Any:
    """Create and execute an Embedding converter.

    Creates an Embedding converter in a notebook and enqueues its execution.
    The converter generates dense vector representations of text using
    pretrained HuggingFace models to capture semantic information.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Text columns used to generate embeddings.
        At least one column must be specified.
    model_name : str
        Name of the pretrained HuggingFace model used to generate embeddings.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    max_length : int
        Maximum sequence length used during tokenization.
    batch_size : int
        Number of text samples processed simultaneously.
    device : {"cuda", "cpu"}
        Computing device used for model inference.
    pooling_strategy : {"mean", "cls", "max"}
        Strategy used to aggregate token embeddings into a single vector.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="Embedding",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "model_name": model_name,
            "max_length": max_length,
            "batch_size": batch_size,
            "device": device,
            "pooling_strategy": pooling_strategy,
        },
        order=order,
    )


@tool(
    "create_tfidf",
    args_schema=CreateTFIDFParams,
    description=(
        "Transforma documentos de texto en vectores numéricos utilizando la "
        "ponderación TF-IDF (Term Frequency - Inverse Document Frequency). "
        "Asigna mayor relevancia a los términos frecuentes en un documento pero "
        "poco comunes en el conjunto de textos, reduciendo la influencia de palabras "
        "muy frecuentes y poco informativas."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute TF-IDF", es="Ejecutar convertidor TF-IDF"
        )
    },
)
def create_tfidf(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    max_features: int,
    lowercase: bool,
    stop_words: Optional[Literal["english"]],
    lower_bound_ngrams: int,
    upper_bound_ngrams: int,
) -> Any:
    """Create and execute a TF-IDF converter.

    Creates a TFIDF converter in a notebook and enqueues its execution.
    The converter transforms text documents into numerical vectors using the
    TF-IDF weighting scheme, emphasizing relevant terms while reducing the
    impact of common words.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Text columns to transform using TF-IDF.
        At least one column must be specified.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    max_features : int
        Maximum number of terms to keep in the learned vocabulary.
    lowercase : bool
        Whether to convert text to lowercase before tokenization.
    stop_words : {"english"} or None
        Stop words collection to remove during preprocessing.
    lower_bound_ngrams : int
        Minimum n-gram size to extract.
    upper_bound_ngrams : int
        Maximum n-gram size to extract.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="TFIDFConverter",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "max_features": max_features,
            "lowercase": lowercase,
            "stop_words": stop_words,
            "lower_bound_ngrams": lower_bound_ngrams,
            "upper_bound_ngrams": upper_bound_ngrams,
        },
        order=order,
    )


@tool(
    "create_tokenizer",
    args_schema=CreateTokenizerParams,
    description=(
        "Tokeniza texto en IDs de tokens usando un tokenizador de "
        "HuggingFace. Preparación para modelos Transformer."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Tokenizer", es="Ejecutar convertidor Tokenizer"
        )
    },
)
def create_tokenizer(
    notebook_id: int,
    columns: list[ConverterColumn],
    model_name: str,
    order: int,
    max_length: int,
    batch_size: int,
    device: Literal["cuda", "cpu"],
) -> Any:
    """Create and execute a Tokenizer converter.

    Creates a Tokenizer converter in a notebook and enqueues its execution.
    The converter tokenizes text inputs into model-compatible token IDs using
    a pretrained HuggingFace tokenizer.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Text columns to tokenize.
        At least one column must be specified.
    model_name : str
        Name of the pretrained tokenizer model.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    max_length : int
        Maximum sequence length used during tokenization.
    batch_size : int
        Number of samples processed simultaneously.
    device : {"cuda", "cpu"}
        Computing device used during tokenization.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="TokenizerConverter",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "model_name": model_name,
            "max_length": max_length,
            "batch_size": batch_size,
            "device": device,
        },
        order=order,
    )


@tool(
    "create_additive_chi2_sampler",
    args_schema=CreateAdditiveChi2SamplerParams,
    description=(
        "Transforma las características a un espacio de mayor dimensión para "
        "aproximar el kernel chi-cuadrado aditivo, permitiendo utilizar modelos "
        "lineales como una alternativa eficiente a los métodos kernel."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Additive Chi2 Sampler",
            es="Ejecutar convertidor Muestreador Chi2 Aditivo",
        )
    },
)
def create_additive_chi2_sampler(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    sample_steps: int,
    sample_interval: Optional[float],
) -> Any:
    """Create and execute an Additive Chi2 Sampler converter.

    Creates an AdditiveChi2Sampler converter in a notebook and enqueues its
    execution. The converter maps input features into a higher-dimensional
    feature space that approximates the additive chi-squared kernel.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature transformation.
        At least one column must be specified.
        Selected columns must not contain NaN values before execution.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    sample_steps : int
        Number of sampling steps used to approximate the kernel mapping.
    sample_interval : float or None
        Number of generated samples between each original sample.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="AdditiveChi2Sampler",
        notebook_id=notebook_id,
        columns=columns,
        params={"sample_steps": sample_steps, "sample_interval": sample_interval},
        order=order,
    )


@tool(
    "create_polynomial_features",
    args_schema=CreatePolynomialFeaturesParams,
    description=(
        "Genera características polinómicas e interacciones entre variables "
        "hasta un grado especificado. Permite capturar relaciones no lineales "
        "y efectos combinados entre características, facilitando que modelos "
        "lineales representen patrones más complejos. "
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Polynomial Features",
            es="Ejecutar convertidor Características Polinómicas",
        )
    },
)
def create_polynomial_features(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    degree: int,
    interaction_only: bool,
    include_bias: bool,
    poly_order: Literal["C", "F"],
) -> Any:
    """Create and execute a Polynomial Features converter.

    Creates a PolynomialFeatures converter in a notebook and enqueues its
    execution. The converter generates polynomial and interaction features up
    to a specified degree, enabling linear models to capture non-linear
    relationships and combined effects between features.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature transformation.
        Selected columns must not contain NaN values before execution.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    degree : int
        Degree of the polynomial features. Must be greater than or equal to 1.
        Defaults to 2.
    interaction_only : bool
        If True, only interaction features are produced: products of at most
        'degree' distinct input features. Defaults to False.
    include_bias : bool
        If True, includes a bias column (a column of ones acting as an
        intercept term). Defaults to True.
    poly_order : {"C", "F"}
        Order of the output array in the dense case. Order 'F' is faster to
        compute but may slow down subsequent estimators. Defaults to "C".

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="PolynomialFeatures",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "degree": degree,
            "interaction_only": interaction_only,
            "include_bias": include_bias,
            "order": poly_order,
        },
        order=order,
    )


@tool(
    "create_rbf_sampler",
    args_schema=CreateRBFSamplerParams,
    description=(
        "Genera una representación de características que aproxima el "
        "kernel RBF (gaussiano) mediante características aleatorias de Fourier. "
        "Esto permite utilizar modelos lineales para capturar relaciones no lineales "
        "similares a las de los métodos kernel, con un menor coste computacional."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute RBF Sampler",
            es="Ejecutar convertidor Muestreador RBF",
        )
    },
)
def create_rbf_sampler(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    gamma: Union[Literal["scale"], float],
    n_components: int,
    random_state: Optional[Union[int, Literal["RandomState"]]],
) -> Any:
    """Create and execute an RBF Sampler converter.

    Creates an RBFSampler converter in a notebook and enqueues its execution.
    The converter builds a feature representation that approximates the RBF
    (Gaussian) kernel using random Fourier features, allowing linear models to
    capture non-linear relationships similar to kernel methods at a lower
    computational cost.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature transformation.
        Selected columns must not contain NaN values before execution.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    gamma : "scale" or float
        Parameter of the RBF kernel. Defaults to "scale".
    n_components : int
        Number of features to construct. Must be greater than or equal to 1.
        Defaults to 100.
    random_state : int, "RandomState" or None
        Pseudo-random number generator used to control the random weights and
        offsets when fitting the data. Pass an int for reproducible results.
        Defaults to 0.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="RBFSampler",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "gamma": gamma,
            "n_components": n_components,
            "random_state": random_state,
        },
        order=order,
    )


@tool(
    "create_skewed_chi2_sampler",
    args_schema=CreateSkewedChi2SamplerParams,
    description=(
        "Genera una representación de características que aproxima el kernel "
        "chi-cuadrado sesgado mediante características aleatorias de Fourier. "
        "Está especialmente diseñado para datos basados en histogramas o conteos, "
        "permitiendo utilizar modelos lineales para aproximar métodos kernel de "
        "forma eficiente."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Skewed Chi2 Sampler",
            es="Ejecutar convertidor Muestreador Chi2 Sesgado",
        )
    },
)
def create_skewed_chi2_sampler(
    notebook_id: int,
    columns: list[ConverterColumn],
    order: int,
    skewedness: float,
    n_components: int,
    random_state: Optional[Union[int, Literal["RandomState"]]],
) -> Any:
    """Create and execute a Skewed Chi2 Sampler converter.

    Creates a SkewedChi2Sampler converter in a notebook and enqueues its
    execution. The converter builds a feature representation that approximates
    the skewed chi-squared kernel using random Fourier features. It is
    specifically designed for histogram- or count-based data, allowing linear
    models to efficiently approximate kernel methods.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature transformation.
        Selected columns must not contain NaN values before execution.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    skewedness : float
        Skewedness parameter of the chi-squared kernel. Must be strictly
        greater than 0.0. Defaults to 1.0.
    n_components : int
        Number of Monte Carlo samples per original feature, equivalent to the
        dimensionality of the computed feature space. Must be greater than or
        equal to 1. Defaults to 100.
    random_state : int, "RandomState" or None
        Pseudo-random number generator used to control the random weights and
        offsets when fitting the data. Pass an int for reproducible results.
        Defaults to None.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SkewedChi2Sampler",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "skewedness": skewedness,
            "n_components": n_components,
            "random_state": random_state,
        },
        order=order,
    )


@tool(
    "create_generic_univariate_select",
    args_schema=CreateGenericUnivariateSelectParams,
    description=(
        "Selecciona características usando un test estadístico univariado con modo "
        "configurable. Soporta múltiples modos de selección: k_best, percentile, fpr, "
        "fdr y fwe. La función de puntuación y el modo son configurables. "
        "Es supervisado: requiere y al momento de ajustar (fit). "
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Generic Univariate Select",
            es="Ejecutar convertidor Selección Univariada Genérica",
        )
    },
)
def create_generic_univariate_select(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    mode: Literal["percentile", "k_best", "fpr", "fdr", "fwe"],
    param: Optional[Union[int, float, Literal["all"]]],
) -> Any:
    """Create and execute a Generic Univariate Select converter.

    Creates a GenericUnivariateSelect converter in a notebook and enqueues its
    execution. The converter selects features using a univariate statistical
    test with a configurable mode. It supports multiple selection modes:
    k_best, percentile, fpr, fdr and fwe. The scoring function and mode are
    configurable. This converter is supervised: it requires a target (y) when
    fitting.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature selection.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected by the statistical test will be removed
        from the dataset copy present in the notebook.
    target_column : ConverterColumn
        Target column used to fit the selector. It must not be one of the
        columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    mode : {"percentile", "k_best", "fpr", "fdr", "fwe"}
        Feature selection mode to apply. Defaults to "percentile".
    param : int, float, "all" or None
        Parameter corresponding to the selected mode. Defaults to 1e-5.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="GenericUnivariateSelect",
        notebook_id=notebook_id,
        columns=columns,
        params={"mode": mode, "param": param},
        order=order,
        target=target_column,
    )


@tool(
    "create_select_fdr",
    args_schema=CreateSelectFdrParams,
    description=(
        "Selecciona características relevantes para la variable objetivo mediante "
        "pruebas estadísticas, controlando la tasa de falsos descubrimientos (FDR). "
        "Esto permite limitar la proporción esperada de variables irrelevantes entre "
        "las características seleccionadas, manteniendo un equilibrio entre detectar "
        "variables útiles y reducir falsos positivos. Es especialmente útil en "
        "conjuntos de datos de alta dimensionalidad donde se evalúan simultáneamente "
        "muchas características."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Select FDR", es="Ejecutar convertidor Selección FDR"
        )
    },
)
def create_select_fdr(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    alpha: float,
) -> Any:
    """Create and execute a Select FDR converter.

    Creates a SelectFdr converter in a notebook and enqueues its execution.
    The converter selects features relevant to the target variable through
    statistical tests, controlling the false discovery rate (FDR). This limits
    the expected proportion of irrelevant variables among the selected
    features, balancing the detection of useful variables with the reduction
    of false positives. It is especially useful in high-dimensional datasets
    where many features are evaluated simultaneously.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature selection.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected by the statistical test will be removed
        from the dataset copy present in the notebook.
    target_column : ConverterColumn
        Target column used to fit the selector. It must not be one of the
        columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    alpha : float
        Highest uncorrected p-value for a feature to be kept. Must be between
        0.0 and 1.0. Defaults to 0.05.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """

    return create_converter_and_enqueue(
        converter_type="SelectFdr",
        notebook_id=notebook_id,
        columns=columns,
        params={"alpha": alpha},
        order=order,
        target=target_column,
    )


@tool(
    "create_select_fpr",
    args_schema=CreateSelectFprParams,
    description=(
        "Selecciona características relevantes mediante pruebas estadísticas, "
        "conservando aquellas cuyo valor p es inferior a un umbral definido. "
        "Controla la tasa de falsos positivos (FPR), aunque sin aplicar correcciones "
        "por comparaciones múltiples, por lo que suele ser más permisivo que métodos "
        "como FDR o FWE."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Select FPR", es="Ejecutar convertidor Selección FPR"
        )
    },
)
def create_select_fpr(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    alpha: float,
) -> Any:
    """Create and execute a Select FPR converter.

    Creates a SelectFpr converter in a notebook and enqueues its execution.
    The converter selects relevant features through statistical tests,
    keeping those whose p-value is below a defined threshold. It controls
    the false positive rate (FPR) without applying multiple-comparison
    corrections, making it more permissive than methods such as FDR or FWE.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature selection.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected by the statistical test will be removed
        from the dataset copy present in the notebook.
    target_column : ConverterColumn
        Target column used to fit the selector. It must not be one of the
        columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    alpha : float
        Highest p-value for features to be kept. Must be between 0.0 and 1.0.
        Defaults to 0.05.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SelectFpr",
        notebook_id=notebook_id,
        columns=columns,
        params={"alpha": alpha},
        order=order,
        target=target_column,
    )


@tool(
    "create_select_fwe",
    args_schema=CreateSelectFweParams,
    description=(
        "Selecciona características mediante pruebas estadísticas y la corrección de "
        "Bonferroni, controlando la tasa de error familiar (FWE). Este enfoque limita "
        "la probabilidad de obtener falsos positivos entre todas las variables "
        "seleccionadas, siendo adecuado para estudios confirmatorios, aplicaciones "
        "críticas o escenarios donde cada característica seleccionada debe tener una "
        "alta confianza."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Select FWE", es="Ejecutar convertidor Selección FWE"
        )
    },
)
def create_select_fwe(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    alpha: float,
) -> Any:
    """Create and execute a Select FWE converter.

    Creates a SelectFwe converter in a notebook and enqueues its execution.
    The converter selects features through statistical tests and the
    Bonferroni correction, controlling the family-wise error rate (FWE). This
    approach limits the probability of obtaining false positives among all
    selected variables, making it suitable for confirmatory studies, critical
    applications, or scenarios where each selected feature must have high
    confidence.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature selection.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected by the statistical test will be removed
        from the dataset copy present in the notebook.
    target_column : ConverterColumn
        Target column used to fit the selector. It must not be one of the
        columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    alpha : float
        Highest uncorrected p-value for a feature to be kept. Must be between
        0.0 and 1.0. Defaults to 0.05.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SelectFwe",
        notebook_id=notebook_id,
        columns=columns,
        params={"alpha": alpha},
        order=order,
        target=target_column,
    )


@tool(
    "create_select_k_best",
    args_schema=CreateSelectKBestParams,
    description=(
        "Selecciona las k características más relevantes para la variable objetivo "
        "utilizando una prueba estadística univariada. Permite reducir la "
        "dimensionalidad conservando únicamente las variables con mayor capacidad "
        "predictiva, facilitando el entrenamiento de modelos más simples y eficientes."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Select K Best ",
            es="Ejecutar convertidor Selección K Mejor",
        )
    },
)
def create_select_k_best(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    k: Union[int, Literal["all"]],
) -> Any:
    """Create and execute a Select K Best converter.

    Creates a SelectKBest converter in a notebook and enqueues its execution.
    The converter selects the k features most relevant to the target variable
    using a univariate statistical test. This reduces dimensionality while
    keeping only the variables with the greatest predictive power, enabling
    simpler and more efficient model training.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature selection.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected by the statistical test will be removed
        from the dataset copy present in the notebook.
    target_column : ConverterColumn
        Target column used to fit the selector. It must not be one of the
        columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    k : int or "all"
        Number of top features to select. Defaults to 10.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SelectKBest",
        notebook_id=notebook_id,
        columns=columns,
        params={"k": k},
        order=order,
        target=target_column,
    )


@tool(
    "create_select_percentile",
    args_schema=CreateSelectPercentileParams,
    description=(
        "Selecciona las características más relevantes para la variable "
        "objetivo mediante pruebas estadísticas univariadas. El parámetro percentil "
        "determina el porcentaje de variables con mejor puntuación que se conservarán, "
        "permitiendo reducir la dimensionalidad de forma proporcional al tamaño del "
        "conjunto de características."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Select Percentile",
            es="Ejecutar convertidor Selección Percentil",
        )
    },
)
def create_select_percentile(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    percentile: int,
) -> Any:
    """Create and execute a Select Percentile converter.

    Creates a SelectPercentile converter in a notebook and enqueues its
    execution. The converter selects the features most relevant to the target
    variable through univariate statistical tests. The percentile parameter
    determines the percentage of top-scoring variables to keep, allowing
    dimensionality reduction proportional to the size of the feature set.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for feature selection.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected by the statistical test will be removed
        from the dataset copy present in the notebook.
    target_column : ConverterColumn
        Target column used to fit the selector. It must not be one of the
        columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    percentile : int
        Percentage of features to keep. Must be between 1 and 100. Defaults
        to 10.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SelectPercentile",
        notebook_id=notebook_id,
        columns=columns,
        params={"percentile": percentile},
        order=order,
        target=target_column,
    )


@tool(
    "create_random_under_sampler",
    args_schema=CreateRandomUnderSamplerParams,
    description=(
        "Balancea la distribución de clases eliminando aleatoriamente muestras de "
        "las clases mayoritarias. El parámetro sampling_strategy permite definir "
        "la proporción deseada entre clases tras el remuestreo, mientras que "
        "random_state controla la semilla utilizada para garantizar resultados "
        "reproducibles."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute Random Under Sampler",
            es="Ejecutar convertidor Submuestreador Aleatorio",
        )
    },
)
def create_random_under_sampler(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    sampling_strategy: Union[float, Literal["auto"]],
    random_state: Optional[Union[int, Literal["RandomState"]]],
) -> Any:
    """Create and execute a Random Under Sampler converter.

    Creates a RandomUnderSamplerConverter in a notebook and enqueues its
    execution. The converter balances the class distribution by randomly
    removing samples from the majority classes. The sampling_strategy
    parameter defines the desired proportion between classes after
    resampling, while random_state controls the seed used to guarantee
    reproducible results.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for resampling.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected will be removed from the dataset copy
        present in the notebook.
    target_column : ConverterColumn
        Target column used to determine class balance. It must not be one of
        the columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    sampling_strategy : float or "auto"
        Sampling strategy used to reduce the majority class. Defaults to
        "auto".
    random_state : int or None
        Seed used for reproducibility. Defaults to None.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="RandomUnderSamplerConverter",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "sampling_strategy": sampling_strategy,
            "random_state": random_state,
        },
        order=order,
        target=target_column,
    )


@tool(
    "create_smote",
    args_schema=CreateSMOTEParams,
    description=(
        "Balancea la distribución de clases generando nuevas muestras para "
        "las clases minoritarias a partir de sus vecinos más cercanos. El parámetro "
        "sampling_strategy define la proporción de muestras deseada tras el "
        "remuestreo, k_neighbors determina cuántos vecinos se utilizan para crear "
        "nuevas observaciones y random_state establece la semilla para garantizar "
        "resultados reproducibles."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generará error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute SMOTE", es="Ejecutar convertidor SMOTE"
        )
    },
)
def create_smote(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    sampling_strategy: Union[float, Literal["auto"]],
    random_state: Optional[int],
    k_neighbors: int,
) -> Any:
    """Create and execute a SMOTE converter.

    Creates a SMOTEConverter in a notebook and enqueues its execution. The
    converter balances the class distribution by generating new samples for
    the minority classes based on their nearest neighbors. The
    sampling_strategy parameter defines the desired sample proportion after
    resampling, k_neighbors determines how many neighbors are used to create
    new observations, and random_state sets the seed to guarantee
    reproducible results.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for resampling.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected will be removed from the dataset copy
        present in the notebook.
    target_column : ConverterColumn
        Target column used to determine class balance. It must not be one of
        the columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    sampling_strategy : float or "auto"
        Sampling strategy used to determine the size of the minority class.
        Defaults to "auto".
    random_state : int or None
        Seed used for reproducibility. Defaults to None.
    k_neighbors : int
        Number of neighbors used to generate synthetic samples. Must be
        greater than or equal to 1. Defaults to 5.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SMOTEConverter",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "sampling_strategy": sampling_strategy,
            "random_state": random_state,
            "k_neighbors": k_neighbors,
        },
        order=order,
        target=target_column,
    )


@tool(
    "create_smoteenn",
    args_schema=CreateSMOTEENNParams,
    description=(
        "Balancea conjuntos de datos desbalanceados mediante una estrategia híbrida "
        "que combina SMOTE y Edited Nearest Neighbours (ENN). Primero genera muestras "
        "sintéticas para las clases minoritarias utilizando sus k_neighbors vecinos "
        "más cercanos y luego elimina muestras potencialmente ruidosas o ambiguas "
        "mediante un proceso de limpieza. El parámetro sampling_strategy controla "
        "el nivel de balanceo deseado y random_state permite reproducir los "
        "resultados."
        "Si las columnas seleccionadas contienen valores NaN, no se podrá "
        "ejecutarse y se generará un error. Es por lo anterior que debes manejar "
        "los valores NaN antes de ejecutar el convertidor"
        "Las columnas que no fueron seleccionadas seran elimnadas de la "
        "copia del dataset presente en el notebook"
        "Al momento de seleccionar las columnas, la columna objetivo (target_column) "
        "no puede ser una columna que haya sido seleccionada en columns dado que de "
        "lo contrario, generara error."
    ),
    extras={
        "display_name": MultilingualString(
            en="Converter Execute SMOTE-ENN", es="Ejecutar convertidor SMOTE-ENN"
        )
    },
)
def create_smoteenn(
    notebook_id: int,
    columns: list[ConverterColumn],
    target_column: ConverterColumn,
    order: int,
    sampling_strategy: Union[float, Literal["auto"]],
    random_state: Optional[int],
    k_neighbors: int,
) -> Any:
    """Create and execute a SMOTE-ENN converter.

    Creates a SMOTEENNConverter in a notebook and enqueues its execution. The
    converter balances imbalanced datasets using a hybrid strategy that
    combines SMOTE and Edited Nearest Neighbours (ENN). It first generates
    synthetic samples for the minority classes using their k_neighbors
    nearest neighbors, and then removes potentially noisy or ambiguous
    samples through a cleaning process. The sampling_strategy parameter
    controls the desired balancing level, and random_state allows results to
    be reproduced.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the converter will be created.
    columns : list[ConverterColumn]
        Numerical columns used for resampling.
        Selected columns must not contain NaN values before execution.
        Columns that are not selected will be removed from the dataset copy
        present in the notebook.
    target_column : ConverterColumn
        Target column used to determine class balance. It must not be one of
        the columns specified in `columns`, otherwise an error will be raised.
    order : int
        Execution order of the converter within the transformation pipeline.
        Must be a non-negative integer.
    sampling_strategy : float or "auto"
        Sampling strategy used to apply SMOTE and clean the dataset. Defaults
        to "auto".
    random_state : int or None
        Seed used for reproducibility. Defaults to None.
    k_neighbors : int
        Number of neighbors used by SMOTE. Must be greater than or equal to
        1. Defaults to 5.

    Returns
    -------
    Any
        Information required to track the created converter and its execution.
    """
    return create_converter_and_enqueue(
        converter_type="SMOTEENNConverter",
        notebook_id=notebook_id,
        columns=columns,
        params={
            "sampling_strategy": sampling_strategy,
            "random_state": random_state,
            "k_neighbors": k_neighbors,
        },
        order=order,
        target=target_column,
    )


CONVERTER_TOOLS: list[BaseTool] = [
    get_converters,
    delete_converter_by_id,
    save_dataset_with_converter_transformations,
    create_binarizer,
    create_label_encoder,
    create_one_hot_encoder,
    create_ordinal_encoder,
    create_max_abs_scaler,
    create_min_max_scaler,
    create_normalizer,
    create_standard_scaler,
    create_fast_ica,
    create_incremental_pca,
    create_nystroem,
    create_pca,
    create_truncated_svd,
    create_variance_threshold,
    create_character_replacer,
    create_column_remover,
    create_knn_imputer,
    create_missing_indicator,
    create_nan_remover,
    create_simple_imputer,
    create_bag_of_words,
    create_embedding,
    create_tfidf,
    create_tokenizer,
    create_additive_chi2_sampler,
    create_polynomial_features,
    create_rbf_sampler,
    create_skewed_chi2_sampler,
    create_generic_univariate_select,
    create_select_fdr,
    create_select_fpr,
    create_select_fwe,
    create_select_k_best,
    create_select_percentile,
    create_random_under_sampler,
    create_smote,
    create_smoteenn,
]
