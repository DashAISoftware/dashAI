import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Type, Union

from fastapi import APIRouter, Depends, Header, HTTPException, status
from kink import di
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.generative_session_params import (
    GenerativeSessionBulkDeleteParams,
    GenerativeSessionParams,
)
from DashAI.back.core.utils import localize
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    GenerativeSessionParameterHistory,
    ProcessData,
)
from DashAI.back.dependencies.downloads.nested import missing_downloads
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.services.workflows import WorkflowSessionError, session_service_for
from DashAI.back.tasks.base_generative_task import BaseGenerativeTask
from DashAI.back.workflows import INFERENCE_WORKFLOW_NAME, BaseGenerativeWorkflow

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry import ComponentRegistry


router = APIRouter()
log = logging.getLogger(__name__)


def _workflow_class(
    workflow_name: str, component_registry: "ComponentRegistry"
) -> Type[BaseGenerativeWorkflow]:
    """Resolve a registered generative workflow for a new session.

    Parameters
    ----------
    workflow_name : str
        Name sent by the client.
    component_registry : ComponentRegistry
        Registry holding the workflows.

    Returns
    -------
    Type[BaseGenerativeWorkflow]
        The workflow class.

    Raises
    ------
    HTTPException
        400 when no generative workflow has that name.
    """
    if (
        workflow_name not in component_registry
        or component_registry[workflow_name]["type"] != BaseGenerativeWorkflow.TYPE
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow {workflow_name} is not registered.",
        )
    return component_registry[workflow_name]["class"]


def _session_workflow(
    session: GenerativeSession, component_registry: "ComponentRegistry"
) -> Type[BaseGenerativeWorkflow]:
    """Resolve the workflow of a stored session.

    Parameters
    ----------
    session : GenerativeSession
        The stored session.
    component_registry : ComponentRegistry
        Registry holding the workflows.

    Returns
    -------
    Type[BaseGenerativeWorkflow]
        The workflow class.

    Raises
    ------
    HTTPException
        404 when the session's workflow is not registered.
    """
    if session.workflow_name not in component_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Workflow '{session.workflow_name}' is not registered"
                " in the component registry."
            ),
        )
    return component_registry[session.workflow_name]["class"]


def _check_model_fits_task(
    model_name: str, task_name: str, component_registry: "ComponentRegistry"
) -> None:
    """Refuse a model that is not a model of the task.

    Parameters
    ----------
    model_name : str
        Model component name.
    task_name : str
        Task component name.
    component_registry : ComponentRegistry
        Registry holding the task to model relation.

    Raises
    ------
    HTTPException
        400 when the model is not related to the task.
    """
    related = {
        component["name"]
        for component in component_registry.get_related_components(task_name)
    }
    if model_name not in related:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model {model_name} is not a model of task {task_name}.",
        )


def _display_name(
    workflow_name: str,
    task_name: str,
    component_registry: "ComponentRegistry",
    accept_language: Union[str, None],
) -> str:
    """Return the name a session is shown under.

    Inference sessions are shown under their task; every other workflow names
    its own sessions.

    Parameters
    ----------
    workflow_name : str
        The session's workflow.
    task_name : str
        The session's task.
    component_registry : ComponentRegistry
        Registry holding both.
    accept_language : Union[str, None]
        Client language.

    Returns
    -------
    str
        The localized display name.
    """
    owner = task_name if workflow_name == INFERENCE_WORKFLOW_NAME else workflow_name
    return localize(component_registry[owner]["display_name"], accept_language)


