"""Dataset export API endpoints."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import HTTPException
from kink import di
from pydantic import BaseModel, ValidationError
from sqlalchemy import exc

from DashAI.back.core.enums.status import DatasetExportStatus, DatasetStatus
from DashAI.back.dependencies.database.models import Dataset, DatasetExport

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dataset_exporters.base_dataset_exporter import (
        BaseDatasetExporter,
    )
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)
router = APIRouter()

#: Statuses of an export whose job has not finished yet.
_IN_PROGRESS = (
    DatasetExportStatus.PENDING,
    DatasetExportStatus.PREPARING,
    DatasetExportStatus.UPLOADING,
)


class ValidateExportRequest(BaseModel):
    """Request body for checking an export without publishing it.

    Parameters
    ----------
    dataset_id : int
        DashAI dataset to export.
    params : dict
        Export parameters for the exporter's schema.
    """

    dataset_id: int
    params: Dict[str, Any] = {}


class CreateExportRequest(BaseModel):
    """Request body for publishing a dataset.

    Parameters
    ----------
    dataset_id : int
        DashAI dataset to export.
    exporter_name : str
        Registered DatasetExporter class name (e.g. ``OpenMLDatasetExporter``).
    params : dict
        Export parameters for the exporter's schema.
    """

    dataset_id: int
    exporter_name: str
    params: Dict[str, Any] = {}


def _row_to_dict(row: DatasetExport) -> Dict[str, Any]:
    return {
        "id": row.id,
        "dataset_id": row.dataset_id,
        "dataset_name": row.dataset_name,
        "exporter_name": row.exporter_name,
        "params": row.params or {},
        "status": row.status.value,
        "remote_id": row.remote_id,
        "remote_url": row.remote_url,
        "error_message": row.error_message,
        "huey_id": row.huey_id,
        "created": row.created.isoformat() if row.created else None,
        "last_modified": row.last_modified.isoformat() if row.last_modified else None,
    }


def _get_exporter_class(
    exporter_name: str, registry: "ComponentRegistry"
) -> type["BaseDatasetExporter"]:
    """Return a registered DatasetExporter class.

    Raises
    ------
    HTTPException
        404 if ``exporter_name`` is not a registered DatasetExporter.
    """
    exporters = registry._registry.get("DatasetExporter", {})
    if exporter_name not in exporters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DatasetExporter '{exporter_name}' not found.",
        )
    return exporters[exporter_name]["class"]


def _get_ready_dataset(dataset_id: int, session_factory: "sessionmaker") -> Dataset:
    """Return a dataset that finished loading.

    Raises
    ------
    HTTPException
        404 if the dataset does not exist, 409 if it is not ready yet.
    """
    with session_factory() as db:
        dataset = db.get(Dataset, dataset_id)
        if dataset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found.",
            )
        if dataset.status != DatasetStatus.FINISHED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset '{dataset.name}' is not ready.",
            )
        db.expunge(dataset)
        return dataset


def _schema_errors(error: ValidationError) -> List[str]:
    """Turn a pydantic error into one readable message per invalid field."""
    return [
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    ]


def _get_export(export_id: int, db) -> DatasetExport:
    row = db.get(DatasetExport, export_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset export {export_id} not found.",
        )
    return row


@router.post("/{exporter_name}/validate")
async def validate_export(
    exporter_name: str,
    body: ValidateExportRequest,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
) -> Dict[str, List[str]]:
    """Check a dataset and export parameters without publishing anything.

    Parameters
    ----------
    exporter_name : str
        Registered DatasetExporter class name.
    body : ValidateExportRequest
        Dataset id and export parameters.
    registry : ComponentRegistry
        Injected component registry.
    session_factory : sessionmaker
        Injected DB session factory.

    Returns
    -------
    dict
        ``{"errors": [...]}``; an empty list means the export can proceed.
    """
    from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

    exporter = _get_exporter_class(exporter_name, registry)()
    dataset_row = _get_ready_dataset(body.dataset_id, session_factory)

    try:
        params = exporter.SCHEMA.model_validate(body.params).model_dump()
    except ValidationError as e:
        return {"errors": _schema_errors(e)}

    dataset = load_dataset(str(Path(dataset_row.file_path) / "dataset"))
    return {"errors": exporter.validate(dataset, params)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_export(
    body: CreateExportRequest,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    job_queue=Depends(lambda: di["job_queue"]),
) -> Dict[str, Any]:
    """Create an export record and enqueue the job that publishes it.

    Parameters
    ----------
    body : CreateExportRequest
        Dataset id, exporter name and export parameters.
    registry : ComponentRegistry
        Injected component registry.
    session_factory : sessionmaker
        Injected DB session factory.
    job_queue : BaseJobQueue
        Injected job queue.

    Returns
    -------
    dict
        ``{"export_id": int, "job_id": str}``.

    Raises
    ------
    HTTPException
        404 if the exporter or dataset is missing, 409 if the dataset is not
        ready, 422 if a required credential is missing or the parameters do
        not match the exporter's schema.
    """
    from DashAI.back.job.dataset_export_job import DatasetExportJob

    exporter_class = _get_exporter_class(body.exporter_name, registry)
    dataset = _get_ready_dataset(body.dataset_id, session_factory)

    missing = [
        name
        for name in exporter_class.REQUIRED_CREDENTIALS
        if not registry[name]["class"]().is_authenticated()
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing credentials: {', '.join(missing)}.",
        )

    try:
        params = exporter_class.SCHEMA.model_validate(body.params).model_dump()
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_schema_errors(e),
        ) from e

    with session_factory() as db:
        row = DatasetExport(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            exporter_name=body.exporter_name,
            params=params,
            status=DatasetExportStatus.PENDING,
        )
        db.add(row)
        try:
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DB error creating the dataset export.",
            ) from e
        export_id = row.id

    job = DatasetExportJob(
        kwargs={"export_id": export_id, "dataset_name": dataset.name}
    )
    job.set_status_as_delivered()
    result = job_queue.put(job)
    # huey.api.Result has .id (task UUID string); plain int in other modes
    job_id = getattr(result, "id", result)

    # Store the task id now so the jobs panel can match the job to this export
    # before the worker starts it.
    with session_factory() as db:
        row = db.get(DatasetExport, export_id)
        if row is not None and not row.huey_id:
            row.huey_id = str(job_id)
            db.commit()

    return {"export_id": export_id, "job_id": job_id}


def _read_column_types(dataset_path: str) -> Dict[str, Any]:
    """Read a saved dataset's DashAI column types from its Arrow header only.

    Parameters
    ----------
    dataset_path : str
        ``Dataset.file_path`` of a finished dataset.

    Returns
    -------
    dict
        Column name mapped to its DashAI type.
    """
    import pyarrow as pa

    from DashAI.back.types.utils import get_types_from_arrow_metadata

    data_file = Path(dataset_path) / "dataset" / "data.arrow"
    with pa.OSFile(str(data_file), "rb") as source:
        schema = pa.ipc.open_file(source).schema
    return get_types_from_arrow_metadata(schema)


@router.get("/{exporter_name}/datasets")
async def list_exportable_datasets(
    exporter_name: str,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
) -> List[Dict[str, Any]]:
    """List the finished datasets and how well each fits the platform.

    Only the column types are read, never the data, so the whole list is
    cheap to build.

    Parameters
    ----------
    exporter_name : str
        Registered DatasetExporter class name.
    registry : ComponentRegistry
        Injected component registry.
    session_factory : sessionmaker
        Injected DB session factory.

    Returns
    -------
    list of dict
        One entry per finished dataset with its ``compatibility`` status,
        messages and the columns that would be left out.
    """
    from DashAI.back.dataset_exporters.base_dataset_exporter import (
        CompatibilityStatus,
        DatasetCompatibility,
    )

    exporter = _get_exporter_class(exporter_name, registry)()

    with session_factory() as db:
        datasets = (
            db.query(Dataset)
            .filter(Dataset.status == DatasetStatus.FINISHED)
            .order_by(Dataset.name)
            .all()
        )
        rows = [
            (d.id, d.name, d.total_rows, d.total_columns, d.file_path) for d in datasets
        ]

    result = []
    for dataset_id, name, total_rows, total_columns, file_path in rows:
        try:
            compatibility = exporter.check_dataset(_read_column_types(file_path))
        except Exception:
            log.exception("Could not read the column types of dataset %s", name)
            compatibility = DatasetCompatibility(
                status=CompatibilityStatus.INCOMPATIBLE,
                messages=["The column types of this dataset could not be read."],
            )
        result.append(
            {
                "id": dataset_id,
                "name": name,
                "total_rows": total_rows,
                "total_columns": total_columns,
                "compatibility": {
                    "status": compatibility.status.value,
                    "messages": compatibility.messages,
                    "unsupported_columns": compatibility.unsupported_columns,
                },
            }
        )
    return result


@router.get("/")
async def list_exports(
    dataset_id: Optional[int] = Query(default=None),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
) -> List[Dict[str, Any]]:
    """Return the export history, newest first, optionally for one dataset."""
    with session_factory() as db:
        query = db.query(DatasetExport)
        if dataset_id is not None:
            query = query.filter(DatasetExport.dataset_id == dataset_id)
        rows = query.order_by(DatasetExport.id.desc()).all()
        return [_row_to_dict(row) for row in rows]


@router.get("/{export_id}")
async def get_export(
    export_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
) -> Dict[str, Any]:
    """Return one export, including its status and published link."""
    with session_factory() as db:
        return _row_to_dict(_get_export(export_id, db))


@router.delete("/{export_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export(
    export_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
) -> None:
    """Delete the local export record.

    The dataset stays published on the platform. Exports still in progress
    cannot be deleted.
    """
    with session_factory() as db:
        row = _get_export(export_id, db)
        if row.status in _IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The export is still in progress.",
            )
        try:
            db.delete(row)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DB error deleting the dataset export.",
            ) from e
