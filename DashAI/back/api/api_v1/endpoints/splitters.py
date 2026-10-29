import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from pydantic import BaseModel
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import Dataset

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


class SplitPreviewParams(BaseModel):
    dataset_id: int
    splitter_name: str
    params: Dict[str, Any] = {}
    split_type: Optional[str] = None
    indexes: Optional[Dict[str, List[int]]] = None


@router.post("/preview")
@inject
async def preview_split(
    params: SplitPreviewParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Describe how a splitter would carve a dataset, for the session wizard.

    The wizard draws the answer and goes on only when it has no errors; the
    splitter computes it (``BaseSplitter.preview``) on the dataset's rows.

    Parameters
    ----------
    params : SplitPreviewParams
        The dataset, the splitter and its parameters; for a holdout, how it is
        given (``split_type``) and, typed by hand, its row ``indexes``. A
        predefined split reads the dataset's own partitions instead.

    Returns
    -------
    dict
        ``rows``, ``notes``, ``shares``, ``errors`` and ``partitions`` (see
        ``BaseSplitter.preview``), or None for a splitter with no preview.

    Raises
    ------
    HTTPException
        404 if the splitter or the dataset does not exist; 422 if the dataset
        is not ready or the parameters cannot be read by the splitter.
    """
    from DashAI.back.core.enums.status import DatasetStatus
    from DashAI.back.dataloaders.classes.dashai_dataset import get_dataset_info

    splitter_name = params.splitter_name
    if (
        splitter_name not in component_registry
        or component_registry[splitter_name]["type"] != "Splitter"
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Splitter {splitter_name} not found",
        )
    splitter = component_registry[splitter_name]["class"]

    with session_factory() as db:
        try:
            dataset = db.get(Dataset, params.dataset_id)
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
            )
        if dataset.status != DatasetStatus.FINISHED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dataset is not in finished state",
            )
        info = get_dataset_info(f"{dataset.file_path}/dataset")

    indexes = params.indexes
    if params.split_type == "predefined":
        indexes = {
            "train": info.get("train_indices", []),
            "validation": info.get("val_indices", []),
            "test": info.get("test_indices", []),
        }

    try:
        return splitter.preview(
            params.params,
            {
                "total_rows": info.get("total_rows", 0),
                "train_size": info.get("train_size", 0),
                "val_size": info.get("val_size", 0),
                "test_size": info.get("test_size", 0),
            },
            params.split_type,
            indexes,
        )
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{splitter_name} cannot read these parameters: {e}",
        ) from e
