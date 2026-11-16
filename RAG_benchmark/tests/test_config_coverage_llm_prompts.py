"""Coverage guards for the component-benchmark config matrices.

Every benchmarked component class must appear in at least two configs so each
category compares a baseline against a variant instead of reporting a single
point. The checks are purely data-level: no template is rendered and no model
is loaded or downloaded.
"""

from __future__ import annotations

from collections import Counter

import pytest

from RAG_benchmark.app.benchmark_data import LLM_MAP, PROMPT_MAP
from RAG_benchmark.app.components import llm as llm_mod
from RAG_benchmark.app.components import transformation as transformation_mod
from RAG_benchmark.app.components.prompts import PROMPT_CONFIGS

#: Minimum number of configs every benchmarked component class must declare.
MIN_CONFIGS_PER_CLASS = 2

#: Checkpoints intentionally left out of the LLM matrix (too large).
MIXTRAL_CLASSES = frozenset({"Mixtral8x7BInstructQ4KM", "Mixtral8x7BInstructQ2K"})

#: Registered checkpoints that the LLM matrix does not benchmark. They live in
#: ``LLM_MAP`` because the query-transformation and LLM-retriever loaders resolve
#: their nested models through it, not because the LLM benchmark covers them.
#: ``Qwen25_3BInstruct`` / ``Qwen25_7BInstruct`` are the larger Qwen 2.5
#: siblings: adding them to the LLM matrix would double its runtime without
#: serving this thesis' comparison.
LLM_MAP_ONLY_CLASSES = frozenset({"Qwen25_3BInstruct", "Qwen25_7BInstruct"})

#: Evaluation prompts consumed by the LLM retrievers.
_EVALUATION_PROMPT_COMPONENTS = (
    "DefaultAgenticRetrieverPrompt",
    "CustomAgenticRetrieverPrompt",
    "DefaultAgenticRerankerPrompt",
    "CustomAgenticRerankerPrompt",
)


def _class_counts(configs: list[dict]) -> Counter:
    """Count the configs declared per ``component_class``."""
    return Counter(cfg["component_class"] for cfg in configs)


@pytest.mark.parametrize(
    ("label", "configs"),
    [
        ("llm", llm_mod.LLM_CONFIGS),
        ("transformation", transformation_mod.TRANSFORMATION_CONFIGS),
        ("prompt", PROMPT_CONFIGS),
    ],
    ids=["llm", "transformation", "prompt"],
)
def test_every_component_class_has_at_least_two_configs(
    label: str, configs: list[dict]
) -> None:
    """No benchmarked class reports a single config in its category."""
    counts = _class_counts(configs)

    assert counts, f"{label} declares no configs"
    sparse = {
        component_class: count
        for component_class, count in counts.items()
        if count < MIN_CONFIGS_PER_CLASS
    }
    assert not sparse, f"{label} classes with fewer than two configs: {sparse}"


def test_llm_configs_cover_every_non_mixtral_checkpoint() -> None:
    """Dropping a benchmarked checkpoint from the LLM matrix fails loudly."""
    covered = set(_class_counts(llm_mod.LLM_CONFIGS))

    assert covered == set(LLM_MAP) - MIXTRAL_CLASSES - LLM_MAP_ONLY_CLASSES


@pytest.mark.parametrize(
    "component_class",
    _EVALUATION_PROMPT_COMPONENTS,
)
def test_evaluation_prompts_are_benchmarked(component_class: str) -> None:
    """The LLM retriever evaluation prompts are registered and benchmarked."""
    assert component_class in PROMPT_MAP
    assert component_class in _class_counts(PROMPT_CONFIGS)


def test_prompt_configs_cover_every_registered_prompt() -> None:
    """Every ``PROMPT_MAP`` entry is exercised by at least one config."""
    assert set(PROMPT_MAP) == set(_class_counts(PROMPT_CONFIGS))
