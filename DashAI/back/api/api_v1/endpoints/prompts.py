import logging

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.api.api_v1.schemas.rag_prompt import RAGPromptSchema
from DashAI.back.dependencies.database.models import (
    RAGPrompt,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.models.RAG import (
    DefaultAugmentationPrompt,
    DefaultGenerationPrompt,
    DefaultQnAGenerationPrompt,
    Prompt,
)

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_rag_prompt(
    prompt: RAGPromptSchema,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new RAGPrompt entry in the database."""
    with session_factory() as db:
        prompt_class_name = prompt.class_name
        if prompt_class_name not in component_registry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Component {prompt_class_name} is not registered.",
            )
        prompt_component = component_registry[prompt_class_name]
        prompt_class: Prompt = prompt_component["class"]
        if not issubclass(prompt_class, Prompt):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Component {prompt_class_name} is not a valid Prompt subclass.",
            )
        template_validation = prompt_class.validate_template(
            prompt.parameters["template"]
        )
        if not template_validation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid template for prompt {prompt.class_name}. "
                    f"Required tokens are: "
                    f"{prompt_class.get_required_placeholders()}"
                ),
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
                    class_name=DefaultGenerationPrompt.__name__,
                    name="Default Generation Prompt",
                    parameters={"template": DefaultAugmentationPrompt.template},
                )
                default_qa_prompt = RAGPrompt(
                    class_name=DefaultQnAGenerationPrompt.__name__,
                    name="Default QnA Prompt",
                    parameters={"template": DefaultQnAGenerationPrompt.template},
                )
                default_augmentation_prompt = RAGPrompt(
                    class_name=DefaultAugmentationPrompt.__name__,
                    name="Default Augmentation Prompt",
                    parameters={"template": DefaultAugmentationPrompt.template},
                )
                db.add(default_generation_prompt)
                db.add(default_qa_prompt)
                db.add(default_augmentation_prompt)
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
