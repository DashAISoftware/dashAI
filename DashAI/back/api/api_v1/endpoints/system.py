import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends
from kink import di

from DashAI.back.updates.checker import UpdateInfo, check_for_updates

logger = logging.getLogger(__name__)

router = APIRouter()


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
