import logging

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.generative_session_params import (
    GenerativeSessionParams,
)
from DashAI.back.dependencies.database.models import GenerativeSession

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/get-all", status_code=status.HTTP_200_OK)
async def get_all_generative_tasks(
    #session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all generative sessions.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with all generative sessions on the database

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    return [
        {
            "task_name": "Text to Image",
            "description": "This task generates images from a given prompt",
        },
        {
            "task_name": "Text to Text",
            "description": "This task generates text from a given prompt",
        },
                {
            "task_name": "Audio to Text",
            "description": "This task takes an audio file and generates text",
        },
    ]

