import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from pydantic import BaseModel

from DashAI.back.updates.checker import (
    UpdateAsset,
    UpdateInfo,
    check_for_updates,
    find_update_asset,
)
from DashAI.back.updates.download import downloaded_file

logger = logging.getLogger(__name__)

router = APIRouter()


class UpdateDownloadStatus(BaseModel):
    """Whether this install can download an update and if it already did."""

    available: bool
    name: Optional[str] = None
    size: Optional[int] = None
    downloaded: bool = False


def _update_asset(config: Dict[str, Any]) -> Optional[UpdateAsset]:
    """Return the update file for this install, unless update checks are off."""
    if not config["UPDATE_CHECK_ENABLED"]:
        return None
    return find_update_asset()


@router.get("/update-check", response_model=UpdateInfo)
def get_update_check(
    config: Dict[str, Any] = Depends(lambda: di["config"]),
) -> UpdateInfo:
    """Tell whether a newer dashAI version has been released.

    The answer from GitHub is cached, so calling this on every page load is
    fine. Setting ``UPDATE_CHECK_ENABLED=false`` turns the check off, for
    example on a shared server where users cannot update the install.

    Returns
    -------
    UpdateInfo
        The current and latest versions, the release notes and the download
        link for the detected install channel.
    """
    return check_for_updates(enabled=config["UPDATE_CHECK_ENABLED"])


@router.get("/update/download", response_model=UpdateDownloadStatus)
def get_update_download(
    config: Dict[str, Any] = Depends(lambda: di["config"]),
) -> UpdateDownloadStatus:
    """Tell whether the update file can be downloaded and if it already was.

    Returns
    -------
    UpdateDownloadStatus
        ``available`` is False when there is no newer release or this install
        channel is not updated from a file (pip, source, Docker).
    """
    asset = _update_asset(config)
    if asset is None:
        return UpdateDownloadStatus(available=False)
    path = downloaded_file(Path(config["UPDATES_PATH"]), asset)
    return UpdateDownloadStatus(
        available=True, name=asset.name, size=asset.size, downloaded=path is not None
    )


@router.post("/update/download", status_code=status.HTTP_201_CREATED)
def start_update_download(
    config: Dict[str, Any] = Depends(lambda: di["config"]),
    job_queue=Depends(lambda: di["job_queue"]),
) -> Dict[str, Any]:
    """Enqueue a job that downloads the update file for this install.

    Returns
    -------
    dict
        ``{"id": job_id}`` of the enqueued download job.

    Raises
    ------
    HTTPException
        409 if there is no update file for this install or it is already
        downloaded.
    """
    from DashAI.back.job.update_download_job import UpdateDownloadJob

    asset = _update_asset(config)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is no update file to download for this installation",
        )
    directory = Path(config["UPDATES_PATH"])
    if downloaded_file(directory, asset) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{asset.name} is already downloaded",
        )
    job = UpdateDownloadJob(asset=asset.model_dump(), directory=str(directory))
    job.set_status_as_delivered()
    job_id = job_queue.put(job).id
    return {"id": job_id}
