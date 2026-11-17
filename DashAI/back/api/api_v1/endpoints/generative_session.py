import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from kink import di
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.generative_session_params import (
    GenerativeSessionBulkDeleteParams,
    GenerativeSessionExportParams,
    GenerativeSessionParams,
)
from DashAI.back.core.utils import localize
from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    GenerativeSessionParameterHistory,
)
from DashAI.back.dependencies.downloads.nested import missing_downloads
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.services.workflows import (
    WorkflowConflictError,
    WorkflowSessionError,
    WorkflowSessionService,
    WorkflowStorageError,
    session_service_for,
)
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


def _session_payload(
    session: GenerativeSession,
    *,
    parameters: Dict[str, Any],
    prompts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Serialize one session from already resolved parts.

    The caller resolves the parameters and prompts, so the same serializer
    runs before a commit and degrades gracefully when a stored prompt is
    unusable.

    Parameters
    ----------
    session : GenerativeSession
        The session.
    parameters : Dict[str, Any]
        Parameters to send, prompts included.
    prompts : Optional[Dict[str, Any]]
        Prompt bindings; left out of the payload when ``None``.

    Returns
    -------
    Dict[str, Any]
        The session payload.
    """
    payload = {
        "id": session.id,
        "task_name": session.task_name,
        "model_name": session.model_name,
        "workflow_name": session.workflow_name,
        "parameters": parameters,
        "name": session.name,
        "description": session.description,
        "created": session.created,
        "last_modified": session.last_modified,
        "index_job_id": session.index_job_id,
        "needs_reindex": session.needs_reindex,
    }
    if prompts is not None:
        payload["prompts"] = prompts
    return payload


def _session_snapshot(
    session: GenerativeSession, service: WorkflowSessionService
) -> Dict[str, Any]:
    """Serialize a stored session as its workflow shows it to the client.

    Parameters
    ----------
    session : GenerativeSession
        The stored session.
    service : WorkflowSessionService
        The session's workflow service.

    Returns
    -------
    Dict[str, Any]
        The session payload.

    Raises
    ------
    WorkflowConflictError
        When the session's stored prompts cannot be resolved.
    """
    parameters, prompts = service.read_parameters(session)
    return _session_payload(session, parameters=parameters, prompts=prompts)


def _parameters_response(
    session_id: int,
    parameters: Dict[str, Any],
    prompts: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the answer to a parameter update.

    Parameters
    ----------
    session_id : int
        The session id.
    parameters : Dict[str, Any]
        Parameters to send, prompts included.
    prompts : Optional[Dict[str, Any]]
        Prompt bindings; left out when ``None``.

    Returns
    -------
    Dict[str, Any]
        The response body.
    """
    response = {"id": session_id, "parameters": parameters}
    if prompts is not None:
        response["prompts"] = prompts
    return response


def _split_parameters_body(
    body: Dict[str, Any],
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Split a parameter update body into parameters and a prompts map.

    The body is either the bare partial parameters, a wrapper with
    ``parameters`` and ``prompts``, or bare parameters next to ``prompts``.

    Parameters
    ----------
    body : Dict[str, Any]
        The request body.

    Returns
    -------
    Tuple[Dict[str, Any], Optional[Dict[str, Any]]]
        The partial parameters and the prompts map, if any.

    Raises
    ------
    HTTPException
        400 when ``parameters`` or ``prompts`` is not an object.
    """
    body = dict(body)
    prompts = None
    if "parameters" in body and not isinstance(body["parameters"], dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'parameters' must be an object of session parameters.",
        )
    if isinstance(body.get("parameters"), dict):
        prompts = body.get("prompts")
        body = dict(body["parameters"])
    elif "prompts" in body:
        prompts = body.pop("prompts")
    if prompts is not None and not isinstance(prompts, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'prompts' must be an object keyed by prompt slot path.",
        )
    return body, prompts


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
    ``workflow_name`` the session runs ``InferenceWorkflow``. The session row,
    what the workflow keeps outside it (prompt bindings, say) and the first
    history entry are committed together.
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
                    params.parameters, accept_language, params.prompts
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

            stored_parameters = service.stored_parameters(parameters)
            now = datetime.now()
            session = GenerativeSession(
                model_name=model_name,
                task_name=task_name,
                workflow_name=workflow_name,
                parameters=stored_parameters,
                name=params.name,
                description=params.description,
                created=now,
                last_modified=now,
            )
            db.add(session)
            try:
                db.flush()
            except exc.IntegrityError as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Generative session with name '{params.name}' already exists."
                    ),
                ) from e

            prompt_snapshot = service.bind_new_session(
                session, parameters, params.prompts
            )
            client_parameters = service.client_parameters(session, stored_parameters)

            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=stored_parameters,
                prompt_bindings=prompt_snapshot,
                model_name=session.model_name,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)
            db.commit()
            db.refresh(session)

            response = _session_payload(
                session, parameters=client_parameters, prompts=prompt_snapshot
            )
            # Localized here so the client never receives a language object.
            response["display_name"] = _display_name(
                session.workflow_name,
                session.task_name,
                component_registry,
                accept_language,
            )
            return response
        except HTTPException:
            db.rollback()
            raise
        except WorkflowConflictError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except WorkflowStorageError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except (ValueError, LookupError) as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{session_id}", status_code=status.HTTP_200_OK)
async def get_generative_session(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Get a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        Registry used to resolve the session's prompts.

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
            return _session_snapshot(
                session,
                session_service_for(session.workflow_name, db, component_registry),
            )
        except WorkflowConflictError as e:
            # The stored prompts are unusable (an unreadable default, a row
            # deleted under the session): a state conflict, not a server fault.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
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
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
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
    component_registry : ComponentRegistry
        Registry used to resolve each session's prompts.

    Returns
    -------
    list
        A list of dictionaries with the matching generative sessions, ordered by
        creation date. A session whose stored prompts cannot be resolved is
        returned with its stored ``parameters`` and a ``prompt_error`` field
        instead of failing the whole list.

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

        payloads = []
        for session in sessions:
            service = session_service_for(session.workflow_name, db, component_registry)
            try:
                payloads.append(_session_snapshot(session, service))
            except (WorkflowConflictError, LookupError) as e:
                # One session whose stored prompt became unreadable must not
                # hide every other session; it is listed with the reason.
                log.warning(
                    "Could not resolve the prompts of session %s: %s",
                    session.id,
                    e,
                )
                payload = _session_payload(
                    session,
                    parameters=dict(session.parameters or {}),
                    prompts={},
                )
                payload["prompt_error"] = str(e)
                payloads.append(payload)
        return payloads


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generative_sessions(
    params: GenerativeSessionBulkDeleteParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Delete multiple generative sessions, in a single transaction.

    Each session's workflow deletes the session with every row it owns inside
    that transaction.

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
            for session_id in params.ids:
                session = db.get(GenerativeSession, session_id)
                if not session:
                    continue
                session_service_for(
                    session.workflow_name, db, component_registry, job_queue
                ).delete(session)
            db.commit()
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


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generative_session(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Delete a generative session by its ID.

    The session's workflow deletes the session with every row it owns, in one
    transaction.

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

            session_service_for(
                session.workflow_name, db, component_registry, job_queue
            ).delete(session)
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

            service = session_service_for(session.workflow_name, db, component_registry)
            if model_name is not None and model_name != session.model_name:
                _session_workflow(session, component_registry)
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
                # Every history entry owns the prompts active when it was
                # written, so a later prompt edit cannot rewrite its diff.
                db.add(
                    GenerativeSessionParameterHistory(
                        session_id=session.id,
                        parameters=new_parameters,
                        prompt_bindings=service.snapshot_prompts(session),
                        model_name=model_name,
                        modified_at=datetime.now(),
                    )
                )

            if name is not None or description is not None or model_name is not None:
                session.last_modified = datetime.now()
                db.commit()
                db.refresh(session)
                return _session_snapshot(session, service)
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except HTTPException:
            raise
        except WorkflowConflictError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
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
    new_params: Dict[str, Any],
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: Any = Depends(lambda: di["job_queue"]),
):
    """Merge a partial parameter update into a session and log it.

    The session's workflow validates the update, runs its side effects and,
    when its model is one of the parameters, the session model follows it. An
    update that changes nothing records no history entry.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to update.
    new_params : Dict[str, Any]
        Partial parameters to merge over the stored ones, or a wrapper with
        ``parameters`` and a ``prompts`` slot path map.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
    component_registry : ComponentRegistry
        Registry resolving the session's task, workflow and models.
    job_queue : Any
        Job queue, for workflows that run background jobs.

    Returns
    -------
    dict
        The session id, its merged parameters and, for a workflow with
        prompts, its prompt bindings.

    Raises
    ------
    HTTPException
        404 if the session, its task or its workflow is unknown, 400 if the
        update is invalid, 409 if a selected component is not downloaded or a
        prompt conflicts with a stored one.
    """
    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

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

            body, body_prompts = _split_parameters_body(new_params)
            try:
                normalized = service.validate_update(session, body, body_prompts)
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

            old_parameters = service.stored_parameters(dict(session.parameters or {}))
            updated_parameters = {
                **old_parameters,
                **service.stored_parameters(normalized),
            }

            # A save that changes neither the configuration nor anything the
            # workflow keeps outside it adds no history row.
            if service.is_unchanged(
                session, old_parameters, updated_parameters, normalized, body_prompts
            ):
                return _parameters_response(
                    session.id,
                    service.client_parameters(session, old_parameters),
                    service.snapshot_prompts(session),
                )

            model_name = session.model_name
            derived_model = service.model_name_from(updated_parameters)
            if derived_model is not None and derived_model != model_name:
                _check_model_fits_task(
                    derived_model, session.task_name, component_registry
                )
                model_name = derived_model

            prompt_snapshot = service.apply_update(
                session, old_parameters, updated_parameters, normalized, body_prompts
            )
            client_parameters = service.client_parameters(session, updated_parameters)
            session.model_name = model_name

            # ── Persist ──
            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=updated_parameters,
                prompt_bindings=prompt_snapshot,
                model_name=session.model_name,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)

            session.parameters = updated_parameters
            session.last_modified = datetime.now()
            db.commit()
            db.refresh(session)

            return _parameters_response(session.id, client_parameters, prompt_snapshot)
        except HTTPException:
            db.rollback()
            raise
        except WorkflowConflictError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except WorkflowStorageError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except (ValueError, LookupError) as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
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
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """
    Get all parameter history entries for a generative session.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve the parameter history for.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
    component_registry : ComponentRegistry
        Registry used to resolve the prompts each entry recorded.

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

            service = session_service_for(session.workflow_name, db, component_registry)
            history_list = []
            for entry in parameters_history:
                history_list.append(
                    {
                        "id": entry.id,
                        "session_id": entry.session_id,
                        "parameters": service.history_parameters(session, entry),
                        "prompt_bindings": getattr(entry, "prompt_bindings", None),
                        "modified_at": entry.modified_at,
                    }
                )
            return history_list
        except WorkflowConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
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
    component_registry : ComponentRegistry
        Registry used to resolve the session's workflow and recorded prompts.

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

            service = session_service_for(session.workflow_name, db, component_registry)
            entries = [
                {
                    "id": entry.id,
                    "parameters": service.history_parameters(session, entry),
                    "model_name": getattr(entry, "model_name", None),
                    "modified_at": entry.modified_at,
                }
                for entry in parameters_history
            ]
            if not entries:
                return []

            model_is_a_parameter = (
                service.model_name_from(session.parameters) is not None
            )

            events = []
            prev_params = entries[0]["parameters"]
            prev_model = entries[0].get("model_name")

            for i in range(1, len(entries)):
                curr = entries[i]
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

        except WorkflowConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_generative_session(
    file: UploadFile = File(...),
    accept_language: str | None = Header(default=None),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    config=Depends(lambda: di["config"]),
):
    """Create a new generative session from an uploaded ``.dashai`` file.

    Raises
    ------
    HTTPException
        400 if the file is not a usable generative session, 409 if it needs a
        newer DashAI or a missing plugin, 500 on any other failure.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from fastapi.concurrency import run_in_threadpool

    from DashAI.back.api.api_v1.endpoints.model_sessions import _import_error_detail
    from DashAI.back.generative_package.load import import_generative_package
    from DashAI.back.model_package.manifest import (
        MissingPluginError,
        ModelPackageError,
        UnsupportedPackageFormatError,
    )

    workdir = Path(tempfile.mkdtemp(prefix="dashai-upload-"))
    try:
        upload = workdir / "session.dashai"
        with open(upload, "wb") as handle:
            shutil.copyfileobj(file.file, handle)
        return await run_in_threadpool(
            import_generative_package,
            upload,
            session_factory,
            component_registry,
            (accept_language or "en").split("-")[0].lower(),
            config["IMAGES_PATH"],
            config["DOCUMENTS_PATH"],
        )
    except (UnsupportedPackageFormatError, MissingPluginError) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=await run_in_threadpool(_import_error_detail, e, session_factory),
        ) from e
    except ModelPackageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=await run_in_threadpool(_import_error_detail, e, session_factory),
        ) from e
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error importing the session",
        ) from e
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@router.get("/{session_id}/export/preview")
async def get_generative_session_export_preview(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    config=Depends(lambda: di["config"]),
):
    """What exporting the session would carry: its conversation and size.

    Raises
    ------
    HTTPException
        404 if the session does not exist.
    """
    from fastapi.concurrency import run_in_threadpool

    from DashAI.back.generative_package.export import (
        GenerativeSessionNotFoundError,
        export_preview,
    )

    try:
        return await run_in_threadpool(
            export_preview, session_id, session_factory, config["IMAGES_PATH"]
        )
    except GenerativeSessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from e


@router.post("/{session_id}/export")
async def export_generative_session(
    session_id: int,
    params: GenerativeSessionExportParams | None = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    config=Depends(lambda: di["config"]),
):
    """Download a generative session as a ``.dashai`` file.

    Without a body, or with ``include_conversation`` false, the file holds
    only the configuration.

    Raises
    ------
    HTTPException
        404 if the session does not exist, 500 on any other failure.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from fastapi.concurrency import run_in_threadpool
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask

    from DashAI.back.generative_package.export import (
        GenerativeSessionNotFoundError,
        build_generative_package,
        generative_session_filename,
    )

    workdir = Path(tempfile.mkdtemp(prefix="dashai-export-"))
    destination = workdir / "session.dashai"
    try:
        manifest = await run_in_threadpool(
            build_generative_package,
            session_id,
            destination,
            session_factory,
            component_registry,
            bool(params and params.include_conversation),
            config["IMAGES_PATH"],
        )
    except GenerativeSessionNotFoundError as e:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from e
    except Exception as e:
        shutil.rmtree(workdir, ignore_errors=True)
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting the session",
        ) from e

    return FileResponse(
        destination,
        media_type="application/zip",
        filename=generative_session_filename(manifest["info"]["session_name"]),
        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
    )
