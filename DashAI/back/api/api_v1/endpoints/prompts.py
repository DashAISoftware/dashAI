import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import exc, select
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.rag_prompt import (
    RAGPromptSchema,
    RAGPromptUpdateSchema,
)
from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    GenerativeSessionParameterHistory,
    RAGPrompt,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.RAG.prompts.generation.default_QA_rag_generation_prompt import (
    DefaultQARAGGenerationPrompt,
)
from DashAI.back.models.RAG.prompts.generation.default_rag_generation_prompt import (
    DefaultRAGGenerationPrompt,
)
from DashAI.back.models.RAG.prompts.prompt import Prompt

router = APIRouter()
log = logging.getLogger(__name__)


def _validate_prompt_template(
    prompt_class_name: str,
    template: str,
    component_registry: ComponentRegistry,
) -> None:
    if prompt_class_name not in component_registry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Component {prompt_class_name} is not registered.",
        )

    prompt_component = component_registry[prompt_class_name]
    prompt_class = prompt_component["class"]
    if not issubclass(prompt_class, Prompt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Component {prompt_class_name} is not a valid Prompt subclass.",
        )

    if not prompt_class.validate_template(template):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid template for prompt {prompt_class_name}. "
                f"Required tokens are: {prompt_class.get_required_placeholders()}"
            ),
        )


def _serialize_prompt(prompt: RAGPrompt) -> Dict[str, Any]:
    return {
        "id": prompt.id,
        "class_name": prompt.class_name,
        "name": prompt.name,
        "parameters": prompt.parameters,
        "created": prompt.created,
        "last_modified": prompt.last_modified,
    }


