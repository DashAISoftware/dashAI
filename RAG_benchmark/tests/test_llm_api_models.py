"""Unit tests for the current LLM and query-transformation component configs.

This replaces the former API-model tests: the remote API model modules were
removed from DashAI, so the component benchmarks now cover the registered
GGUF text-generation classes and the query transformation family. No model
weights are downloaded; only schemas, component imports and the PDF parser
are exercised.
"""

from __future__ import annotations

import importlib
import inspect
import types
from collections import defaultdict
from pathlib import Path

import pytest

from RAG_benchmark.app.benchmark_data import (
    LLM_MAP,
    PROMPT_MAP,
    TRANSFORMATION_MAP,
    discover_benchmark_paper_files,
    load_paper_texts,
)
from RAG_benchmark.app.components import llm as llm_mod
from RAG_benchmark.app.components import transformation as transformation_mod

_DUMMY_DEVICE = "CPU"

#: Expected sampling values of each LLM config profile suffix.
_EXPECTED_LLM_PROFILES = {
    "concise": {
        "max_tokens": 100,
        "temperature": 0.1,
        "frequency_penalty": 0.0,
        "context_window": 4096,
        "device": _DUMMY_DEVICE,
    },
    "creative": {
        "max_tokens": 200,
        "temperature": 0.7,
        "frequency_penalty": 0.2,
        "context_window": 4096,
    },
}

_EXPECTED_LLM_CLASSES = 10
_EXPECTED_LLM_CONFIGS = len(_EXPECTED_LLM_PROFILES) * _EXPECTED_LLM_CLASSES
_EXPECTED_TRANSFORMATION_CLASSES = 3

#: Checkpoints the transformation matrix benchmarks, keyed by config suffix.
#: ``Qwen`` component, ``model_name`` repo and context window per checkpoint.
_TRANSFORMER_VARIANTS = {
    "qwen1.5b": ("Qwen25_15BInstruct", "Qwen/Qwen2.5-1.5B-Instruct-GGUF", 2048),
    "qwen7b": ("Qwen25_7BInstruct", "Qwen/Qwen2.5-7B-Instruct-GGUF", 4096),
}

#: Transformer config names and the parameter overrides each profile applies.
_EXPECTED_TRANSFORMER_CONFIGS = {
    f"{slug}-{variant}{name_suffix}": params
    for slug, baseline, suffix, variant_params in (
        ("rewriter", {"history_window": 2}, "-no-history", {"history_window": 0}),
        (
            "expander",
            {"history_window": 2, "n_queries": 3},
            "-n5",
            {"history_window": 0, "n_queries": 5},
        ),
        (
            "decomposer",
            {"history_window": 2, "max_subqueries": 4},
            "-n2",
            {"history_window": 0, "max_subqueries": 2},
        ),
    )
    for variant in _TRANSFORMER_VARIANTS
    for name_suffix, params in (("", baseline), (suffix, variant_params))
}

_EXPECTED_TRANSFORMATION_CONFIGS = len(_EXPECTED_TRANSFORMER_CONFIGS)

_PHI4_COMPONENT = "Phi4MiniInstructModel"
_PHI4_CHECKPOINT_PARAMS = {
    "model_name": "unsloth/Phi-4-mini-instruct-GGUF",
    "quantization": "Phi-4-mini-instruct.Q8_0.gguf",
}

#: Sampling values every transformation config's nested LLM must declare,
#: excluding the per-checkpoint context window.
_EXPECTED_TRANSFORMER_LLM_PARAMS = {
    "max_tokens": 256,
    "temperature": 0.1,
    "frequency_penalty": 0.0,
    "device": _DUMMY_DEVICE,
}


def _make_logger(tmp_path: Path) -> types.SimpleNamespace:
    """Build a logger stub whose output directory lives under tmp_path."""
    return types.SimpleNamespace(output_dir=Path(tmp_path))


