"""Factory for text-to-text generation models (LLMs).

Resolves a component name + parameters into an instantiated model
via the component registry, with lookup-or-create DB semantics.
"""

from dataclasses import dataclass
from typing import Any, Dict

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    RAGGenerationModel as GenerationDBModel,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)


@dataclass(frozen=True)
class LLMFactoryResult:
    """Result of LLM instantiation via LLMFactory."""

    db_record_id: int
    model: TextToTextGenerationTaskModel


class LLMFactory:
    """Creates LLM instances with lookup-or-create DB semantics."""

    def __init__(self, db: Session, component_registry: ComponentRegistry):
        self._db = db
        self._registry = component_registry

    def create(self, component_name: str, params: Dict[str, Any]) -> LLMFactoryResult:
        sorted_params = dict(sorted(params.items()))
        existing = (
            self._db.query(GenerationDBModel)
            .filter_by(class_name=component_name, parameters=sorted_params)
            .first()
        )
        if existing is not None:
            model_class = self._registry[existing.class_name]["class"]
            return LLMFactoryResult(
                db_record_id=existing.id,
                model=model_class(**existing.parameters),
            )

        db_record = GenerationDBModel(
            class_name=component_name,
            parameters=sorted_params,
        )
        self._db.add(db_record)
        self._db.commit()
        self._db.refresh(db_record)

        model_class = self._registry[component_name]["class"]
        return LLMFactoryResult(
            db_record_id=db_record.id,
            model=model_class(**params),
        )
