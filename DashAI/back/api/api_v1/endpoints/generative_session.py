import copy
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Union

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
from DashAI.back.models.RAG.exceptions import (
    RAGDatabaseError,
    RAGWorkflowError,
)
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.exceptions import RAGPromptValidationError
from DashAI.back.services.RAG.index_job_service import cancel_live_index_job
from DashAI.back.services.RAG.prompt_service import (
    PromptConflictError,
    PromptService,
)
from DashAI.back.services.RAG.session_document_service import (
    SessionDocumentService,
)
from DashAI.back.services.RAG.session_validation_service import (
    SessionValidationService,
)
from DashAI.back.tasks.base_generative_task import BaseGenerativeTask
from DashAI.back.tasks.RAG_task import RAGTask

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry import ComponentRegistry


router = APIRouter()
log = logging.getLogger(__name__)


def _is_rag_session(session: GenerativeSession) -> bool:
    """Whether a session runs the RAG task and therefore has prompt slots."""
    return session.task_name == RAGTask.__name__


def _session_payload(
    session: GenerativeSession,
    *,
    parameters: dict[str, Any],
    prompts: Union[dict[str, Any], None] = None,
) -> dict[str, Any]:
    """Serialize one session from already-resolved parts.

    The caller resolves the prompts, so the same serializer can run before a
    commit (into a still-uncommitted session) and degrade gracefully when one
    stored prompt is unusable.
    """
    payload = {
        "id": session.id,
        "task_name": session.task_name,
        "model_name": session.model_name,
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
    session: GenerativeSession,
    prompt_service: PromptService,
) -> dict[str, Any]:
    """Serialize a session, injecting its prompts for the current frontend.

    Non-RAG sessions are returned with their stored parameters untouched. RAG
    sessions get a materialized copy (prompts resolved from storage, or from
    legacy parameters) plus the resolved binding map.
    """
    parameters = dict(session.parameters or {})
    if _is_rag_session(session):
        return _session_payload(
            session,
            parameters=prompt_service.materialize_session_parameters(
                session.id, parameters
            ),
            prompts=prompt_service.list_bindings(session.id),
        )
    return _session_payload(session, parameters=parameters)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_generative_session(
    params: GenerativeSessionParams,
    accept_language: str | None = Header(default=None),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Create a new generative session and log the initial parameters in the history."""

    with session_factory() as db:
        try:
            # Check if the model is registered
            if params.model_name not in component_registry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {params.model_name} is not registered.",
                )
            model_class = component_registry[params.model_name]["class"]

            # Guard: model requires download but has not been downloaded -> 409.
            # Reconcile against the filesystem so a model downloaded after startup
            # (in the worker process) is recognised without an API restart.
            if getattr(
                model_class, "REQUIRES_DOWNLOAD", False
            ) and not component_registry.refresh_download_status(params.model_name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Model {params.model_name} must be downloaded before use."
                    ),
                )

            # Check if the model is a subclass of GenerativeModel
            if not issubclass(model_class, BaseGenerativeModel):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {params.model_name} is not a valid "
                    f"generative model.",
                )

            # Check if the task is registered
            if params.task_name not in component_registry:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task {params.task_name} is not registered.",
                )
            task_class = component_registry[params.task_name]["class"]

            # Prompt resolution validates every slot and reads stored rows, so
            # the service is created before the RAG parameter validation runs.
            prompt_service = PromptService(db, component_registry)

            # RAG: validate and normalise RAG-specific parameters, filling in
            # the components the caller did not choose. A prompt supplied only
            # through the ``prompts`` map is placed at its slot first, so a
            # required nested slot can be configured from scratch.
            if task_class == RAGTask:
                candidate_parameters = params.parameters
                if isinstance(params.prompts, dict):
                    candidate_parameters = prompt_service.apply_prompt_map(
                        params.parameters, params.prompts
                    )
                try:
                    params.parameters = SessionValidationService(
                        db, component_registry
                    ).prepare_RAG_params(candidate_parameters, accept_language)
                except (ValueError, RAGWorkflowError) as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e),
                    ) from e

            # A parameter may select another component that itself needs
            # downloading; block until every nested one is present. Runs after
            # the RAG defaults are applied so it sees the final configuration.
            nested_missing = missing_downloads(params.parameters, component_registry)
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
                model_class.SCHEMA.model_validate(params.parameters)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid parameters for model {params.model_name}: {e}",
                ) from e

            # Check if the task is a subclass of BaseGenerativeTask
            if not issubclass(task_class, BaseGenerativeTask):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task {params.task_name} is not a valid generative task.",
                )

            # Prompts are stored in their own table: split them out of the
            # validated configuration before persisting it. Any explicit
            # ``prompts`` map wins over prompts embedded in ``parameters``.
            if task_class == RAGTask:
                generation_default = params.parameters.get("prompt")
                clean_parameters, prompt_inputs = prompt_service.split_prompts(
                    params.parameters
                )
                if isinstance(params.prompts, dict):
                    prompt_inputs.update(params.prompts)
            else:
                generation_default = None
                clean_parameters = params.parameters
                prompt_inputs = {}

            now = datetime.now()
            session = GenerativeSession(
                model_name=params.model_name,
                task_name=params.task_name,
                parameters=clean_parameters,
                name=params.name,
                description=params.description,
                created=now,
                last_modified=now,
            )
            db.add(session)
            try:
                # Flush only: the id is needed to create the bindings, but the
                # row must stay uncommitted until every binding and the history
                # entry exist. A failed prompt must never leave a session
                # behind without its prompts.
                db.flush()
            except exc.IntegrityError as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Generative session with name '{params.name}' already exists."
                    ),
                ) from e

            prompt_snapshot = None
            injected_parameters = dict(clean_parameters)
            if task_class == RAGTask:
                prompt_snapshot = prompt_service.sync_session_bindings(
                    session.id,
                    clean_parameters,
                    prompt_inputs,
                    generation_default=generation_default,
                )
                # Materialise the prompts before the commit: a prompt that
                # cannot be rendered must fail the request, not leave a
                # committed session whose next read fails.
                injected_parameters = prompt_service.inject_prompt_slots(
                    session.id, clean_parameters
                )

            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=clean_parameters,
                prompt_bindings=prompt_snapshot,
                model_name=session.model_name,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)
            db.commit()
            db.refresh(session)

            response = _session_payload(
                session,
                parameters=injected_parameters,
                prompts=prompt_snapshot if task_class == RAGTask else None,
            )
            # Localized here so the client never receives a language object.
            response["display_name"] = localize(
                component_registry[session.task_name]["display_name"],
                accept_language,
            )
            return response
        except HTTPException:
            db.rollback()
            raise
        except PromptConflictError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            # Database errors are a server fault, not a bad prompt payload.
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except (RAGWorkflowError, ValueError, LookupError) as e:
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
            return _session_snapshot(session, PromptService(db, component_registry))
        except RAGPromptValidationError as e:
            # The stored prompts are unusable (an unreadable default, a row
            # deleted under the session). That is a state conflict, not a
            # server fault, so report it instead of failing with a 500.
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
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Get all generative sessions ordered by creation date.

    Parameters
    ----------
    task_name : str | None
        If given, return only sessions of that generative task. A view scoped to
        one task (the RAG entry point, say) uses this; the shared session list
        asks for everything and groups the result by task.
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
        returned with prompt-free ``parameters`` and a ``prompt_error`` field
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
            sessions = query.order_by(GenerativeSession.created.asc()).all()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        prompt_service = PromptService(db, component_registry)
        payloads = []
        for session in sessions:
            try:
                payloads.append(_session_snapshot(session, prompt_service))
            except (RAGPromptValidationError, LookupError) as e:
                # One session whose stored prompt became unreadable (a deleted
                # row, an unseeded default) must not hide every other session.
                # Return it without prompts so the client can still list it and
                # show why it cannot be opened.
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
):
    """Delete multiple generative sessions, in a single transaction.

    Parameters
    ----------
    params : GenerativeSessionBulkDeleteParams
        The IDs of the generative sessions to delete. IDs that do not match
        an existing session are silently skipped rather than failing the
        whole request.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            deletion = SessionDocumentService(db, di["job_queue"])
            for session_id in params.ids:
                deletion.delete_session(session_id, commit=False, missing_ok=True)
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
):
    """Delete a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            SessionDocumentService(db, di["job_queue"]).delete_session(session_id)
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            ) from e
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
                # Every history writer captures the prompts active at the time
                # of the entry. A model switch does not change them, but the
                # entry must still own its snapshot so a later prompt edit
                # cannot rewrite it in the diff.
                prompt_snapshot = None
                if _is_rag_session(session):
                    prompt_snapshot = PromptService(
                        db, component_registry
                    ).snapshot_bindings(session.id)
                db.add(
                    GenerativeSessionParameterHistory(
                        session_id=session.id,
                        parameters=new_parameters,
                        prompt_bindings=prompt_snapshot,
                        model_name=model_name,
                        modified_at=datetime.now(),
                    )
                )

            if name is not None or description is not None or model_name is not None:
                session.last_modified = datetime.now()
                db.commit()
                db.refresh(session)
                return _session_snapshot(session, PromptService(db, component_registry))
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
    new_params: dict[str, Any],
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            old_raw_parameters = dict(session.parameters or {})
            try:
                task_class = component_registry[session.task_name]["class"]
            except KeyError as e:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Task '{session.task_name}' is not registered"
                        " in the component registry."
                    ),
                ) from e

            # Accept both the bare parameter body and a wrapper carrying an
            # explicit ``prompts`` map. Explicit inputs win over prompts
            # embedded in ``parameters``.
            body = dict(new_params)
            body_prompts = None
            if "parameters" in body and not isinstance(body["parameters"], dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="'parameters' must be an object of session parameters.",
                )
            if isinstance(body.get("parameters"), dict):
                body_prompts = body.get("prompts")
                body = dict(body["parameters"])
            elif "prompts" in body:
                body_prompts = body.get("prompts")
                bare_body: dict[str, Any] = {}
                for key, value in body.items():
                    if key != "prompts":
                        bare_body[key] = value
                body = bare_body
            if body_prompts is not None and not isinstance(body_prompts, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="'prompts' must be an object keyed by prompt slot path.",
                )

            prompt_service = PromptService(db, component_registry)
            prompt_snapshot = None

            # ── RAG-specific validation of new_params ──
            if task_class is not None and task_class == RAGTask:
                old_parameters, _ = prompt_service.split_prompts(old_raw_parameters)
                validation_payload = body
                if isinstance(body_prompts, dict):
                    # Fold the map into a candidate configuration first so a
                    # prompt can be sent for a slot the request does not repeat,
                    # and validate only the keys the request (or the map)
                    # touches, keeping partial-update semantics.
                    candidate = {
                        **copy.deepcopy(old_parameters),
                        **copy.deepcopy(body),
                    }
                    prepared = prompt_service.apply_prompt_map(candidate, body_prompts)
                    touched = set(body) | {
                        prompt_service.slot_top_level_key(path) for path in body_prompts
                    }
                    validation_payload = {
                        key: prepared.get(key, body.get(key)) for key in touched
                    }
                try:
                    normalized = SessionValidationService(
                        db, component_registry
                    ).validate_update_payload(validation_payload)
                except (ValueError, RAGWorkflowError) as e:
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

                generation_default = normalized.get("prompt")
                new_clean, new_prompt_inputs = prompt_service.split_prompts(normalized)
                if isinstance(body_prompts, dict):
                    new_prompt_inputs.update(body_prompts)

                # Merge validated, prompt-free new params into old params
                updated_parameters = {**old_parameters, **new_clean}

                # A save that changes neither the configuration nor the bound
                # prompts must not add a history row or bump last_modified.
                if updated_parameters == old_parameters:
                    preview = prompt_service.preview_session_bindings(
                        session.id,
                        updated_parameters,
                        new_prompt_inputs,
                        generation_default=generation_default,
                    )
                    current_bindings = prompt_service.snapshot_bindings(session.id)
                    if preview == current_bindings:
                        return {
                            "id": session.id,
                            "parameters": prompt_service.inject_prompt_slots(
                                session.id, old_parameters
                            ),
                            "prompts": current_bindings,
                        }

                # A running index writes the very rows the cleanup below
                # deletes, so it has to be stopped before, not after.
                cancel_live_index_job(session, di["job_queue"])

                # Cleanup orphaned RAG resources. Both sides are prompt-free, so
                # editing a prompt never invalidates the retriever or index.
                # ``commit=False`` keeps the update in the same transaction as
                # the binding sync and history entry below: an error must not
                # leave the session half-updated.
                CleanupService(db).cleanup_orphaned_resources(
                    session_id,
                    old_parameters,
                    updated_parameters,
                    commit=False,
                )

                prompt_snapshot = prompt_service.sync_session_bindings(
                    session.id,
                    updated_parameters,
                    new_prompt_inputs,
                    generation_default=generation_default,
                )
                # Materialise before the commit: a prompt that cannot be
                # rendered must fail the request instead of leaving a committed
                # session whose next read fails.
                injected_parameters = prompt_service.inject_prompt_slots(
                    session.id, updated_parameters
                )
            else:
                # Non-RAG update: simple merge without RAG validation
                updated_parameters = {**old_raw_parameters, **body}
                injected_parameters = updated_parameters

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

            if task_class is not None and task_class == RAGTask:
                return {
                    "id": session.id,
                    "parameters": injected_parameters,
                    "prompts": prompt_snapshot,
                }
            return {"id": session.id, "parameters": session.parameters}
        except HTTPException:
            db.rollback()
            raise
        except PromptConflictError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            # Database errors are a server fault, not a bad prompt payload.
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except (RAGWorkflowError, ValueError, LookupError) as e:
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
        Registry used to resolve prompts for RAG history entries.

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

            prompt_service = PromptService(db, component_registry)
            materialize = _is_rag_session(session)

            # Convert the objects to dictionaries (explicit loop for clarity)
            history_list = []
            for entry in parameters_history:
                entry_parameters = dict(entry.parameters or {})
                if materialize:
                    entry_parameters = prompt_service.materialize_history_parameters(
                        entry_parameters,
                        getattr(entry, "prompt_bindings", None),
                        session_id=session_id,
                    )
                history_list.append(
                    {
                        "id": entry.id,
                        "session_id": entry.session_id,
                        "parameters": entry_parameters,
                        "prompt_bindings": getattr(entry, "prompt_bindings", None),
                        "modified_at": entry.modified_at,
                    }
                )
            return history_list
        except RAGPromptValidationError as e:
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
        Registry used to resolve prompts for RAG history entries.

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

            prompt_service = PromptService(db, component_registry)
            materialize = _is_rag_session(session)
            entries = []
            for entry in parameters_history:
                entry_parameters = dict(entry.parameters or {})
                if materialize:
                    entry_parameters = prompt_service.materialize_history_parameters(
                        entry_parameters,
                        getattr(entry, "prompt_bindings", None),
                        session_id=session_id,
                    )
                entries.append(
                    {
                        "id": entry.id,
                        "parameters": entry_parameters,
                        "model_name": getattr(entry, "model_name", None),
                        "modified_at": entry.modified_at,
                    }
                )

            if not entries:
                return []

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
                if curr_model and prev_model and curr_model != prev_model:
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

        except RAGPromptValidationError as e:
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
