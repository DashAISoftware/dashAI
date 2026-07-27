from typing import Any

import requests
from langchain.tools import tool
from langchain_core.tools import BaseTool

from DashAI.back.core.utils import MultilingualString
from DashAI.back.pydantic_models.notebooks_models import (
    DeleteNotebook,
    GetDatasetRowsByNotebookIdParams,
    GetNotebookExplorerListByNotebookId,
    UploadNotebook,
)


@tool(
    "upload_notebook",
    args_schema=UploadNotebook,
    description=(
        "Crea un nuevo notebook en DashAI vinculado a un dataset existente. "
        "El notebook es el espacio donde se generan exploradores y análisis."
    ),
    extras={
        "display_name": MultilingualString(
            en="Upload notebook to DashAI", es="Subir notebook a DashAI"
        )
    },
)
def upload_notebook(
    dataset_id: int, name: str | None = None, description: str | None = None
) -> str:
    """Create a notebook associated with an existing dataset.

    Parameters
    ----------
    dataset_id : int
        Identifier of an existing dataset in DashAI. The notebook will be
        created using this dataset as its data source.
    name : str | None, default=None
        Optional notebook name. If omitted, DashAI assigns its default value.
    description : str | None, default=None
        Optional notebook description.

    Returns
    -------
    str
        Success message if the notebook is created successfully, otherwise
        an error message describing the failure.
    """
    endpoint = "http://localhost:8000/api/v1/notebook/"
    try:
        response = requests.post(
            endpoint,
            json={"name": name, "description": description, "dataset_id": dataset_id},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 201:
            return (
                "Se ha ejecutado de manera exitosa la creación del notebook en "
                "la plataforma"
            )
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al crear el notebook: {exc}"


@tool(
    "delete_notebook",
    args_schema=DeleteNotebook,
    description=(
        "Elimina un notebook de DashAI usando su notebook_id. "
        "Esta acción elimina también todos los exploradores creados en él."
    ),
    extras={
        "display_name": MultilingualString(
            en="Delete notebook from DashAI", es="Eliminar notebook de DashAI"
        )
    },
)
def delete_notebook(notebook_id: int) -> str:
    """Delete an existing notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook to remove.

    Returns
    -------
    str
        Confirmation message if the notebook is deleted successfully,
        otherwise an error message.
    """
    endpoint = f"http://localhost:8000/api/v1/notebook/{notebook_id}"
    try:
        response = requests.delete(
            endpoint, headers={"Content-Type": "application/json"}
        )
        if response.status_code == 204:
            return (
                f"Se ha ejecutado de manera exitosa la eliminacion del notebook "
                f"{notebook_id} de la plataforma"
            )

        return f"Error al eliminar el notebook: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error durante la eliminacion del notebook: {exc}"


@tool(
    "get_notebooks",
    description=(
        "Lista todos los notebooks creados en DashAI con información como su ID, "
        "nombre y dataset asociado."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get notebooks from DashAI", es="Obtener notebooks de DashAI"
        )
    },
)
def get_notebooks() -> list[Any] | str:
    """Retrieve all notebooks available in DashAI.

    Returns
    -------
    list[Any] | str
        List containing the notebook metadata returned by DashAI or an
        error message if the request cannot be completed.
    """
    endpoint = "http://localhost:8000/api/v1/notebook/"
    try:
        response = requests.get(endpoint, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return f"La herramienta se ha ejecutado con éxito: {response.json()}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los notebooks: {exc}"


@tool(
    "get_notebook_explorer_list_by_notebook_id",
    args_schema=GetNotebookExplorerListByNotebookId,
    description=(
        "Lista todos los exploradores (gráficos y visualizaciones) que han sido "
        "creados en un notebook específico."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get notebook explorers by notebook ID",
            es="Obtener exploradores de notebook por ID",
        )
    },
)
def get_notebook_explorer_list_by_notebook_id(notebook_id: int) -> list[Any] | str:
    """Retrieve all explorers associated with a notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook whose explorers will be listed.

    Returns
    -------
    list[Any] | str
        List containing the explorers associated with the notebook or
        an error message if the request fails.
    """
    endpoint = f"http://localhost:8000/api/v1/notebook/{notebook_id}/explorers"
    try:
        response = requests.get(endpoint, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return f"La herramienta se ha ejecutado con éxito: {response.json()}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los explorers del notebook: {exc}"


@tool(
    "get_rows_dataset_by_notebook_id",
    args_schema=GetDatasetRowsByNotebookIdParams,
    description=(
        "Dado un notebook_id, obtiene las filas del dataset asociado a ese notebook "
        "dentro de un rango específico."
        "Si el notebook ha ejecutado convertidores que transforman la copia del "
        "dataset, se obtendrán las filas de la versión transformada del dataset."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get dataset info and sample by notebook ID",
            es="Obtener información y muestra del dataset por ID de notebook",
        )
    },
)
def get_rows_dataset_by_notebook_id(
    notebook_id: int, start_row: int = 0, end_row: int = 5
) -> Any:
    """Retrieve sample rows from the dataset associated with a notebook.

    If the notebook contains dataset transformations performed through
    converters, the returned rows correspond to the transformed dataset.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook.
    start_row : int, default=0
        Zero-based index of the first row to include.
    end_row : int, default=5
        Index of the first row not included in the returned sample.

    Returns
    -------
    Any
        Human-readable message containing the requested dataset rows or an
        error message if the operation cannot be completed.
    """

    notebook_url = f"http://localhost:8000/api/v1/notebook/{notebook_id}"
    try:
        nb_response = requests.get(
            notebook_url, headers={"Content-Type": "application/json"}
        )
        if nb_response.status_code != 200:
            return (
                f"Error al obtener el notebook: "
                f"{nb_response.status_code} - {nb_response.text}"
            )
        notebook_data = nb_response.json()
        file_path = notebook_data.get("file_path")
        if not file_path:
            return "Error: el notebook no tiene una ruta de archivo asociada."
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor."
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener el notebook: {exc}"

    from urllib.parse import quote

    encoded_path = quote(file_path, safe="")

    file_url = f"http://localhost:8000/api/v1/dataset/file/?path={encoded_path}&page=0&page_size=5"
    try:
        file_response = requests.get(file_url)
        if file_response.status_code != 200:
            file_result = f"Error {file_response.status_code}: {file_response.text}"
        else:
            file_result = file_response.json()
    except requests.exceptions.RequestException as exc:
        file_result = f"Error al consultar muestra del archivo: {exc}"

    rows = file_result.get("rows")
    selected_rows = rows[start_row:end_row] if rows else []

    return (
        f"A continuación se muestran las filas entre el indice {start_row} y "
        f"{end_row}: \n {selected_rows}"
    )


@tool(
    "get_notebook_converters_list_by_notebook_id",
    args_schema=GetNotebookExplorerListByNotebookId,
    description=(
        "Lista todos los conversores (transformaciones y procesamientos) que "
        "han sido aplicados en un notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get notebook converters by notebook ID",
            es="Obtener conversores de notebook por ID",
        )
    },
)
def get_notebook_converters_list_by_notebook_id(notebook_id: int) -> list[Any] | str:
    """Retrieve the converters associated with a notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook whose converters will be listed.

    Returns
    -------
    list[Any] | str
        List containing the converters associated with the notebook or
        an error message if the request fails.
    """
    endpoint = f"http://localhost:8000/api/v1/notebook/{notebook_id}/converters"
    try:
        response = requests.get(endpoint, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return f"La herramienta se ha ejecutado con éxito: {response.json()}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los converters del notebook: {exc}"


NOTEBOOK_TOOLS: list[BaseTool] = [
    upload_notebook,
    delete_notebook,
    get_notebooks,
    get_notebook_explorer_list_by_notebook_id,
    get_rows_dataset_by_notebook_id,
    get_notebook_converters_list_by_notebook_id,
]