def _workflow_tasks(
    workflow_name: str, component_registry: "ComponentRegistry"
) -> list:
    """Return the generative tasks a workflow runs.

    Parameters
    ----------
    workflow_name : str
        The workflow.
    component_registry : ComponentRegistry
        Registry holding the workflow's compatible components.

    Returns
    -------
    list
        Names of the related components of type ``GenerativeTask``.
    """
    return [
        component["name"]
        for component in component_registry.get_related_components(workflow_name)
        if component["type"] == BaseGenerativeTask.TYPE
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_generative_session(
    params: GenerativeSessionParams,
    accept_language: str | None = Header(default=None),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Create a generative session and log its initial parameters.

    The task must be one the workflow runs (it may be left out when the
    workflow runs only one). The workflow's session service completes the
    parameters, may name the model from them, and validates them. Without
    ``workflow_name`` the session runs ``InferenceWorkflow``.
    """

    with session_factory() as db:
        try:
            workflow_class = _workflow_class(
                params.workflow_name or INFERENCE_WORKFLOW_NAME, component_registry
            )
            workflow_name = workflow_class.__name__

            workflow_tasks = _workflow_tasks(workflow_name, component_registry)
            task_name = params.task_name
            if task_name is None and len(workflow_tasks) == 1:
                task_name = workflow_tasks[0]
            if task_name is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Workflow {workflow_name} needs a task_name.",
                )

            service = session_service_for(
                workflow_name, db, component_registry, job_queue
            )
            try:
                parameters = service.prepare_parameters(
                    params.parameters, accept_language
                )
            except WorkflowSessionError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                ) from e

            model_name = service.model_name_from(parameters) or params.model_name
            if model_name is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Workflow {workflow_name} needs a model_name.",
                )
            if params.model_name is not None and params.model_name != model_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Model {params.model_name} is not the model the "
                        f"session parameters name, {model_name}."
                    ),
                )

            # Check if the model is registered
            if model_name not in component_registry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {model_name} is not registered.",
                )
            model_class = component_registry[model_name]["class"]

            # Guard: model requires download but has not been downloaded -> 409.
            # Reconcile against the filesystem so a model downloaded after startup
            # (in the worker process) is recognised without an API restart.
            if getattr(
                model_class, "REQUIRES_DOWNLOAD", False
            ) and not component_registry.refresh_download_status(model_name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(f"Model {model_name} must be downloaded before use."),
                )

            # Check if the model is a subclass of GenerativeModel
            if not issubclass(model_class, BaseGenerativeModel):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {model_name} is not a valid generative model.",
                )

            # Check if the task is registered
            if task_name not in component_registry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task {task_name} is not registered.",
                )
            task_class = component_registry[task_name]["class"]

            if task_name not in workflow_tasks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Workflow {workflow_name} does not run task {task_name}; "
                        f"it runs {', '.join(workflow_tasks)}."
                    ),
                )

            _check_model_fits_task(model_name, task_name, component_registry)

            # A parameter may select another component that itself needs
            # downloading; block until every nested one is present. Runs after
            # the workflow completed the parameters so it sees the final
            # configuration.
            nested_missing = missing_downloads(parameters, component_registry)
            if nested_missing:
                names = ", ".join(m["name"] for m in nested_missing)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"These components must be downloaded before use: {names}."
                    ),
                )

            # Validate schema
            try:
                service.check_parameters(model_class, parameters)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid parameters for model {model_name}: {e}",
                ) from e

            # Check if the task is a subclass of BaseGenerativeTask
            if not issubclass(task_class, BaseGenerativeTask):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task {task_name} is not a valid generative task.",
                )

            now = datetime.now()
            session = GenerativeSession(
                model_name=model_name,
                task_name=task_name,
                workflow_name=workflow_name,
                parameters=parameters,
                name=params.name,
                description=params.description,
                created=now,
                last_modified=now,
            )
            db.add(session)
            try:
                db.commit()
            except exc.IntegrityError as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Generative session with name '{params.name}' already exists."
                    ),
                ) from e
            db.refresh(session)

            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=session.parameters,
                model_name=session.model_name,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)
            db.commit()

            return {
                "id": session.id,
                "model_name": session.model_name,
                "task_name": session.task_name,
                "workflow_name": session.workflow_name,
                "parameters": session.parameters,
                "name": session.name,
                "description": session.description,
                "created": session.created,
                "last_modified": session.last_modified,
                # Localized here so the client never receives a language object.
                "display_name": _display_name(
                    session.workflow_name,
                    session.task_name,
                    component_registry,
                    accept_language,
                ),
            }
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{session_id}", status_code=status.HTTP_200_OK)
async def get_generative_session(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative session on the database

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(f"Generative session {session_id} does not exist in DB."),
                )
            return session
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_generative_sessions(
    task_name: Union[str, None] = None,
    workflow_name: Union[str, None] = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get all generative sessions ordered by creation date.

    Parameters
    ----------
    task_name : str | None
        If given, return only sessions of that generative task.
    workflow_name : str | None
        If given, return only sessions run by that workflow. A view scoped to
        one workflow (the RAG entry point, say) uses this; the shared session
        list asks for everything and groups the result.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with the matching generative sessions, ordered by
        creation date.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            query = db.query(GenerativeSession)
            if task_name is not None:
                query = query.filter(GenerativeSession.task_name == task_name)
            if workflow_name is not None:
                query = query.filter(GenerativeSession.workflow_name == workflow_name)
            sessions = query.order_by(GenerativeSession.created.asc()).all()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        session_list = []
        for session in sessions:
            session_list.append(
                {
                    "id": session.id,
                    "task_name": session.task_name,
                    "model_name": session.model_name,
                    "workflow_name": session.workflow_name,
                    "parameters": session.parameters,
                    "name": session.name,
                    "description": session.description,
                    "created": session.created,
                    "last_modified": session.last_modified,
                }
            )
        return session_list


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generative_sessions(
    params: GenerativeSessionBulkDeleteParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Delete multiple generative sessions, in a single transaction.

    Each session's workflow releases what the session owns inside that
    transaction; once it is committed, each workflow sweeps what its session
    left unused. A failed sweep is logged and does not undo the deletion.

    Parameters
    ----------
    params : GenerativeSessionBulkDeleteParams
        The IDs of the generative sessions to delete. IDs that do not match
        an existing session are silently skipped rather than failing the
        whole request.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        Registry resolving each session's workflow.
    job_queue : Any
        Job queue, for workflows that run background jobs.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            sweeps = []
            for session_id in params.ids:
                session = db.get(GenerativeSession, session_id)
                if not session:
                    continue

                service = session_service_for(
                    session.workflow_name, db, component_registry, job_queue
                )
                service.before_delete(session)
                sweeps.append((service, session_id, dict(session.parameters or {})))

                # Delete all the processes associated with the session
                processes = (
                    db.query(GenerativeProcess)
                    .filter(GenerativeProcess.session_id == session_id)
                    .all()
                )
                # Delete all the process data associated with the processes
                for process in processes:
                    process_data = (
                        db.query(ProcessData)
                        .filter(ProcessData.process_id == process.id)
                        .all()
                    )
                    for data in process_data:
                        db.delete(data)
                # Delete the processes
                for process in processes:
                    db.delete(process)

                # Delete the session parameter history entries
                parameters_history = (
                    db.query(GenerativeSessionParameterHistory)
                    .filter(GenerativeSessionParameterHistory.session_id == session_id)
                    .all()
                )
                for entry in parameters_history:
                    db.delete(entry)

                # Finally, delete the session itself
                db.delete(session)

            db.commit()

            for service, session_id, old_parameters in sweeps:
                try:
                    service.after_delete(session_id, old_parameters)
                except Exception:
                    log.exception(
                        "Could not sweep the resources of deleted session %s",
                        session_id,
                    )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e
        finally:
            db.rollback()
            db.close()


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generative_session(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Delete a generative session by its ID.

    The session's workflow releases what the session owns before the rows go
    and sweeps what it left unused afterwards, in the same transaction.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        Registry resolving the session's workflow.
    job_queue : Any
        Job queue, for workflows that run background jobs.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            old_parameters = dict(session.parameters or {})

            service = session_service_for(
                session.workflow_name, db, component_registry, job_queue
            )
            service.before_delete(session)

            # Delete all the processes associated with the session
            processes = (
                db.query(GenerativeProcess)
                .filter(GenerativeProcess.session_id == session_id)
                .all()
            )
            # Delete all the process data associated with the processes
            for process in processes:
                process_data = (
                    db.query(ProcessData)
                    .filter(ProcessData.process_id == process.id)
                    .all()
                )
                for data in process_data:
                    db.delete(data)
            # Delete the processes
            for process in processes:
                db.delete(process)

            # Delete the session parameter history entries
            parameters_history = (
                db.query(GenerativeSessionParameterHistory)
                .filter(GenerativeSessionParameterHistory.session_id == session_id)
                .all()
            )
            for entry in parameters_history:
                db.delete(entry)
            # Finally, delete the session itself
            db.delete(session)

            service.after_delete(session_id, old_parameters)
            db.commit()
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e
        finally:
            db.close()


@router.patch("/{session_id}", status_code=status.HTTP_200_OK)
async def update_generative_session(
    session_id: int,
    name: Union[str, None] = None,
    description: Union[str, None] = None,
    model_name: Union[str, None] = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Update the generative session associated with the provided ID.

    Parameters
    ----------
    session_id : int
        ID of the generative session to update.
    name : Union[str, None], optional
        New name for the session.
    description : Union[str, None], optional
        New description for the session.
    model_name : Union[str, None], optional
        New model (component name) for the session. Must be a registered
        generative model; if it requires a download it must already be
        downloaded.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        The DashAI component registry, used to validate the new model.

    Returns
    -------
    Dict
        A dictionary containing the updated generative session record.

    Raises
    ------
    HTTPException
        If the session does not exist, the name is invalid or taken, or the new
        model is unknown, not a generative model, or not yet downloaded.
    """
    from DashAI.back.models.base_generative_model import BaseGenerativeModel

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generative session not found",
                )

            if model_name is not None and model_name != session.model_name:
                _session_workflow(session, component_registry)
                service = session_service_for(
                    session.workflow_name, db, component_registry
                )
                if service.model_name_from(session.parameters) is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"The model of a {session.workflow_name} session is "
                            "named in its parameters; change them instead."
                        ),
                    )

            # Validate name if provided
            if name is not None:
                if not name or not name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Name cannot be empty",
                    )

                new_name = name.strip()

                # Check if name is different from current name
                if new_name != session.name:
                    # Check if name already exists
                    exists = db.execute(
                        select(GenerativeSession.id).where(
                            GenerativeSession.name == new_name,
                            GenerativeSession.id != session_id,
                        )
                    ).scalar()
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Generative session name already exists",
                        )
                    setattr(session, "name", new_name)

            if description is not None:
                setattr(session, "description", description)

            # Validate and apply a model change if provided. A model may be
            # selected even when it is not downloaded yet; the chat blocks input
            # and offers a download until the weights become available.
            if model_name is not None and model_name != session.model_name:
                try:
                    model_class = component_registry[model_name]["class"]
                except KeyError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Model {model_name} is not registered.",
                    ) from e
                if not issubclass(model_class, BaseGenerativeModel):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Model {model_name} is not a valid generative model.",
                    )

                # Resolve the parameters for the new model: reuse the most
                # recent parameters used for it in this session, else fall back
                # to the model's schema defaults (its field placeholders).
                last_used = (
                    db.query(GenerativeSessionParameterHistory)
                    .filter(
                        GenerativeSessionParameterHistory.session_id == session_id,
                        GenerativeSessionParameterHistory.model_name == model_name,
                    )
                    .order_by(GenerativeSessionParameterHistory.modified_at.desc())
                    .first()
                )
                if last_used is not None:
                    new_parameters = last_used.parameters
                else:
                    properties = model_class.get_schema().get("properties", {})
                    new_parameters = {
                        key: prop.get("placeholder") for key, prop in properties.items()
                    }

                session.model_name = model_name
                session.parameters = new_parameters
                db.add(
                    GenerativeSessionParameterHistory(
                        session_id=session.id,
                        parameters=new_parameters,
                        model_name=model_name,
                        modified_at=datetime.now(),
                    )
                )

            if name is not None or description is not None or model_name is not None:
                session.last_modified = datetime.now()
                db.commit()
                db.refresh(session)
                return session
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except HTTPException:
            raise
        except exc.IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Generative session name already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.put("/{session_id}/parameters", status_code=status.HTTP_200_OK)
