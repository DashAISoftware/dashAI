"""Endpoints to inspect and unload the models the job worker keeps loaded."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from DashAI.back.dependencies.database.models import LoadedModel

log = logging.getLogger(__name__)
router = APIRouter()


def _serialize(row: LoadedModel) -> dict:
    return {
        "id": row.id,
        "slot": row.slot,
        "label": row.label,
        "load_params": row.load_params,
        "ram_bytes": row.ram_bytes,
        "gpu_bytes": row.gpu_bytes,
        "loaded_at": row.loaded_at,
        "last_used_at": row.last_used_at,
        "in_use": row.in_use,
        "unload_requested": row.unload_requested,
    }


@router.get("/", status_code=status.HTTP_200_OK)
async def list_loaded_models(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Return the models the worker currently keeps loaded.

    Returns
    -------
    list[dict]
        One item per loaded model.
    """
    with session_factory() as db:
        rows = db.scalars(select(LoadedModel).order_by(LoadedModel.id)).all()
        return [_serialize(row) for row in rows]


@router.post("/{loaded_model_id}/unload", status_code=status.HTTP_202_ACCEPTED)
async def unload_loaded_model(
    loaded_model_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Ask the worker to unload a model.

    The worker unloads it as soon as the model is not in use.

    Parameters
    ----------
    loaded_model_id : int
        Id of the loaded model row.

    Raises
    ------
    HTTPException
        404 if the row does not exist.
    """
    with session_factory() as db:
        row = db.get(LoadedModel, loaded_model_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loaded model not found",
            )
        row.unload_requested = True
        db.commit()
        return _serialize(row)
