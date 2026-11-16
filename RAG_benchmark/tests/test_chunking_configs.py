"""Coverage guards for the chunking benchmark matrix."""

from __future__ import annotations

from collections import Counter

from DashAI.back.initial_components import get_initial_components
from DashAI.back.models.RAG.chunking_models.base_chunking_model import (
    BaseChunkingModel,
)
from RAG_benchmark.app.components.chunking import CHUNKER_CONFIGS


def test_every_registered_chunker_is_benchmarked() -> None:
    """Every concrete chunker in the registry has a benchmark config."""
    registered = {
        component.__name__
        for component in get_initial_components()
        if isinstance(component, type)
        and issubclass(component, BaseChunkingModel)
        and component is not BaseChunkingModel
    }
    configured = {cfg["component_class"] for cfg in CHUNKER_CONFIGS}

    assert configured == registered


def test_every_chunker_class_has_at_least_two_configs() -> None:
    """Each chunker class compares at least two configurations."""
    counts = Counter(cfg["component_class"] for cfg in CHUNKER_CONFIGS)

    for component, count in counts.items():
        assert count >= 2, f"{component} declares {count} config(s)"


def test_chunking_config_keys_are_unique() -> None:
    """``(component_class, model_name, config_name)`` identifies one config."""
    keys = [
        (cfg["component_class"], cfg["model_name"], cfg["config_name"])
        for cfg in CHUNKER_CONFIGS
    ]

    assert len(keys) == len(set(keys))
