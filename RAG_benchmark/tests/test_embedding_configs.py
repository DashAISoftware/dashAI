"""Tests for the dynamic embedding benchmark configs.

The configs are generated from ``TEXT_EMBEDDING_CONVERTERS``, so the suite
asserts total coverage instead of a hand-maintained list. No model is
downloaded: the configs are only inspected, and the executor is exercised with
a fake converter.
"""

from __future__ import annotations

import copy
import json
import os
from collections import Counter
from typing import Any, ClassVar, Dict, Iterator, List

import numpy as np
import pytest

from DashAI.back.converters.hugging_face.text_embedding import (
    TEXT_EMBEDDING_CONVERTERS,
)
from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from DashAI.back.initial_components import get_initial_components
from RAG_benchmark.app.components import embedding as embedding_mod
from RAG_benchmark.app.components.embedding import (
    EMBEDDING_CONFIGS,
    _execute_embedding,
)

#: Config names the generator must produce for every converter.
CONFIG_SUFFIXES = ("default", "alternate")

#: Width of the vectors the fake converter returns.
FAKE_DIMENSIONS = 4

#: Converter that calls a remote embedding API instead of loading weights.
OPENAI_EMBEDDING_COMPONENT = "OpenAIEmbedding"

#: Converter that runs the quantized e5-mistral GGUF checkpoint.
E5_MISTRAL_GGUF_COMPONENT = "E5MistralGGUFEmbedding"

#: Environment variable the remote converter reads its credential from.
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

#: Parameter the remote converter takes its credential through.
API_KEY_PARAM = "api_key"

#: Parameter that selects the remote embedding model.
MODEL_NAME_PARAM = "model_name"

#: Credential the environment injection test installs.
FAKE_API_KEY = "sk-test-not-a-real-key"


