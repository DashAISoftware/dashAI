import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from pydantic import BaseModel, ValidationError
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import Dataset
from DashAI.back.splitters.splits_payload import (
    INDEX_KEY_BY_SPLIT,
    INDEX_SPLIT_TYPES,
    validate_splitter_parameters,
)

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
def preview_split(
    params: SplitPreviewParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Describe how a splitter would carve a dataset, for the session wizard.

    The wizard draws the answer and goes on only when it has no errors; the
    splitter computes it (``BaseSplitter.preview``) on the dataset's rows.
    A configuration the preview finds no fault with is then checked against
    the splitter's schema, as creating the session checks it, so the wizard
    does not go on with one the session would refuse.

    The wizard asks again as the form changes, so the rows are counted from
    the dataset's ``total_rows``. Its ``splits.json``, which holds every index
    list, is read only for a predefined split, which draws those partitions,
    or for a dataset from before ``total_rows`` was filled. A plain ``def``:
    FastAPI runs it in the threadpool, off the event loop.

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
        is not ready, the parameters cannot be read by the splitter, or its
        schema refuses them.
    """
    from DashAI.back.core.enums.status import DatasetStatus
    from DashAI.back.dataloaders.classes import dashai_dataset

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
        dataset_path = f"{dataset.file_path}/dataset"
        total_rows = dataset.total_rows

    indexes = params.indexes
    sizes = {"total_rows": total_rows}
    if params.split_type == "predefined" or total_rows is None:
        info = dashai_dataset.get_dataset_info(dataset_path)
        sizes = {
            "total_rows": info.get("total_rows", 0),
            "train_size": info.get("train_size", 0),
            "val_size": info.get("val_size", 0),
            "test_size": info.get("test_size", 0),
        }
        if params.split_type == "predefined":
            indexes = {
                "train": info.get("train_indices", []),
                "validation": info.get("val_indices", []),
                "test": info.get("test_indices", []),
            }

    try:
        preview = splitter.preview(params.params, sizes, params.split_type, indexes)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{splitter_name} cannot read these parameters: {e}",
        ) from e

    # The preview's own errors speak first: they say what to change on this
    # dataset, and a schema bound can hide them (more folds than rows is also
    # more than the 20 the schema allows). With none left, the schema has the
    # last word, as it does when the session is created.
    if preview is None or not preview["errors"]:
        parameters = dict(params.params)
        if params.split_type in INDEX_SPLIT_TYPES:
            for split in INDEX_KEY_BY_SPLIT:
                parameters.pop(split, None)
        try:
            validate_splitter_parameters(splitter, parameters)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid configuration for splitter {splitter_name}: {e}",
            ) from e
    return preview
