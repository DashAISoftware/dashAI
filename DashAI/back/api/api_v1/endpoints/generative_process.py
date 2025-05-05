import logging
import os
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from kink import di
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.generative_process_params import (
    GenerativeProcessParams,
)
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.tasks import BaseGenerativeTask

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_generative_process(
    request: Request,
    session_id: Annotated[int, Form(...)],
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Create a new generative session.

    Parameters
    ----------
    params : GenerativeProcessParams
        The parameters of the new generative process, which includes the model name,
        task name, parameters, process name and description.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the new generative session on the database

    Raises
    ------
    HTTPException
        If there's an internal database error or if the session ID does not exist.
    """
    form = await request.form()
    input_items = []

    # Filter and sort only indexed keys like 'text_0', 'file_1'
    indexed_keys = [
        key for key in form.keys() if "_" in key and key.split("_")[1].isdigit()
    ]
    for key in sorted(indexed_keys, key=lambda x: int(x.split("_")[1])):
        value = form[key]
        if isinstance(value, UploadFile):
            content = await value.read()
            input_items.append(content)  # raw image bytes
        else:
            input_items.append(str(value))  # text string

    with session_factory() as db:
        try:
            session = db.query(GenerativeSession).filter_by(id=session_id).first()
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session with ID {session_id} does not exist.",
                )

            task: BaseGenerativeTask = di["component_registry"][session.task_name][
                "class"
            ]()
            processed_input = task.prepare_input_for_database(
                input_items, path=config["LOCAL_PATH"]
            )

            process = GenerativeProcess(
                input=processed_input,
                session_id=session_id,
            )
            db.add(process)
            db.commit()
            db.refresh(process)
            return process
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{process_id}", status_code=status.HTTP_200_OK, response_model=None)
async def get_generative_process(
    process_id: str,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Get a generative process by its session ID.

    Parameters
    ----------
    process_id : str
        The ID of the generative process to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative process data.

    Raises
    ------
    HTTPException
        If the generative process is not found or if there's an internal database error.
    """
    with session_factory() as db:
        try:
            process = db.query(GenerativeProcess).filter_by(id=process_id).all()
            generative_session: GenerativeSession = db.get(
                GenerativeSession, process[0].session_id
            )

            task: BaseGenerativeTask = component_registry[generative_session.task_name][
                "class"
            ]()

            process = [p.__dict__ for p in process]

            process = [
                {
                    **p,
                    "output": task.process_output_from_database(p["output"]),
                }
                for p in process
            ]

            return process[0]
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete(
    "/{process_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_generative_process(
    process_id: str,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete a generative process by its ID.

    Parameters
    ----------
    process_id : str
        The ID of the generative process to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    None

    Raises
    ------
    HTTPException
        If the generative process is not found or if there's an internal database error.
    """
    with session_factory() as db:
        try:
            process = db.query(GenerativeProcess).filter_by(id=process_id).first()
            if not process:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative process with ID {process_id} does not exist.",
                )
            db.delete(process)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get(
    "/session/{session_id}", status_code=status.HTTP_200_OK, response_model=None
)
async def get_generative_process(
    session_id: str,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Get a generative process by its session ID.

    Parameters
    ----------
    session_id : str
        The ID of the generative process to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative process data.

    Raises
    ------
    HTTPException
        If the generative process is not found or if there's an internal database error.
    """

    with session_factory() as db:
        try:
            process = db.query(GenerativeProcess).filter_by(session_id=session_id).all()
            generative_session: GenerativeSession = db.get(
                GenerativeSession, session_id
            )

            task: BaseGenerativeTask = component_registry[generative_session.task_name][
                "class"
            ]()

            process = [p.__dict__ for p in process]

            process = [
                {
                    **p,
                    "output": task.process_output_from_database(p["output"]),
                }
                for p in process
            ]

            return process
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/image/{image_path}", status_code=200, response_model=None)
async def get_generative_image(
    image_path: str,
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """
    Get a generated image by its path.

    Parameters
    ----------
    image_path : str
        The relative path or filename of the generated image to retrieve.

    Returns
    -------
    FileResponse
        The image file to be served to the client.
    """

    image_path = os.path.join(config["LOCAL_PATH"], "images", image_path)

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type="image/png")
