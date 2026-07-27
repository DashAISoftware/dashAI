import json
import os
import time
from typing import Any, Union
from urllib.parse import quote

import requests
from langchain.tools import tool
from langchain_core.tools import BaseTool

from DashAI.back.core.utils import MultilingualString
from DashAI.back.pydantic_models.datasets_models import (
    CSVUploadParams,
    DeleteDataset,
    ExcelUploadParams,
    GetColumnsByNameInput,
    GetDatasetInfoByName,
    GetDatasetRowsWithRoot,
    JSONUploadParams,
    UploadDataset,
)


@tool(
    "read_dataset_rows_with_root",
    args_schema=GetDatasetRowsWithRoot,
    description=(
        "Inspecciona un archivo de dataset (CSV, JSON o Excel) antes de cargarlo.  "
        "Muestra las primeras n filas y devuelve los parámetros recomendados para "
        "usar en upload_dataset según el formato y estructura detectados."
    ),
    extras={
        "display_name": MultilingualString(
            en="Read rows from dataset prior loading on platform",
            es="Leer filas de dataset antes de cargar en plataforma",
        )
    },
)
def read_dataset_rows_with_root(root: str, number_rows_to_read: int) -> list | str:
    """Read a local dataset file and return a preview of its contents.

    Loads the first rows of a CSV, JSON, Excel, or OpenDocument spreadsheet
    without importing it into DashAI. This tool is intended to inspect the
    dataset structure before calling ``upload_dataset``.

    Parameters
    ----------
    root : str
        Absolute or relative path to the dataset file.
    number_rows_to_read : int
        Number of rows to include in the preview.

    Returns
    -------
    str
        A formatted preview containing the first rows of the dataset or an
        error message if the file cannot be read or its format is not
        supported.
    """
    import pandas as pd

    file_ext = os.path.splitext(root)[-1].lower()
    try:
        if file_ext == ".csv":
            dataset = pd.read_csv(root, nrows=number_rows_to_read)

        elif file_ext in (".xlsx", ".xls", ".xlsm", ".xlsb", ".odf", ".ods", ".odt"):
            xl_file = pd.ExcelFile(root)
            dataset = xl_file.parse(sheet_name=0, nrows=number_rows_to_read)

        elif file_ext == ".json":
            dataset = pd.read_json(root, lines=True, nrows=number_rows_to_read)

        else:
            return (
                f"Formato de archivo no soportado: '{file_ext}'. Use CSV, JSON, "
                "Excel (.xlsx, .xls, .xlsm, .xlsb) u OpenDocument (.odf, .ods, .odt)."
            )

        return (
            f"Primeras {number_rows_to_read} filas de '{os.path.basename(root)}': "
            f"{dataset.head(number_rows_to_read).to_string(index=False)}"
        )

    except Exception as exc:
        return f"Error al leer el archivo '{root}': {exc}"