def _load_class(component_map: dict[str, tuple[str, str]], component: str):
    module_path, class_name = component_map[component]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _group_by_class(configs: list[dict]) -> dict[str, list[dict]]:
    """Group configs by the ``component_class`` they benchmark."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for cfg in configs:
        grouped[cfg["component_class"]].append(cfg)
    return grouped


def test_llm_configs_pair_sampling_profiles_per_class() -> None:
    """Each of the 10 GGUF classes has one concise and one creative config."""
    assert len(llm_mod.LLM_CONFIGS) == _EXPECTED_LLM_CONFIGS

    grouped = _group_by_class(llm_mod.LLM_CONFIGS)
    assert len(grouped) == _EXPECTED_LLM_CLASSES

    for component_class, configs in grouped.items():
        assert len(configs) == len(_EXPECTED_LLM_PROFILES), component_class
        suffixes = {cfg["config_name"].rsplit("-", 1)[-1] for cfg in configs}
        assert suffixes == set(_EXPECTED_LLM_PROFILES), component_class
        # A pair benchmarks the same checkpoint with different sampling only.
        assert len({cfg["model_name"] for cfg in configs}) == 1, component_class

        for cfg in configs:
            profile = cfg["config_name"].rsplit("-", 1)[-1]
            for key, expected in _EXPECTED_LLM_PROFILES[profile].items():
                assert cfg["params"][key] == expected, (component_class, key)


def test_llm_configs_validate_against_real_schemas() -> None:
    """Every LLM_CONFIGS entry passes its registered class schema."""
    assert len(llm_mod.LLM_CONFIGS) == _EXPECTED_LLM_CONFIGS

    for cfg in llm_mod.LLM_CONFIGS:
        model_class = _load_class(LLM_MAP, cfg["component_class"])
        params = dict(cfg["params"])
        params["device"] = _DUMMY_DEVICE
        unknown = sorted(set(params) - set(model_class.SCHEMA.model_fields))
        assert not unknown, f"{cfg['component_class']} has unknown params {unknown}"
        model_class.SCHEMA.model_validate(params)


def test_llm_config_keys_are_unique_and_omit_mixtral() -> None:
    """Config keys are unique and the oversized Mixtral classes stay out."""
    keys = [(cfg["component_class"], cfg["config_name"]) for cfg in llm_mod.LLM_CONFIGS]
    assert len(keys) == len(set(keys))
    assert not any("Mixtral" in cfg["component_class"] for cfg in llm_mod.LLM_CONFIGS)


def test_phi4_configs_keep_checkpoint_params() -> None:
    """Both Phi-4 configs carry the quantization the checkpoint requires."""
    phi4_configs = [
        cfg for cfg in llm_mod.LLM_CONFIGS if cfg["component_class"] == _PHI4_COMPONENT
    ]

    assert len(phi4_configs) == len(_EXPECTED_LLM_PROFILES)
    for cfg in phi4_configs:
        for key, expected in _PHI4_CHECKPOINT_PARAMS.items():
            assert cfg["params"][key] == expected


def test_transformation_configs_pair_variants_per_class() -> None:
    """Each transformer class ships a baseline and a variant per checkpoint."""
    assert len(transformation_mod.TRANSFORMATION_CONFIGS) == (
        _EXPECTED_TRANSFORMATION_CONFIGS
    )

    grouped = _group_by_class(transformation_mod.TRANSFORMATION_CONFIGS)
    assert len(grouped) == _EXPECTED_TRANSFORMATION_CLASSES
    expected_per_class = 2 * len(_TRANSFORMER_VARIANTS)
    assert all(len(configs) == expected_per_class for configs in grouped.values())

    config_names = {
        cfg["config_name"] for cfg in transformation_mod.TRANSFORMATION_CONFIGS
    }
    assert config_names == set(_EXPECTED_TRANSFORMER_CONFIGS)

    for cfg in transformation_mod.TRANSFORMATION_CONFIGS:
        expected = _EXPECTED_TRANSFORMER_CONFIGS[cfg["config_name"]]
        for key, value in expected.items():
            assert cfg["params"][key] == value, (cfg["config_name"], key)


def _variant_of(config_name: str) -> str:
    """Return the checkpoint suffix a transformer config name declares."""
    for suffix in _TRANSFORMER_VARIANTS:
        if config_name.endswith(suffix) or f"-{suffix}-" in config_name:
            return suffix
    raise AssertionError(f"config name declares no checkpoint: {config_name}")


def test_transformation_llm_params_validate_against_qwen_schema() -> None:
    """Every transformer's nested LLM params validate against its checkpoint."""
    assert len(transformation_mod.TRANSFORMATION_CONFIGS) == (
        _EXPECTED_TRANSFORMATION_CONFIGS
    )
    for cfg in transformation_mod.TRANSFORMATION_CONFIGS:
        component, _, _ = _TRANSFORMER_VARIANTS[_variant_of(cfg["config_name"])]
        qwen_class = _load_class(LLM_MAP, component)
        llm_spec = cfg["params"]["llm_model"]
        assert llm_spec["component"] == component
        params = dict(llm_spec["params"])
        params["device"] = _DUMMY_DEVICE
        qwen_class.SCHEMA.model_validate(params)


def test_transformation_configs_declare_their_checkpoint() -> None:
    """The config name, component, repo and context window agree on the model."""
    assert len(transformation_mod.TRANSFORMATION_CONFIGS) == (
        _EXPECTED_TRANSFORMATION_CONFIGS
    )
    for cfg in transformation_mod.TRANSFORMATION_CONFIGS:
        component, repo, context_window = _TRANSFORMER_VARIANTS[
            _variant_of(cfg["config_name"])
        ]
        llm_spec = cfg["params"]["llm_model"]
        assert llm_spec["component"] == component
        for key, expected in _EXPECTED_TRANSFORMER_LLM_PARAMS.items():
            assert llm_spec["params"][key] == expected, (cfg["config_name"], key)
        assert llm_spec["params"]["context_window"] == context_window
        assert cfg["model_name"] == repo


