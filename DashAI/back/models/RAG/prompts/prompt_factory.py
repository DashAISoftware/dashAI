"""Factory for prompt templates with lookup-or-create semantics.

Resolves a component name + parameters into a Prompt instance,
creating a RAGPrompt DB record when no matching record exists.
"""

from dataclasses import dataclass
from typing import Any, Dict

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import RAGPrompt as PromptDBModel
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.prompts import Prompt


@dataclass(frozen=True)
class PromptFactoryResult:
    """Result of prompt instantiation via PromptFactory."""

    db_record_id: int
    model: Prompt


class PromptFactory:
    """Creates Prompt instances with automatic DB record reuse."""

    def __init__(self, db: Session, component_registry: ComponentRegistry):
        self._db = db
        self._registry = component_registry

    def create(
        self, component_name: str, params: Dict[str, Any]
    ) -> PromptFactoryResult:
        sorted_params: Dict[str, Any] = dict(sorted(params.items()))
        existing: PromptDBModel | None = (
            self._db.query(PromptDBModel)
            .filter_by(class_name=component_name, parameters=sorted_params)
            .first()
        )
        if existing is not None:
            prompt_class = self._registry[existing.class_name]["class"]
            return PromptFactoryResult(
                db_record_id=existing.id,
                model=prompt_class(**existing.parameters),
            )

        db_record = PromptDBModel(
            class_name=component_name,
            parameters=sorted_params,
        )
        self._db.add(db_record)
        self._db.commit()
        self._db.refresh(db_record)

        prompt_class = self._registry[component_name]["class"]
        return PromptFactoryResult(
            db_record_id=db_record.id,
            model=prompt_class(**params),
        )