async def update_generative_session_params(
    session_id: int,
    new_params: dict,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Merge a partial parameter update into a session and log it.

    The session's workflow validates the update, runs its side effects and,
    when its model is one of the parameters, the session model follows it.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to update.
    new_params : dict
        Partial parameters to merge over the stored ones.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
    component_registry : ComponentRegistry
        Registry resolving the session's task, workflow and models.
    job_queue : Any
        Job queue, for workflows that run background jobs.

    Returns
    -------
    dict
        The session id and its merged parameters.

    Raises
    ------
    HTTPException
        404 if the session, its task or its workflow is unknown, 400 if the
        update is invalid, 409 if a selected component is not downloaded.
    """
    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            old_parameters = dict(session.parameters or {})
            if session.task_name not in component_registry:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Task '{session.task_name}' is not registered"
                        " in the component registry."
                    ),
                )
            _session_workflow(session, component_registry)
            service = session_service_for(
                session.workflow_name, db, component_registry, job_queue
            )

            try:
                normalized = service.validate_update(session, new_params)
            except WorkflowSessionError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                ) from e

            nested_missing = missing_downloads(normalized, component_registry)
            if nested_missing:
                names = ", ".join(m["name"] for m in nested_missing)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"These components must be downloaded before use: {names}."
                    ),
                )

            updated_parameters = {**old_parameters, **normalized}

            model_name = session.model_name
            derived_model = service.model_name_from(updated_parameters)
            if derived_model is not None and derived_model != model_name:
                _check_model_fits_task(
                    derived_model, session.task_name, component_registry
                )
                model_name = derived_model

            service.apply_update(session, old_parameters, updated_parameters)
            session.model_name = model_name

            # ── Persist ──
            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=updated_parameters,
                model_name=session.model_name,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)

            session.parameters = updated_parameters
            session.last_modified = datetime.now()
            db.commit()
            db.refresh(session)

            return {"id": session.id, "parameters": session.parameters}
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{session_id}/parameters-history", status_code=status.HTTP_200_OK)
async def get_generative_session_parameters_history(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """
    Get all parameter history entries for a generative session.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve the parameter history for.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.

    Returns
    -------
    list
        A list of dictionaries with all parameter history entries for the session.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """
    with session_factory() as db:
        try:
            # Check if the generative session exists
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            # Get the session parameter history
            parameters_history = (
                db.query(GenerativeSessionParameterHistory)
                .filter(GenerativeSessionParameterHistory.session_id == session_id)
                .order_by(GenerativeSessionParameterHistory.modified_at.asc())
                .all()
            )

            # Convert the objects to dictionaries (explicit loop for clarity)
            history_list = []
            for entry in parameters_history:
                history_list.append(
                    {
                        "id": entry.id,
                        "session_id": entry.session_id,
                        "parameters": entry.parameters,
                        "modified_at": entry.modified_at,
                    }
                )
            return history_list
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/parameters-history/{session_id}", status_code=status.HTTP_200_OK)
async def get_parameter_history_entry(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """
    Get history entry for a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with the parameter history entries for the session.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            # Check if the generative session exists
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            # Get the parameter history entry for the session
            parameters_history = (
                db.query(GenerativeSessionParameterHistory)
                .filter(GenerativeSessionParameterHistory.session_id == session_id)
                .order_by(GenerativeSessionParameterHistory.modified_at.asc())
                .all()
            )

            parameters_history = [p.__dict__ for p in parameters_history]
            if not parameters_history:
                return []

            model_is_a_parameter = (
                session_service_for(
                    session.workflow_name, db, component_registry
                ).model_name_from(session.parameters)
                is not None
            )

            events = []
            prev_params = parameters_history[0]["parameters"]
            prev_model = parameters_history[0].get("model_name")

            for i in range(1, len(parameters_history)):
                curr = parameters_history[i]
                curr_params = curr["parameters"]
                curr_model = curr.get("model_name")
                changes = []

                # A model switch resets parameters to the new model's own
                # values, so the raw parameter diff would be noise; report only
                # the model change for that entry.
                if (
                    not model_is_a_parameter
                    and curr_model
                    and prev_model
                    and curr_model != prev_model
                ):
                    changes.append(
                        {
                            "parameter": "model",
                            "oldValue": prev_model,
                            "newValue": curr_model,
                        }
                    )
                else:
                    for key in curr_params:
                        old_val = prev_params.get(key)
                        new_val = curr_params[key]
                        if old_val != new_val:
                            changes.append(
                                {
                                    "parameter": key,
                                    "oldValue": old_val,
                                    "newValue": new_val,
                                }
                            )

                events.append(
                    {
                        "id": curr["id"],
                        "timestamp": curr["modified_at"],
                        "changes": changes,
                    }
                )
                prev_params = curr_params
                prev_model = curr_model

            return events

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