class _FakeEmbedding:
    """Converter double that records the lifecycle calls it received."""

    MODEL_NAME = "fake/embedding"
    SCHEMA = None
    instances: ClassVar[List["_FakeEmbedding"]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.normalize = bool(kwargs.get("normalize", True))
        self.loaded = 0
        self.encoded: List[List[str]] = []
        self.roles: List[str] = []
        _FakeEmbedding.instances.append(self)

    def pretrained(self) -> None:
        """Record that the weights were loaded."""
        self.loaded += 1

    def encode(self, texts: List[str], role: str = "passage") -> np.ndarray:
        """Return unit-norm vectors, mimicking a normalized converter."""
        self.encoded.append(list(texts))
        self.roles.append(role)
        vectors = np.ones((len(texts), FAKE_DIMENSIONS), dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


@pytest.fixture(scope="module")
def components() -> Dict[str, type]:
    """Return the registered component classes keyed by class name."""
    return {cls.__name__: cls for cls in get_initial_components()}


@pytest.fixture(autouse=True)
def _reset_fakes() -> Iterator[None]:
    """Keep the recorded fake instances scoped to a single test."""
    _FakeEmbedding.instances.clear()
    yield
    _FakeEmbedding.instances.clear()


def test_every_registered_converter_has_exactly_two_configs() -> None:
    """The generator covers ``TEXT_EMBEDDING_CONVERTERS`` completely."""
    counts = Counter(cfg["component_class"] for cfg in EMBEDDING_CONFIGS)

    assert set(counts) == {cls.__name__ for cls in TEXT_EMBEDDING_CONVERTERS}
    for component, count in counts.items():
        assert count == len(CONFIG_SUFFIXES), (
            f"{component} declares {count} config(s), expected {len(CONFIG_SUFFIXES)}"
        )


def test_config_keys_are_unique() -> None:
    """``(component_class, model_name, config_name)`` identifies one config."""
    keys = [
        (cfg["component_class"], cfg["model_name"], cfg["config_name"])
        for cfg in EMBEDDING_CONFIGS
    ]

    assert len(keys) == len(set(keys))


def test_config_names_and_model_names_follow_the_converter() -> None:
    """Each config is named after its converter and repeats its checkpoint."""
    by_class = {cls.__name__: cls for cls in TEXT_EMBEDDING_CONVERTERS}

    for cfg in EMBEDDING_CONFIGS:
        converter = by_class[cfg["component_class"]]
        suffix = cfg["config_name"].removeprefix(f"{cfg['component_class']}-")
        assert suffix in CONFIG_SUFFIXES
        assert cfg["model_name"] == converter.MODEL_NAME


def test_pooling_strategy_only_appears_when_the_converter_exposes_it() -> None:
    """The pooling option is added exactly for converters that declare it."""
    by_class = {cls.__name__: cls for cls in TEXT_EMBEDDING_CONVERTERS}

    for cfg in EMBEDDING_CONFIGS:
        converter = by_class[cfg["component_class"]]
        exposes_pooling = bool(getattr(converter, "POOLING_STRATEGIES", None))
        assert ("pooling_strategy" in cfg["params"]) is exposes_pooling


def test_new_converters_take_part_in_the_matrix() -> None:
    """The restored remote and GGUF converters are covered by the generator."""
    covered = {cls.__name__ for cls in TEXT_EMBEDDING_CONVERTERS}

    assert {OPENAI_EMBEDDING_COMPONENT, E5_MISTRAL_GGUF_COMPONENT} <= covered


def test_openai_configs_log_an_empty_key_and_a_configurable_model() -> None:
    """The remote configs log the empty placeholder key, never an environment key."""
    by_class = {cls.__name__: cls for cls in TEXT_EMBEDDING_CONVERTERS}
    converter = by_class[OPENAI_EMBEDDING_COMPONENT]
    configs = [
        cfg for cfg in EMBEDDING_CONFIGS if cfg["component_class"] == converter.__name__
    ]

    assert {cfg["config_name"] for cfg in configs} == {
        f"{converter.__name__}-{suffix}" for suffix in CONFIG_SUFFIXES
    }
    expected_model = schema_placeholder_defaults(converter)[MODEL_NAME_PARAM]
    assert expected_model, "The OpenAI config must declare an embedding model"
    for cfg in configs:
        assert cfg["params"][API_KEY_PARAM] == ""
        assert cfg["params"][MODEL_NAME_PARAM] == expected_model

    secret = os.environ.get(OPENAI_API_KEY_ENV)
    if secret:
        assert secret not in json.dumps(EMBEDDING_CONFIGS), (
            "The environment API key leaked into the logged benchmark configs"
        )


def test_every_config_component_is_registered(components: Dict[str, type]) -> None:
    """Every configured class is part of ``get_initial_components()``."""
    for cfg in EMBEDDING_CONFIGS:
        assert cfg["component_class"] in components


def test_embedding_configs_validate_against_their_schemas(
    components: Dict[str, type],
) -> None:
    """Each config's params pass the converter schema."""
    for cfg in EMBEDDING_CONFIGS:
        schema = components[cfg["component_class"]].SCHEMA
        assert schema is not None, f"{cfg['component_class']} declares no SCHEMA"
        params = copy.deepcopy(cfg["params"])
        params.pop(embedding_mod.ITERATION_KEY, None)
        params.pop(embedding_mod.TOTAL_ITERATIONS_KEY, None)
        unknown = sorted(set(params) - set(schema.model_fields))
        assert not unknown, (
            f"{cfg['component_class']} declares unknown params {unknown}"
        )
        schema.model_validate(params)


def test_execute_embedding_loads_before_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The executor measures the weights load and encodes two passages."""
    monkeypatch.setattr(embedding_mod, "_component_class", lambda name: _FakeEmbedding)
    cfg = {
        "component_class": "FakeEmbedding",
        "model_name": "fake/embedding",
        "config_name": "fake",
        "params": {
            "device": "CPU",
            "batch_size": 32,
            "normalize": True,
            "overflow_strategy": "truncate",
        },
    }

    status, exec_time, load_time, error = _execute_embedding(
        cfg, download_missing_models=False
    )

    assert status == "passed", error
    assert error == ""
    assert exec_time > 0.0
    assert load_time > 0.0
    converter = _FakeEmbedding.instances[0]
    assert converter.loaded == 1
    assert len(converter.encoded) == 1
    assert len(converter.encoded[0]) == 2
    assert converter.roles == ["passage"]


def test_execute_embedding_uses_prepared_passages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner parses the PDF once and passes the spans to every executor."""
    monkeypatch.setattr(embedding_mod, "_component_class", lambda name: _FakeEmbedding)
    monkeypatch.setattr(
        embedding_mod,
        "load_paper_texts",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("PDF parsed again")),
    )
    passages = ["first span", "second span"]

    status, _, _, error = _execute_embedding(
        {
            "component_class": "FakeEmbedding",
            "model_name": "fake/embedding",
            "config_name": "fake",
            "params": {"device": "CPU", "batch_size": 32, "normalize": True},
        },
        download_missing_models=False,
        passages=passages,
    )

    assert status == "passed", error
    assert _FakeEmbedding.instances[0].encoded == [passages]


def test_execute_embedding_rejects_non_finite_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A converter returning non-finite values fails the benchmark."""

    class _NonFiniteEmbedding(_FakeEmbedding):
        """Converter double whose vectors contain ``nan``."""

        def encode(self, texts: List[str], role: str = "passage") -> np.ndarray:
            vectors = np.full((len(texts), FAKE_DIMENSIONS), np.nan, dtype=np.float32)
            return vectors

    monkeypatch.setattr(
        embedding_mod, "_component_class", lambda name: _NonFiniteEmbedding
    )

    with pytest.raises(AssertionError):
        _execute_embedding(
            {
                "component_class": "NonFiniteEmbedding",
                "model_name": "fake/embedding",
                "config_name": "fake",
                "params": {"device": "CPU", "batch_size": 32},
            },
            download_missing_models=False,
        )


def _openai_cfg() -> Dict[str, Any]:
    """Return a remote-converter config carrying the empty placeholder key."""
    return {
        "component_class": "FakeOpenAIEmbedding",
        "model_name": "fake/openai-embedding",
        "config_name": "fake-openai",
        "params": {
            "device": "CPU",
            "batch_size": 32,
            "normalize": True,
            "overflow_strategy": "truncate",
            MODEL_NAME_PARAM: "text-embedding-ada-002",
            API_KEY_PARAM: "",
        },
    }


def test_execute_embedding_allows_environment_api_key_without_copying_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The environment credential is available but never copied into params."""

    class _FakeOpenAIEmbedding(_FakeEmbedding):
        """Converter double for a remote, API-key-bearing embedding model."""

        REQUIRES_API_KEY = True

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.saw_environment_key = bool(os.environ.get(OPENAI_API_KEY_ENV))

    monkeypatch.setenv(OPENAI_API_KEY_ENV, FAKE_API_KEY)
    monkeypatch.setattr(
        embedding_mod, "_component_class", lambda name: _FakeOpenAIEmbedding
    )
    cfg = _openai_cfg()
    logged_params = copy.deepcopy(cfg["params"])

    status, _, _, error = _execute_embedding(
        cfg, download_missing_models=False, passages=["first span", "second span"]
    )

    assert status == "passed", error
    converter = _FakeOpenAIEmbedding.instances[0]
    assert not converter.kwargs.get(API_KEY_PARAM)
    assert FAKE_API_KEY not in str(converter.kwargs)
    assert converter.saw_environment_key
    assert cfg["params"] == logged_params, "The logged config was mutated"


def test_execute_embedding_requires_an_api_key_for_remote_converters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A remote converter without a key fails before any artifact is touched."""

    class _FakeOpenAIEmbedding(_FakeEmbedding):
        """Converter double that declares it needs an API key."""

        REQUIRES_API_KEY = True

    monkeypatch.delenv(OPENAI_API_KEY_ENV, raising=False)
    monkeypatch.setattr(
        embedding_mod, "_component_class", lambda name: _FakeOpenAIEmbedding
    )

    with pytest.raises(RuntimeError, match=OPENAI_API_KEY_ENV):
        _execute_embedding(
            _openai_cfg(),
            download_missing_models=False,
            passages=["first span", "second span"],
        )

    assert not _FakeOpenAIEmbedding.instances
