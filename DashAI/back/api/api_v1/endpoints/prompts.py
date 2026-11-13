from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from kink import di
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.RAG_prompt import (
    RAGPromptForkSchema,
    RAGPromptSchema,
    RAGPromptUpdateSchema,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.RAG.exceptions import (
    RAGDatabaseError,
    RAGPromptError,
    RAGPromptValidationError,
)
from DashAI.back.services.RAG.prompt_service import (
    PromptConflictError,
    PromptInUseError,
    PromptService,
)
from DashAI.back.services.RAG.session_document_service import (
    SessionDocumentService,
)

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_RAG_prompt(  # noqa: N802
    prompt: RAGPromptSchema,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new RAGPrompt entry in the database."""

    with session_factory() as db:
        try:
            service = PromptService(db, component_registry)
            result = service.create(
                prompt.class_name, prompt.name, prompt.parameters or {}
            )
            return {"id": result.id}
        except PromptConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except RAGPromptValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            # A generic database failure is not a duplicate-content signal;
            # conflicts are raised as ``PromptConflictError`` above.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create the prompt.",
            ) from e
        except RAGPromptError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_prompts(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all available RAG prompts."""

    component_registry = di["component_registry"]
    with session_factory() as db:
        service = PromptService(db, component_registry)
        return service.get_all()


@router.get("/library", status_code=status.HTTP_200_OK)
async def get_library_prompts(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """List the prompts the prompt library page shows.

    Includes the user-created library rows and the built-in default prompts.
    Internal pipeline drafts are excluded. Each prompt reports the RAG sessions
    that use it, so the UI can name them before deleting it.

    Parameters
    ----------
    session_factory : sessionmaker
        Session factory from the DI container.
    component_registry : ComponentRegistry
        Registry used by the service.

    Returns
    -------
    list of PromptResponse
        Library and built-in prompts ordered by id.

    Raises
    ------
    HTTPException
        500 on database errors.
    """
    with session_factory() as db:
        try:
            return PromptService(db, component_registry).get_library()
        except RAGDatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e


@router.get("/{prompt_id}", status_code=status.HTTP_200_OK)
async def get_RAG_prompt(  # noqa: N802
    prompt_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Get one RAG prompt by id.

    Parameters
    ----------
    prompt_id : int
        Primary key of the prompt.
    session_factory : sessionmaker
        Session factory from the DI container.
    component_registry : ComponentRegistry
        Registry used by the service.

    Returns
    -------
    PromptResponse
        The serialized prompt.

    Raises
    ------
    HTTPException
        404 for an unknown prompt, 409 for an internal draft (drafts are
        session-local and have no standalone identity), 500 on database
        errors.
    """
    with session_factory() as db:
        try:
            prompt = PromptService(db, component_registry).get(prompt_id)
            if prompt.origin == "draft":
                # Internal drafts belong to one session's binding and must not
                # be read or adopted through the catalog API.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Prompt {prompt_id} is an internal draft and is not "
                        "addressable on its own."
                    ),
                )
            return prompt
        except HTTPException:
            raise
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e


@router.patch("/{prompt_id}", status_code=status.HTTP_200_OK)
async def update_RAG_prompt(  # noqa: N802
    prompt_id: int,
    payload: RAGPromptUpdateSchema,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Edit a prompt saved in the library in place.

    Built-in defaults are immutable and must be forked; internal drafts are
    promoted by creating a library prompt instead.

    Parameters
    ----------
    prompt_id : int
        Primary key of the prompt.
    payload : RAGPromptUpdateSchema
        New name and/or parameters. Omitted fields keep their stored value.
    session_factory : sessionmaker
        Session factory from the DI container.
    component_registry : ComponentRegistry
        Registry used by the service.

    Returns
    -------
    PromptResponse
        The updated prompt.

    Raises
    ------
    HTTPException
        404 for an unknown prompt, 409 for a default/draft or duplicate
        content, 400 for invalid parameters, 500 on database errors.
    """
    with session_factory() as db:
        service = PromptService(db, component_registry)
        try:
            current = service.get(prompt_id)
            if current.is_default:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Built-in default prompts cannot be edited; fork them "
                        "to make a library copy."
                    ),
                )
            if not current.is_library:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Only prompts created from the prompt library can be edited."
                    ),
                )
            return service.update_library_prompt(
                prompt_id,
                name=payload.name,
                parameters=payload.parameters,
            )
        except HTTPException:
            raise
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except PromptConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except RAGPromptValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e


@router.post("/{prompt_id}/fork", status_code=status.HTTP_201_CREATED)
async def fork_RAG_prompt(  # noqa: N802
    prompt_id: int,
    payload: RAGPromptForkSchema,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Create a user-owned copy of a prompt.

    Forking a default switches it to its ``Custom*`` counterpart and records
    ``based_on_id`` lineage. When a library row already owns the content it is
    returned instead of duplicating it.

    Parameters
    ----------
    prompt_id : int
        Primary key of the source prompt.
    payload : RAGPromptForkSchema
        Name for the copy and an optional parameter override.
    session_factory : sessionmaker
        Session factory from the DI container.
    component_registry : ComponentRegistry
        Registry used by the service.

    Returns
    -------
    PromptResponse
        The new, promoted, or existing library prompt.

    Raises
    ------
    HTTPException
        404 for an unknown prompt, 409 for duplicate/default content, 400 for
        invalid parameters, 500 on database errors.
    """
    with session_factory() as db:
        try:
            return PromptService(db, component_registry).fork_prompt(
                prompt_id,
                payload.name,
                payload.parameters,
            )
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except PromptConflictError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except RAGPromptValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_RAG_prompt(  # noqa: N802
    prompt_id: int,
    cascade_sessions: bool = Query(default=False),
    detach: bool = Query(default=False),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Delete a prompt saved in the prompt library.

    Parameters
    ----------
    prompt_id : int
        Primary key of the prompt.
    cascade_sessions : bool
        Delete the RAG sessions that use the prompt as well. When false and
        such sessions exist, the request fails with 409 and lists them.
    detach : bool
        Keep the sessions and repoint their bindings to an internal draft copy
        of the prompt. Mutually exclusive with ``cascade_sessions``.
    session_factory : sessionmaker
        Session factory from the DI container.
    component_registry : ComponentRegistry
        Registry used by the service.

    Returns
    -------
    Response
        204 No Content.

    Raises
    ------
    HTTPException
        400 when both delete options are requested, 404 for an unknown prompt,
        409 when it is used or not deletable, 500 on database errors.
    """
    if detach and cascade_sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose either detach or cascade_sessions, not both.",
        )
    with session_factory() as db:
        try:
            PromptService(db, component_registry).delete(
                prompt_id,
                cascade_sessions=cascade_sessions,
                detach=detach,
                session_service=SessionDocumentService(db, di["job_queue"]),
            )
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except PromptInUseError as e:
            sessions = []
            for session in e.sessions:
                sessions.append({"id": session.id, "name": session.name})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": str(e), "sessions": sessions},
            ) from e
        except RAGPromptValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            ) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)