def _build_session_prompt_name(base_name: str, session_id: int, db) -> str:
    candidate = f"{base_name} - session {session_id}"
    suffix = 2
    while db.execute(select(RAGPrompt.id).where(RAGPrompt.name == candidate)).scalar():
        candidate = f"{base_name} - session {session_id} ({suffix})"
        suffix += 1
    return candidate


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_rag_prompt(
    prompt: RAGPromptSchema,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new RAGPrompt entry in the database."""
    with session_factory() as db:
        # Validate presence of parameters and template explicitly for readability
        if not prompt.parameters:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Prompt parameters are required and must include a template.",
            )

        if "templates" in prompt.parameters:
            for _lang, tmpl in prompt.parameters["templates"].items():
                _validate_prompt_template(prompt.class_name, tmpl, component_registry)
        elif "template" in prompt.parameters:
            _validate_prompt_template(
                prompt.class_name,
                prompt.parameters["template"],
                component_registry,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Prompt parameters must include 'template' or 'templates'.",
            )
        new_prompt = RAGPrompt(
            class_name=prompt.class_name,
            name=prompt.name,
            parameters=prompt.parameters,
        )
        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)
        return {"id": new_prompt.id}


@router.patch("/{prompt_id}", status_code=status.HTTP_200_OK)
async def update_rag_prompt(
    prompt_id: int,
    prompt: RAGPromptUpdateSchema,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Update an existing prompt in place."""
    with session_factory() as db:
        try:
            existing_prompt = db.get(RAGPrompt, prompt_id)
            if existing_prompt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Prompt not found",
                )

            changed = False

            if prompt.name is not None:
                new_name = prompt.name.strip()
                if not new_name:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Prompt name cannot be empty",
                    )
                if new_name != existing_prompt.name:
                    existing_prompt.name = new_name
                    changed = True

            if prompt.parameters is not None:
                if "templates" in prompt.parameters:
                    for _lang, tmpl in prompt.parameters["templates"].items():
                        _validate_prompt_template(
                            existing_prompt.class_name,
                            tmpl,
                            component_registry,
                        )
                elif "template" in prompt.parameters:
                    _validate_prompt_template(
                        existing_prompt.class_name,
                        prompt.parameters["template"],
                        component_registry,
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "Prompt parameters must include 'template' or 'templates'."
                        ),
                    )
                existing_prompt.parameters = prompt.parameters
                changed = True

            if not changed:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )

            existing_prompt.last_modified = datetime.now()
            db.commit()
            db.refresh(existing_prompt)
            return _serialize_prompt(existing_prompt)
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.post("/{prompt_id}/sessions/{session_id}", status_code=status.HTTP_201_CREATED)
async def update_rag_prompt_for_session(
    prompt_id: int,
    session_id: int,
    prompt: RAGPromptUpdateSchema,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a session-scoped copy of a prompt and attach it to the session."""
    with session_factory() as db:
        try:
            existing_prompt = db.get(RAGPrompt, prompt_id)
            if existing_prompt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Prompt not found",
                )

            session = db.get(GenerativeSession, session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generative session not found",
                )

            if prompt.parameters is not None:
                if "templates" in prompt.parameters:
                    for _lang, tmpl in prompt.parameters["templates"].items():
                        _validate_prompt_template(
                            existing_prompt.class_name,
                            tmpl,
                            component_registry,
                        )
                elif "template" in prompt.parameters:
                    _validate_prompt_template(
                        existing_prompt.class_name,
                        prompt.parameters["template"],
                        component_registry,
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "Prompt parameters must include 'template' or 'templates'."
                        ),
                    )
                new_parameters = prompt.parameters
            else:
                new_parameters = existing_prompt.parameters

            # Make parameters unique per session to avoid UNIQUE constraint
            new_parameters = dict(new_parameters or {})
            new_parameters["cloned_for_session"] = session_id

            # Choose a base name in an explicit, easy-to-read way
            if prompt.name:
                candidate_name = prompt.name
            elif existing_prompt.name:
                candidate_name = existing_prompt.name
            else:
                candidate_name = existing_prompt.class_name

            base_name = (candidate_name or "").strip()
            new_name = _build_session_prompt_name(base_name, session_id, db)

            new_prompt = RAGPrompt(
                class_name=existing_prompt.class_name,
                name=new_name,
                parameters=new_parameters,
            )
            db.add(new_prompt)
            db.commit()
            db.refresh(new_prompt)

            session_parameters = dict(session.parameters or {})
            session_parameters["prompt_id"] = new_prompt.id
            session.parameters = session_parameters
            session.last_modified = datetime.now()
            db.add(
                GenerativeSessionParameterHistory(
                    session_id=session.id,
                    parameters=session_parameters,
                    modified_at=datetime.now(),
                )
            )
            db.commit()
            db.refresh(session)

            return {
                "prompt": _serialize_prompt(new_prompt),
                "session_id": session.id,
                "parameters": session.parameters,
            }
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_prompts(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Get all available RAG prompts.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with all prompts on the database.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """
    with session_factory() as db:
        try:
            prompts = db.query(RAGPrompt).all()

            if len(prompts) == 0:
                default_generation_prompt = RAGPrompt(
                    class_name=DefaultRAGGenerationPrompt.__name__,
                    name="Default RAG Generation Prompt",
                    parameters={
                        "templates": DefaultRAGGenerationPrompt.metadata["templates"],
                        "language": "en",
                    },
                )
                default_qa_prompt = RAGPrompt(
                    class_name=DefaultQARAGGenerationPrompt.__name__,
                    name="Default QA RAG Generation Prompt",
                    parameters={
                        "templates": DefaultQARAGGenerationPrompt.metadata["templates"],
                        "language": "en",
                    },
                )
                db.add(default_generation_prompt)
                db.add(default_qa_prompt)
                db.commit()
                prompts = db.query(RAGPrompt).all()

            prompt_responses = []
            for prompt in prompts:
                prompt_responses.append(
                    {
                        "id": prompt.id,
                        "class_name": prompt.class_name,
                        "name": prompt.name,
                        "parameters": prompt.parameters,
                        "created": prompt.created,
                        "last_modified": prompt.last_modified,
                    }
                )

            return prompt_responses
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