def test_transformation_prompt_params_validate_against_real_schemas() -> None:
    """Every transformer's prompt ref validates against its registered schema.

    The default transformation prompt schemas require a ``template`` field, so
    each config must pass both ``language`` and ``template`` for validation to
    succeed (runtime previously relied on a TEMPLATES fallback).
    """
    assert len(transformation_mod.TRANSFORMATION_CONFIGS) == (
        _EXPECTED_TRANSFORMATION_CONFIGS
    )
    for cfg in transformation_mod.TRANSFORMATION_CONFIGS:
        prompt_spec = cfg["params"]["prompt"]
        prompt_class = _load_class(PROMPT_MAP, prompt_spec["component"])
        prompt_class.SCHEMA.model_validate(prompt_spec["params"])


def test_transformation_configs_validate_against_component_schemas() -> None:
    """Every transformer config passes its registered class schema."""
    for cfg in transformation_mod.TRANSFORMATION_CONFIGS:
        transformer_class = _load_class(TRANSFORMATION_MAP, cfg["component_class"])
        transformer_class.SCHEMA.model_validate(dict(cfg["params"]))


def test_run_all_llm_benchmarks_rejects_include_api_models(tmp_path: Path) -> None:
    """The removed ``include_api_models`` option is no longer accepted."""
    assert (
        "include_api_models"
        not in inspect.signature(llm_mod.run_all_llm_benchmarks).parameters
    )

    with pytest.raises(TypeError):
        llm_mod.run_all_llm_benchmarks(
            _make_logger(tmp_path),
            iterations=1,
            device="CPU",
            include_api_models=True,
        )


def test_transform_prompts_render_all_placeholders() -> None:
    """Every default transformation prompt resolves its placeholders."""
    inputs = {
        "DefaultQueryRewritingPrompt": {},
        "DefaultQueryExpansionPrompt": {"n": 3},
        "DefaultQueryDecompositionPrompt": {"n_max": 4},
    }

    for component, extra in inputs.items():
        prompt_class = _load_class(PROMPT_MAP, component)
        prompt = prompt_class(language="en")
        rendered = prompt.format(
            input="A follow-up question about the retrieval stage.",
            history="user: What are the stages of a RAG pipeline?",
            **extra,
        )
        for placeholder in ("{input}", "{history}", "{n}", "{n_max}"):
            assert placeholder not in rendered


def test_resolve_llm_device_normalizes_aliases_and_rejects_unknown() -> None:
    """CPU/CUDA aliases resolve; an unknown label fails before the run."""
    assert llm_mod._resolve_llm_device("cpu") == "CPU"
    with pytest.raises(ValueError, match="Unknown device"):
        llm_mod._resolve_llm_device("cuda:0")


def test_phi4_preflight_accepts_a_cached_checkpoint(monkeypatch) -> None:
    """A cached GGUF file makes the pre-flight a no-op."""
    import huggingface_hub

    monkeypatch.setattr(
        huggingface_hub,
        "try_to_load_from_cache",
        lambda **kwargs: "C:/cache/model.gguf",
    )
    llm_mod._ensure_phi4_checkpoint(
        {"model_name": "repo/phi4", "quantization": "model.gguf"},
        download=False,
    )


def test_phi4_preflight_fails_fast_without_download(monkeypatch) -> None:
    """A missing GGUF file raises under --no-download."""
    import huggingface_hub

    monkeypatch.setattr(
        huggingface_hub, "try_to_load_from_cache", lambda **kwargs: None
    )
    with pytest.raises(RuntimeError, match="--no-download"):
        llm_mod._ensure_phi4_checkpoint(
            {"model_name": "repo/phi4", "quantization": "model.gguf"},
            download=False,
        )


def test_phi4_preflight_downloads_before_loading(monkeypatch) -> None:
    """With downloads enabled, the missing file is fetched up front."""
    import huggingface_hub

    calls = []
    monkeypatch.setattr(
        huggingface_hub, "try_to_load_from_cache", lambda **kwargs: None
    )
    monkeypatch.setattr(
        huggingface_hub,
        "hf_hub_download",
        lambda **kwargs: calls.append(kwargs) or "C:/cache/model.gguf",
    )

    llm_mod._ensure_phi4_checkpoint(
        {"model_name": "repo/phi4", "quantization": "model.gguf"},
        download=True,
    )

    assert calls == [{"repo_id": "repo/phi4", "filename": "model.gguf"}]


def test_discover_benchmark_paper_files_is_sorted() -> None:
    """PDF discovery returns sorted ``.pdf`` paths."""
    files = discover_benchmark_paper_files()

    assert files, "Expected at least one benchmark paper"
    assert all(isinstance(path, Path) for path in files)
    assert all(path.suffix.lower() == ".pdf" for path in files)
    assert files == sorted(files)


def test_load_paper_texts_returns_non_empty_text() -> None:
    """The pypdf loader extracts non-empty text from the first paper."""
    if not discover_benchmark_paper_files(max_docs=1):
        pytest.skip("No benchmark papers available")

    texts = load_paper_texts(max_docs=1)

    assert set(texts) == {0}
    assert isinstance(texts[0], str)
    assert texts[0].strip(), "Extracted paper text is empty"