@tool(
    "upload_dataset",
    args_schema=UploadDataset,
    description=(
        "Carga un archivo local (CSV, JSON o Excel) como nuevo dataset en "
        "DashAI. Infiere automáticamente los tipos de columnas y lo importa "
        "con los parámetros del dataloader correspondiente."
    ),
    extras={
        "display_name": MultilingualString(
            en="Upload Dataset File", es="Cargar archivo de dataset"
        )
    },
)
def upload_dataset(
    file_path: str,
    name: str,
    inference_rows: int,
    extra_params: Union[CSVUploadParams, JSONUploadParams, ExcelUploadParams],
) -> str:
    """Upload a local dataset into the DashAI platform.

    Creates a new dataset, infers the column types using the corresponding
    dataloader, enqueues the dataset import job, and monitors its execution
    for a limited period before returning the final status.

    Parameters
    ----------
    file_path : str
        Path to the dataset file to upload.
    name : str
        Name assigned to the dataset in DashAI.
    inference_rows : int
        Number of rows used to infer the dataset column types.
    extra_params : CSVUploadParams | JSONUploadParams | ExcelUploadParams
        Dataloader-specific parameters required to correctly parse the input
        file according to its format.

    Returns
    -------
    str
        A status message indicating whether the dataset was uploaded
        successfully, the import job is still running, or an error occurred
        during the upload process.
    """
    url_preview = "http://localhost:8000/api/v1/dataset/preview_with_types"
    url_dataset = "http://localhost:8000/api/v1/dataset/"
    url_enqueue_job = "http://localhost:8000/api/v1/job/"

    dataloader_name = extra_params.dataloader
    filename = os.path.basename(file_path)

    preview_params = {"inference_rows": inference_rows, "name": name}

    if isinstance(extra_params, CSVUploadParams):
        preview_params.update(
            {
                "separator": extra_params.separator,
                "header": extra_params.header,
                "names": extra_params.names,
                "encoding": extra_params.encoding,
                "na_values": extra_params.na_values,
                "keep_default_na": extra_params.keep_default_na,
                "true_values": extra_params.true_values,
                "false_values": extra_params.false_values,
                "skip_blank_lines": extra_params.skip_blank_lines,
                "skiprows": extra_params.skiprows,
                "nrows": extra_params.nrows,
                "dataloader_name": dataloader_name,
            }
        )
    elif isinstance(extra_params, JSONUploadParams):
        preview_params.update(
            {
                "data_key": extra_params.data_key,
                "dataloader_name": dataloader_name,
            }
        )
    elif isinstance(extra_params, ExcelUploadParams):
        preview_params.update(
            {
                "sheet": extra_params.sheet,
                "header": extra_params.header,
                "usecols": extra_params.usecols,
                "skiprows": extra_params.skiprows,
                "nrows": extra_params.nrows,
                "names": extra_params.names,
                "na_values": extra_params.na_values,
                "keep_default_na": extra_params.keep_default_na,
                "true_values": extra_params.true_values,
                "false_values": extra_params.false_values,
                "dataloader_name": dataloader_name,
            }
        )

    try:
        with open(file_path, "rb") as dataset_file:
            preview_resp = requests.post(
                url_preview,
                data={"params": json.dumps(preview_params)},
                files={"file": (filename, dataset_file)},
            )
        if preview_resp.status_code != 200:
            return (
                f"Error al obtener los tipos inferidos del dataset: "
                f"{preview_resp.status_code} - {preview_resp.text}.  "
                f"Si la falla sucede al intentar subir un archivo json, "
                f"posiblemente seleccionaste el data_key incorrecto.  "
                f"Revisa la estructura del json y sigue las indicaciones "
                f"asociadas al campo data_key."
            )
        inferred_types = preview_resp.json().get("inferred_types", {})
    except Exception as exc:
        return f"Error al llamar al endpoint de previsualización: {exc}"

    try:
        create_resp = requests.post(
            url_dataset,
            json={"name": name, "notebook_id": None},
            headers={"Content-Type": "application/json"},
        )
        if create_resp.status_code == 409:
            return (
                f"Error: ya existe un dataset con el nombre '{name}'. Usa un "
                f"nombre diferente."
            )

        if create_resp.status_code != 201:
            return (
                f"Error al crear el registro del dataset: "
                f"{create_resp.status_code} - {create_resp.text}"
            )

        dataset_id = create_resp.json()["id"]
    except Exception as exc:
        return f"Error al crear el registro del dataset: {exc}"

    params_dict = dict(preview_params)
    params_dict["dataloader"] = dataloader_name
    params_dict["inferred_types"] = inferred_types

    kwargs = {
        "dataset_id": dataset_id,
        "notebook_id": None,
        "url": "",
        "params": params_dict,
    }
    kwargs_json = json.dumps(kwargs)
    req_headers = {"filename": quote(filename)}

    try:
        with open(file_path, "rb") as dataset_file:
            files = {
                "job_type": (None, "DatasetJob"),
                "kwargs": (None, kwargs_json),
                "file": (filename, dataset_file),
            }
            enqueue_resp = requests.post(
                url_enqueue_job, files=files, headers=req_headers
            )
        if enqueue_resp.status_code != 201:
            return (
                f"Error al encolar el trabajo del dataset: {enqueue_resp.status_code} "
                f"- {enqueue_resp.text}"
            )

        job_id = enqueue_resp.json().get("id")
    except Exception as exc:
        return f"Ha ocurrido un error durante la carga del dataset: {exc}"

    url_job_status = f"http://localhost:8000/api/v1/job/status/{job_id}"
    for _ in range(7):
        time.sleep(5)
        try:
            status_resp = requests.get(url_job_status)
            if status_resp.status_code == 200:
                job_status = status_resp.json().get("status", "")
                if job_status == "finished":
                    return (
                        f"El dataset '{name}' con ID {dataset_id} ha sido cargado "
                        f"exitosamente."
                    )
                if job_status == "error":
                    error_msg = status_resp.json().get("error") or "desconocido"
                    return (
                        f"El trabajo de carga del dataset '{name}' terminó con "
                        f"error: {error_msg}"
                    )

        except Exception:
            pass

    return (
        f"El dataset '{name}' con ID {dataset_id} fue encolado exitosamente, pero "
        f"han transcurrido 35 segundos desde el encolamiento y el proceso aún está "
        f"en curso. El proceso continúa ejecutándose en segundo plano."
    )


