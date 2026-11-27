"""Unified factory that delegates to type-specific sub-factories.

Phase 1 of the 3-phase lifecycle (Construction -> Initialization -> Persistence).
Builds models in memory -- no I/O, no DB access.
"""

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    BaseChunkingModel,
)
from DashAI.back.models.RAG.chunking_models.chunking_model_factory import (
    ChunkingModelFactory,
)
from DashAI.back.models.RAG.llm_factory import LLMFactory, LLMFactoryResult
from DashAI.back.models.RAG.prompts.prompt_factory import (
    PromptFactory,
    PromptFactoryResult,
)
from DashAI.back.models.RAG.transformation import (
    TransformationFactory,
    TransformationFactoryResult,
)


class RAGModelsFactory:
    """Delegates model construction to type-specific sub-factories.

    Every ``create_*`` method:
    - Accepts a component name + params dict
    - Delegates to the corresponding sub-factory
    - Returns the model -- no I/O, no DB
    """

    def __init__(self, registry: ComponentRegistry):
        """Initialise the factory with a component registry.

        Args:
            registry: The ComponentRegistry used to resolve component
                names to their implementations.
        """
        self._registry = registry

    def create_chunking_model(self, component: str, params: dict) -> BaseChunkingModel:
        """Build a chunking model via ChunkingModelFactory. Phase 1 only."""
        return ChunkingModelFactory(self._registry).create(component, params.copy())

    def create_prompt(self, component: str, params: dict) -> PromptFactoryResult:
        """Build a prompt via PromptFactory. Phase 1 only."""
        return PromptFactory(self._registry).create(component, params)

    def create_llm(self, component: str, params: dict) -> LLMFactoryResult:
        """Build an LLM via LLMFactory. Phase 1 only."""
        return LLMFactory(self._registry).create(component, params)

    def create_query_transformation(
        self, component: str, params: dict
    ) -> TransformationFactoryResult:
        """Build a query transformer via TransformationFactory. Phase 1 only."""
        return TransformationFactory(self._registry).create(component, params)
