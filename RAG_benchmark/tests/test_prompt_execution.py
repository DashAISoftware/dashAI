"""Execution tests for the prompt-formatting component benchmarks.

Every registered prompt component runs through the real ``_execute_prompt``
executor — no LLM is involved and nothing is downloaded — so the tests assert
the placeholder resolution each prompt family must honour. They also prove the
full default-language matrix (en/es/pt per default class) and two genuine
custom templates per custom class render exactly the template their config
carries, including the evaluation prompts the LLM retrievers use.
"""

from __future__ import annotations

import importlib

import pytest

from DashAI.back.models.RAG.prompts.evaluation.default_agentic_reranker_prompt import (
    TEMPLATES as FILTER_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.evaluation.default_agentic_retriever_prompt import (  # noqa: E501
    TEMPLATES as SUFFICIENCY_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.generation.default_QA_RAG_generation_prompt import (  # noqa: E501
    TEMPLATES as QA_GENERATION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.generation.default_RAG_generation_prompt import (  # noqa: E501
    TEMPLATES as GENERATION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_decomposition_prompt import (  # noqa: E501
    TEMPLATES as DECOMPOSITION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_decomposition_prompt import (  # noqa: E501
    DefaultQueryDecompositionPrompt,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_expansion_prompt import (  # noqa: E501
    TEMPLATES as EXPANSION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_rewriting_prompt import (  # noqa: E501
    TEMPLATES as REWRITING_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.transformation.llm_query_transformation import (
    format_history,
)
from RAG_benchmark.app.benchmark_data import (
    PROMPT_MAP,
    TRANSFORMATION_HISTORY,
    TRANSFORMATION_MESSAGE,
)
from RAG_benchmark.app.components.prompts import (
    _CUSTOM_PROMPT_CLASSES,
    GENERATION_SAMPLE_QUESTION,
    PROMPT_CONFIGS,
    _assert_prompt_rendered,
    _execute_prompt,
    _prompt_family,
    _render,
    _template_prefix,
)

_DEFAULT_TEMPLATES = {
    "DefaultQueryRewritingPrompt": REWRITING_PROMPT_TEMPLATES,
    "DefaultQueryExpansionPrompt": EXPANSION_PROMPT_TEMPLATES,
    "DefaultQueryDecompositionPrompt": DECOMPOSITION_PROMPT_TEMPLATES,
    "DefaultRAGGenerationPrompt": GENERATION_PROMPT_TEMPLATES,
    "DefaultQARAGGenerationPrompt": QA_GENERATION_PROMPT_TEMPLATES,
    "DefaultAgenticRetrieverPrompt": SUFFICIENCY_PROMPT_TEMPLATES,
    "DefaultAgenticRerankerPrompt": FILTER_PROMPT_TEMPLATES,
}

#: Custom class -> the two genuine custom templates its two configs render.
_CUSTOM_TEMPLATES = {
    component_class: templates
    for component_class, _family, templates in _CUSTOM_PROMPT_CLASSES
}

_CUSTOM_TO_DEFAULT = {
    "CustomQueryRewritingPrompt": "DefaultQueryRewritingPrompt",
    "CustomQueryExpansionPrompt": "DefaultQueryExpansionPrompt",
    "CustomQueryDecompositionPrompt": "DefaultQueryDecompositionPrompt",
    "CustomRAGGenerationPrompt": "DefaultRAGGenerationPrompt",
    "CustomAgenticRetrieverPrompt": "DefaultAgenticRetrieverPrompt",
    "CustomAgenticRerankerPrompt": "DefaultAgenticRerankerPrompt",
}

_EXPECTED_FAMILIES = {
    "DefaultQueryRewritingPrompt": "rewriting",
    "DefaultQueryExpansionPrompt": "expansion",
    "DefaultQueryDecompositionPrompt": "decomposition",
    "DefaultRAGGenerationPrompt": "generation",
    "DefaultQARAGGenerationPrompt": "generation",
    "DefaultAgenticRetrieverPrompt": "sufficiency",
    "DefaultAgenticRerankerPrompt": "filter",
    "CustomQueryRewritingPrompt": "rewriting",
    "CustomQueryExpansionPrompt": "expansion",
    "CustomQueryDecompositionPrompt": "decomposition",
    "CustomRAGGenerationPrompt": "generation",
    "CustomAgenticRetrieverPrompt": "sufficiency",
    "CustomAgenticRerankerPrompt": "filter",
}

_EXPECTED_DEFAULT_CONFIGS = 21
_EXPECTED_CUSTOM_CONFIGS = 12
_CONFIG_IDS = [
    f"{cfg['component_class']}-{cfg['config_name']}" for cfg in PROMPT_CONFIGS
]
_CUSTOM_CONFIGS = [
    cfg for cfg in PROMPT_CONFIGS if cfg["component_class"] in _CUSTOM_TEMPLATES
]


def _load_class(name: str):
    """Import the prompt class behind *name* via the module map."""
    module_path, class_name = PROMPT_MAP[name]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _render_for(cfg: dict) -> str:
    """Instantiate a config's prompt and render it with fixed sample inputs."""
    prompt = _load_class(cfg["component_class"])(**cfg["params"])
    history_block = format_history(TRANSFORMATION_HISTORY, 2)
    return _render(prompt, cfg["component_class"], history_block)


def test_prompts_module_imports_cleanly() -> None:
    """The exported benchmark module imports and exposes its entry point."""
    module = importlib.import_module("RAG_benchmark.app.components.prompts")
    assert callable(module.run_all_prompt_benchmarks)


def test_prompt_configs_cover_full_default_language_matrix() -> None:
    """The configs include every default class × real TEMPLATES language."""
    assert len(PROMPT_CONFIGS) == _EXPECTED_DEFAULT_CONFIGS + _EXPECTED_CUSTOM_CONFIGS

    expected_defaults = {
        (component_class, language)
        for component_class, templates in _DEFAULT_TEMPLATES.items()
        for language in templates
    }
    actual_defaults = {
        (cfg["component_class"], cfg["config_name"])
        for cfg in PROMPT_CONFIGS
        if cfg["component_class"] in _DEFAULT_TEMPLATES
    }

    assert len(expected_defaults) == _EXPECTED_DEFAULT_CONFIGS
    assert actual_defaults == expected_defaults

    for cfg in PROMPT_CONFIGS:
        templates = _DEFAULT_TEMPLATES.get(cfg["component_class"])
        if templates is None:
            continue
        assert cfg["params"]["language"] == cfg["config_name"]
        assert cfg["params"]["template"] == templates[cfg["config_name"]]


def test_custom_prompt_configs_cover_two_per_category() -> None:
    """Every custom class renders two distinct genuine custom templates."""
    assert len(_CUSTOM_CONFIGS) == _EXPECTED_CUSTOM_CONFIGS
    assert {cfg["component_class"] for cfg in _CUSTOM_CONFIGS} == set(_CUSTOM_TEMPLATES)
    assert {cfg["model_name"] for cfg in _CUSTOM_CONFIGS} == {
        "rewriting",
        "expansion",
        "decomposition",
        "generation",
        "sufficiency",
        "filter",
    }

    for cfg in _CUSTOM_CONFIGS:
        templates = _CUSTOM_TEMPLATES[cfg["component_class"]]
        assert len(templates) == 2
        assert len(set(templates)) == 2
        assert cfg["params"]["template"] in templates

    for component_class, templates in _CUSTOM_TEMPLATES.items():
        config_names = {
            cfg["config_name"]
            for cfg in _CUSTOM_CONFIGS
            if cfg["component_class"] == component_class
        }
        config_templates = {
            cfg["params"]["template"]
            for cfg in _CUSTOM_CONFIGS
            if cfg["component_class"] == component_class
        }
        assert config_names == {"custom-1", "custom-2"}
        assert config_templates == set(templates)


@pytest.mark.parametrize("component_class", sorted(_EXPECTED_FAMILIES))
def test_prompt_family_covers_every_class(component_class: str) -> None:
    """Each prompt class maps to the placeholder family its templates use."""
    assert _prompt_family(component_class) == _EXPECTED_FAMILIES[component_class]


def test_prompt_config_keys_are_unique_and_named() -> None:
    """Every config key is unique and every ``model_name`` is non-empty."""
    keys = [
        (cfg["component_class"], cfg["model_name"], cfg["config_name"])
        for cfg in PROMPT_CONFIGS
    ]
    assert len(keys) == len(set(keys))
    assert all(cfg["model_name"] for cfg in PROMPT_CONFIGS)


@pytest.mark.parametrize("cfg", PROMPT_CONFIGS, ids=_CONFIG_IDS)
def test_every_prompt_config_executes(cfg: dict) -> None:
    """Runs the real executor for every config and asserts a clean pass."""
    status, exec_time, load_time, error = _execute_prompt(cfg)

    assert status == "passed", error
    assert exec_time >= 0.0
    assert load_time >= 0.0


@pytest.mark.parametrize("cfg", PROMPT_CONFIGS, ids=_CONFIG_IDS)
def test_rendered_output_passes_placeholder_assertions(cfg: dict) -> None:
    """Every config renders a string with all family tokens resolved."""
    _assert_prompt_rendered(_render_for(cfg), cfg["component_class"])


@pytest.mark.parametrize("component_class", list(_DEFAULT_TEMPLATES))
def test_default_language_variants_render_their_own_template(
    component_class: str,
) -> None:
    """Each default class renders its en/es/pt prefix and the prefixes differ."""
    configs = [
        cfg for cfg in PROMPT_CONFIGS if cfg["component_class"] == component_class
    ]
    assert {cfg["config_name"] for cfg in configs} == set(
        _DEFAULT_TEMPLATES[component_class]
    )

    prefixes: dict[str, str] = {}
    for cfg in configs:
        rendered = _render_for(cfg)
        prefix = _template_prefix(cfg["params"]["template"])

        assert prefix, f"{component_class} template starts with a placeholder"
        assert prefix in rendered
        prefixes[cfg["config_name"]] = prefix

    assert len(set(prefixes.values())) == len(prefixes)


@pytest.mark.parametrize(
    "cfg",
    _CUSTOM_CONFIGS,
    ids=[f"{cfg['component_class']}-{cfg['config_name']}" for cfg in _CUSTOM_CONFIGS],
)
def test_custom_configs_use_genuine_custom_templates(cfg: dict) -> None:
    """Custom configs render custom text that differs from the EN default."""
    template = cfg["params"]["template"]
    default_en = _DEFAULT_TEMPLATES[_CUSTOM_TO_DEFAULT[cfg["component_class"]]]["en"]

    assert template in _CUSTOM_TEMPLATES[cfg["component_class"]]
    assert template != default_en

    rendered = _render_for(cfg)
    prefix = _template_prefix(template)

    assert prefix, f"{cfg['component_class']} custom template starts with a placeholder"
    assert prefix in rendered


@pytest.mark.parametrize(
    "component_class",
    sorted(_CUSTOM_TEMPLATES),
)
def test_custom_templates_render_distinct_outputs(component_class: str) -> None:
    """The two custom configs of a class render different prompt text."""
    rendered = {
        _render_for(cfg)
        for cfg in _CUSTOM_CONFIGS
        if cfg["component_class"] == component_class
    }

    assert len(rendered) == len(_CUSTOM_TEMPLATES[component_class])


def test_sufficiency_render_resolves_every_optional_placeholder() -> None:
    """The sufficiency render substitutes the pool, round and catalog values."""
    rendered = _render_for(
        {
            "component_class": "DefaultAgenticRetrieverPrompt",
            "params": {
                "language": "en",
                "template": SUFFICIENCY_PROMPT_TEMPLATES["en"],
            },
        }
    )

    assert "Current pool size: 3 chunks." in rendered
    assert "Free pool slots left: 7." in rendered
    assert "paper.pdf" in rendered
    assert "BM25Retriever" in rendered


def test_filter_render_resolves_every_optional_placeholder() -> None:
    """The filter render substitutes the top-k cap and document summary."""
    rendered = _render_for(
        {
            "component_class": "DefaultAgenticRerankerPrompt",
            "params": {
                "language": "en",
                "template": FILTER_PROMPT_TEMPLATES["en"],
            },
        }
    )

    assert "Select at most 5 best chunks" in rendered
    assert "paper.pdf" in rendered


def test_assert_prompt_rendered_rejects_leftover_expansion_token() -> None:
    """A rendered expansion prompt that still holds ``{n}`` fails loudly."""
    rendered = f"{TRANSFORMATION_MESSAGE} produce exactly {{n}} queries"

    with pytest.raises(AssertionError, match=r"\{n\}"):
        _assert_prompt_rendered(rendered, "DefaultQueryExpansionPrompt")


def test_assert_prompt_rendered_rejects_leftover_documents_token() -> None:
    """A rendered filter prompt that still holds ``{documents.names}`` fails."""
    rendered = f"{GENERATION_SAMPLE_QUESTION} documents: {{documents.names}}"

    with pytest.raises(AssertionError, match=r"\{documents\.names\}"):
        _assert_prompt_rendered(rendered, "DefaultAgenticRerankerPrompt")


def test_assert_prompt_rendered_rejects_leftover_retriever_token() -> None:
    """A rendered sufficiency prompt that keeps its catalog token fails."""
    rendered = f"{GENERATION_SAMPLE_QUESTION} catalog: {{retriever.description}}"

    with pytest.raises(AssertionError, match=r"\{retriever\.description\}"):
        _assert_prompt_rendered(rendered, "DefaultAgenticRetrieverPrompt")


@pytest.mark.parametrize("cfg", PROMPT_CONFIGS, ids=_CONFIG_IDS)
def test_config_params_validate_against_schema(cfg: dict) -> None:
    """Params satisfy the class ``SCHEMA`` whenever it declares one."""
    cls = _load_class(cfg["component_class"])
    if cls.SCHEMA is None:
        pytest.skip(f"{cfg['component_class']} declares no SCHEMA")
    cls.SCHEMA(**cfg["params"])


def test_decomposition_optional_line_follows_n_max() -> None:
    """``n_max=None`` drops the cap sentence; a value substitutes in place."""
    prompt = DefaultQueryDecompositionPrompt(
        language="en", template=DECOMPOSITION_PROMPT_TEMPLATES["en"]
    )

    without_cap = prompt.format(input=TRANSFORMATION_MESSAGE, history="", n_max=None)
    assert "Do not produce more than" not in without_cap
    assert "{n_max}" not in without_cap

    with_cap = prompt.format(input=TRANSFORMATION_MESSAGE, history="", n_max=4)
    assert "Do not produce more than 4 sub-queries" in with_cap
    assert "{n_max}" not in with_cap
