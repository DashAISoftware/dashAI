"""Dataset source API endpoints."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import HTTPException
from kink import di
from pydantic import BaseModel

from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.inf.type_inference import infer_types

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)
router = APIRouter()


def _resolve_string(value: Any, default: str) -> str:
    """Return the English text from a MultilingualString, or the value itself if plain str."""
    if isinstance(value, MultilingualString):
        return value.en
    if isinstance(value, str):
        return value
    return default


def _get_source(source_name: str, registry: "ComponentRegistry"):
    """Retrieve and instantiate a DatasetSource from the registry.

    Parameters
    ----------
    source_name : str
        Registered class name of the DatasetSource.
    registry : ComponentRegistry
        The component registry to look up.

    Returns
    -------
    BaseDatasetSource
        Instantiated source object.

    Raises
    ------
    HTTPException
        404 if source_name is not found in the DatasetSource registry.
    """
    sources = registry._registry.get("DatasetSource", {})
    if source_name not in sources:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DatasetSource '{source_name}' not found.",
        )
    return sources[source_name]["class"]()


@router.get("/", response_model=List[Dict[str, Any]])
async def list_sources(
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> List[Dict[str, Any]]:
    """Return all registered DatasetSource components.

    Parameters
    ----------
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    list[dict]
        List of source metadata dicts with name, type, display_name, description.
    """
    sources = registry._registry.get("DatasetSource", {})
    return [
        {
            "name": name,
            "type": "DatasetSource",
            "display_name": _resolve_string(info.get("display_name"), name),
            "description": _resolve_string(info.get("description"), ""),
        }
        for name, info in sources.items()
    ]


@router.get("/{source_name}/search")
async def search_datasets(
    source_name: str,
    q: str = Query(default="", description="Search query"),
    limit: int = Query(default=20, ge=1, le=100),
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> List[Dict[str, Any]]:
    """Search for datasets in a registered source.

    Parameters
    ----------
    source_name : str
        Registered DatasetSource class name.
    q : str
        Search query string.
    limit : int
        Maximum number of results (1-100).
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    list[dict]
        List of DatasetEntry dicts.
    """
    source = _get_source(source_name, registry)
    results = source.search(q, limit=limit)
    return [
        {
            "id": e.id,
            "name": e.name,
            "description": e.description,
            "tags": e.tags,
            "size_bytes": e.size_bytes,
            "row_count": e.row_count,
            "url": e.url,
            "source": e.source,
        }
        for e in results
    ]


@router.get("/{source_name}/{dataset_id:path}/download-url")
async def get_download_url(
    source_name: str,
    dataset_id: str,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> Dict[str, str]:
    """Return the direct download URL for a dataset.

    Parameters
    ----------
    source_name : str
        Registered DatasetSource class name.
    dataset_id : str
        Source-specific dataset identifier (URL-encoded).
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    dict
        ``{"url": "<download_url>"}``.
    """
    source = _get_source(source_name, registry)
    url = source.get_download_url(unquote(dataset_id))
    return {"url": url}


@router.get("/{source_name}/{dataset_id:path}/preview")
async def preview_dataset(
    source_name: str,
    dataset_id: str,
    n_rows: int = Query(default=100, ge=1, le=500),
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> Dict[str, Any]:
    """Fetch a sample preview of a dataset with inferred DashAI column types.

    Parameters
    ----------
    source_name : str
        Registered DatasetSource class name.
    dataset_id : str
        Source-specific dataset identifier (URL-encoded).
    n_rows : int
        Number of sample rows (1-500).
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    dict
        ``{"sample": [...], "inferred_types": {...}, "preview_row_count": int}``
        matching the format expected by the PreviewDataset frontend component.
    """
    source = _get_source(source_name, registry)
    decoded_id = unquote(dataset_id)

    try:
        df = source.fetch_preview(decoded_id, n_rows=n_rows)
    except Exception as exc:
        log.exception("Error fetching preview for %s/%s", source_name, decoded_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch preview from source: {exc}",
        ) from exc

    inferred = infer_types(df, method="DashAIPtype")
    sample = df.to_dict(orient="records")

    return {
        "sample": sample,
        "inferred_types": inferred,
        "preview_row_count": len(df),
    }


class ImportRequest(BaseModel):
    """Request body for the dataset import endpoint.

    Parameters
    ----------
    dataset_id : int
        ID of a pre-created Dataset DB record to populate.
    params : dict
        Parameters including ``inferred_types`` and ``column_renames``.
    """

    dataset_id: int
    params: Dict[str, Any] = {}


@router.post("/{source_name}/{dataset_id:path}/import", status_code=status.HTTP_201_CREATED)
async def import_dataset(
    source_name: str,
    dataset_id: str,
    body: ImportRequest,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue=Depends(lambda: di["job_queue"]),
) -> Dict[str, Any]:
    """Enqueue a DatasetJob to import a dataset from an external source.

    Parameters
    ----------
    source_name : str
        Registered DatasetSource class name.
    dataset_id : str
        Source-specific dataset identifier (URL-encoded).
    body : ImportRequest
        Contains the DashAI dataset_id and params.
    registry : ComponentRegistry
        Injected component registry.
    job_queue : BaseJobQueue
        Injected job queue.

    Returns
    -------
    dict
        ``{"job_id": int, "dataset_id": int}`` — the enqueued job and dataset IDs.
    """
    from DashAI.back.job.dataset_job import DatasetJob

    _get_source(source_name, registry)  # validates source exists, raises 404 if not

    job = DatasetJob(
        kwargs={
            "dataset_id": body.dataset_id,
            "source_name": source_name,
            "dataset_source_id": unquote(dataset_id),
            "params": body.params,
        }
    )
    job.set_status_as_delivered()
    result = job_queue.put(job)
    # huey.api.Result has .id (task UUID string); plain int in other modes
    job_id = getattr(result, "id", result)

    return {"job_id": job_id, "dataset_id": body.dataset_id}