@tool(
    "delete_dataset",
    args_schema=DeleteDataset,
    description=(
        "Elimina un dataset existente de DashAI usando su dataset_id. Esta "
        "acción es irreversible y también elimina los notebooks asociados."
    ),
    extras={
        "display_name": MultilingualString(en="Delete Dataset", es="Eliminar dataset")
    },
)
def delete_dataset(dataset_id: int) -> str:
    """Delete a dataset from the DashAI platform.

    Permanently removes the dataset identified by ``dataset_id`` together with
    any associated resources managed by the platform.

    Parameters
    ----------
    dataset_id : int
        Identifier of the dataset to delete.

    Returns
    -------
    str
        A message indicating whether the dataset was deleted successfully or
        describing the error encountered during the deletion process.
    """
    endpoint = f"http://localhost:8000/api/v1/dataset/{dataset_id}"
    try:
        response = requests.delete(
            endpoint, headers={"Content-Type": "application/json"}
        )
        if response.status_code == 204:
            return (
                f"Se ha ejecutado de manera exitosa la eliminación del dataset "
                f"{dataset_id} de la plataforma"
            )

        return f"Error al eliminar el dataset: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error durante la eliminacion del dataset: {exc}"


@tool(
    "get_datasets",
    description=(
        "Lista todos los datasets cargados actualmente en DashAI. Devuelve "
        "información como nombre, ID y ruta de cada dataset."
    ),
    extras={
        "display_name": MultilingualString(
            en="List Available Datasets", es="Listar datasets disponibles"
        )
    },
)
def get_datasets() -> list[Any] | str:
    """Retrieve all datasets available in the DashAI platform.

    Queries the dataset service and returns the list of datasets currently
    registered in the platform together with their associated metadata.

    Returns
    -------
    list[Any] | str
        A list containing the available datasets if the request succeeds, or
        an error message if the datasets cannot be retrieved.
    """
    endpoint = "http://localhost:8000/api/v1/dataset/"
    try:
        response = requests.get(endpoint, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return response.json()
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los datasets: {exc}"


@tool(
    "get_dataset_info_by_name",
    args_schema=GetDatasetInfoByName,
    description=(
        "Obtiene información detallada de un dataset a partir de su nombre exacto. "
        "Retorna:\n"
        "- total_rows: número total de filas del dataset\n"
        "- total_columns: número total de columnas\n"
        "- column_names: lista con los nombres de las columnas\n"
        "- nan: conteo de valores nulos por columna\n"
        "- train_size / test_size / val_size: tamaño de los conjuntos de "
        "entrenamiento, prueba y validación\n"
        "- train_indices / test_indices / val_indices: índices de las filas asignadas "
        "a cada conjunto\n"
        "- general_info: tipos de datos por columna (dtypes), filas duplicadas, uso "
        "de memoria en MB, cantidad de filas y columnas\n"
        "- numeric_stats: por cada columna numérica: max, min, media, mediana, "
        "cuartiles (q1, q3), desviación estándar, curtosis, asimetría, límite "
        "superior e inferior, valores únicos y cantidad de outliers\n"
        "- categorical_stats: por cada columna categórica: valor más frecuente "
        "y su conteo, cantidad de valores únicos, top 5 valores\n"
        "- correlations: matriz de correlaciones entre columnas numéricas\n"
        "- quality_info: puntuación de calidad del dataset (data_quality_score), "
        "columnas constantes, columnas con alta cardinalidad, posibles columnas de "
        "ID, ratio de NaN por columna, filas con al menos un NaN y filas con "
        "múltiples NaN\n"
        "- text_stats: por cada columna de texto: longitud promedio, mediana, "
        "mínima y máxima, conteo promedio de palabras, cantidad de valores únicos "
        "y ratio de unicidad"
    ),
    extras={
        "display_name": MultilingualString(
            en="Get Dataset Info by Name",
            es="Obtener información del dataset por nombre",
        )
    },
)
def get_dataset_info_by_name(dataset_name: str) -> dict[str, Any] | str:
    """Retrieve detailed information about a dataset by its name.

    Searches for a dataset with the specified name and returns descriptive
    statistics, quality metrics, column information, correlations, and other
    metadata generated by the dataset analysis service.

    Parameters
    ----------
    dataset_name : str
        Exact name of the dataset to inspect.

    Returns
    -------
    dict[str, Any] | str
        A dictionary containing the dataset information if the dataset is
        found, or an error message if the lookup or analysis fails.
    """
    endpoint_base = "http://localhost:8000/api/v1/dataset/"
    try:
        response = requests.get(
            endpoint_base, headers={"Content-Type": "application/json"}
        )
        if response.status_code != 200:
            return f"Error al obtener los datasets: {response.status_code}"
        datasets = response.json()
        dataset = next(
            (item for item in datasets if item.get("name") == dataset_name), None
        )
        if not dataset:
            return f"No se encontró un dataset con el nombre '{dataset_name}'"
        file_path = dataset.get("file_path")
        if not file_path:
            return f"El dataset '{dataset_name}' no tiene ruta de archivo asociada."
        response_info = requests.get(
            endpoint_base + "file/info",
            params={"path": file_path},
            headers={"Content-Type": "application/json"},
        )
        if response_info.status_code == 200:
            return response_info.json()
        return (
            f"Error al obtener la información del dataset: {response_info.status_code}"
        )

    except Exception as exc:
        return f"Error durante la consulta de información del dataset: {exc}"


@tool(
    "get_column_with_types_by_name",
    args_schema=GetColumnsByNameInput,
    description=(
        "Obtiene las columnas de un dataset con sus tipos de datos a partir del "
        "nombre del dataset en DashAI. Retorna una lista de columnas con los "
        "campos columnName, valueType, dataType, id y order, listas para usar "
        "directamente en herramientas de exploradores."
        "No permite obtener las columnas de copias del dataset presentes en "
        "notebooks."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get Columns with Types by Dataset Name",
            es="Obtener columnas con tipos por nombre de dataset",
        )
    },
)
def get_column_with_types_by_name(dataset_name: str) -> list[dict] | str:
    """Retrieve the columns and their data types for a dataset.

    Searches for a dataset by its name and returns its columns formatted as
    ExplorerColumn objects, including the column name, logical type, physical
    data type, identifier, and display order.

    Parameters
    ----------
    dataset_name : str
        Exact name of the dataset whose columns will be retrieved.

    Returns
    -------
    list[dict] | str
        A list of ExplorerColumn dictionaries describing the dataset columns,
        or an error message if the dataset cannot be found or queried.
    """
    endpoint1 = "http://localhost:8000/api/v1/dataset/"
    try:
        response1 = requests.get(
            endpoint1, headers={"Content-Type": "application/json"}
        )
        if response1.status_code != 200:
            return f"Error al obtener los datasets: {response1.status_code}"
        datasets = response1.json()
        dataset = next((d for d in datasets if d.get("name") == dataset_name), None)
        if not dataset:
            return f"No se encontró un dataset con el nombre '{dataset_name}'"
        dataset_id = dataset.get("id")
        if not dataset_id:
            return f"El dataset '{dataset_name}' no tiene ID asociado."
    except Exception as exc:
        return f"Error al buscar el dataset: {exc}"

    endpoint2 = f"http://localhost:8000/api/v1/dataset/{dataset_id}/types"
    try:
        response2 = requests.get(
            endpoint2, headers={"Content-Type": "application/json"}
        )
        if response2.status_code != 200:
            return (
                f"Error al obtener las columnas: "
                f"{response2.status_code}-{response2.text}"
            )
        columns = response2.json()
    except Exception as exc:
        return f"Error durante la consulta de columnas: {exc}"
    result = []
    for order, (col_name, col_info) in enumerate(columns.items(), start=1):
        result.append(
            {
                "columnName": col_name,
                "valueType": col_info.get("type", ""),
                "dataType": col_info.get("dtype", ""),
                "id": order - 1,
                "order": order,
            }
        )
    return result


DATASET_TOOLS: list[BaseTool] = [
    read_dataset_rows_with_root,
    upload_dataset,
    delete_dataset,
    get_datasets,
    get_dataset_info_by_name,
    get_column_with_types_by_name,
]
