from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from kink import di
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.RAG_prompt import (
    RAGPromptSchema,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.RAG.exceptions import (
    RAGDatabaseError,
    RAGPromptError,
    RAGPromptValidationError,
)
from DashAI.back.services.RAG.prompt_service import PromptInUseError, PromptService
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
        except RAGPromptValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
            ) from e
        except RAGDatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A prompt with these parameters already exists.",
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
    """List the prompts a user saved in the prompt library.

    Internal pipeline rows and built-in defaults are excluded. Each prompt
    reports the RAG sessions that use it, so the UI can name them before
    deleting it.

    Parameters
    ----------
    session_factory : sessionmaker
        Session factory from the DI container.
    component_registry : ComponentRegistry
        Registry used by the service.

    Returns
    -------
    list of PromptResponse
        Library prompts ordered by id.

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


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_RAG_prompt(  # noqa: N802
    prompt_id: int,
    cascade_sessions: bool = Query(default=False),
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
        404 for an unknown prompt, 409 when it is used or not deletable,
        500 on database errors.
    """
    with session_factory() as db:
        try:
            PromptService(db, component_registry).delete(
                prompt_id,
                cascade_sessions=cascade_sessions,
                session_service=SessionDocumentService(db, di["job_queue"]),
            )
        except LookupError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
            ) from e
        except PromptInUseError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": str(e),
                    "sessions": [
                        {"id": session.id, "name": session.name}
                        for session in e.sessions
                    ],
                },
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
