import gc
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from DashAI.back.core.schema_fields import default_parameters_from_schema

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry


class InsightProviderError(Exception):
    """Raised when an InsightProvider cannot produce a completion."""


class InsightProvider(ABC):
    """Where a generated insight's text comes from: a local model or a remote API."""

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError

    def close(self) -> None:
        """Release any resources held to answer ``complete()``. No-op by default."""
        return None


class LocalModelInsightProvider(InsightProvider):
    """Wraps an already-registered local generative model (e.g. a GGUF
    checkpoint loaded via llama.cpp) so it can answer ``InsightProvider.complete()``.

    Loading a local model is expensive (memory, sometimes GPU), so it stays
    unloaded until the first ``complete()`` call and is released via
    ``close()`` — the same load/generate/free cycle ``GenerativeJob`` already
    uses elsewhere in DashAI for local generative models.
    """

    def __init__(
        self,
        model_name: str,
        generation_params: Optional[Dict[str, Any]],
        component_registry: "ComponentRegistry",
    ) -> None:
        self._model_name = model_name
        self._generation_params = generation_params or {}
        self._component_registry = component_registry
        self._model = None

    def complete(self, messages: List[Dict[str, str]]) -> str:
        model = self._ensure_model()
        output = model.generate(messages)
        return output[0]

    def _ensure_model(self):
        if self._model is not None:
            return self._model

        model_class = self._component_registry[self._model_name]["class"]
        if (
            getattr(model_class, "REQUIRES_DOWNLOAD", False)
            and not model_class.is_downloaded()
        ):
            raise InsightProviderError(
                f"Model '{self._model_name}' is not downloaded. "
                "Download it before requesting an AI insight."
            )
        params = {}
        schema_cls = getattr(model_class, "SCHEMA", None)
        if schema_cls is not None:
            params.update(default_parameters_from_schema(schema_cls))
        params.update(self._generation_params)
        self._model = model_class(**params)
        return self._model

    def close(self) -> None:
        self._model = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        gc.collect()


def build_provider(
    kind: str,
    params: Optional[Dict[str, Any]],
    component_registry: "ComponentRegistry",
) -> InsightProvider:
    """Resolve an ``InsightProvider`` from a stored ``provider_kind``/``params``.

    The only place in this layer with a closed ``if``/``elif`` on provider
    kind — acceptable because ``InsightProvider`` has exactly two known
    families (local model, remote API), unlike consumers, which are
    open-ended and never need a branch here.
    """
    params = params or {}
    if kind == "local":
        return LocalModelInsightProvider(
            model_name=params["model_name"],
            generation_params=params.get("generation_params"),
            component_registry=component_registry,
        )
    if kind == "remote":
        raise InsightProviderError(
            "Remote AI insight providers are not implemented yet."
        )
    raise InsightProviderError(f"Unknown insight provider kind: '{kind}'.")
