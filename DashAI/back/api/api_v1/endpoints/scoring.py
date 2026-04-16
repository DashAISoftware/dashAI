"""Scoring and model comparison endpoints."""

from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Query

if TYPE_CHECKING:
    pass

router = APIRouter()


@router.get("/profiles")
def get_scoring_profiles(
    task_name: Optional[str] = Query(None),
):
    """Retrieve available scoring profiles, optionally filtered by task.

    Profiles are fetched from task SCORING_PROFILES defined in the registry.

    Parameters
    ----------
    task_name : Optional[str], optional
        Task class name (e.g., "TabularClassificationTask"). If specified,
        only profiles for that task are returned, by default None.

    Returns
    -------
    List[Dict[str, Any]]
        List of profile dicts with keys:
        - id: str (e.g., "balanced")
        - description: str
        - weights: Dict[str, float] (metric name → weight)
    """
    from DashAI.back.services.scoring_service import ScoringService

    service = ScoringService()
    profiles = service.get_available_profiles(task_name)
    return profiles
