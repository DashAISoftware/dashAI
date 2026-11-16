"""Tests for the retrieval component benchmark configs and execution helpers.

No model is downloaded and no real LLM runs. The sparse families execute
against the real paper chunks through the live DashAI classes, the builder is
exercised with fake component classes that record how they were built, and the
agentic reranker retriever runs against a real BM25 child with a fake
function-calling model.
"""

from __future__ import annotations

import copy
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterator, List

import pytest

from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from DashAI.back.initial_components import get_initial_components
from DashAI.back.models.RAG.retrievers.persistence import (
    DensePersistence,
    SparsePersistence,
)
from DashAI.back.models.RAG.retrievers.ref_utils import is_component_ref
from DashAI.back.models.text_to_text_generation_model import (
    FunctionCallResult,
    TextToTextGenerationTaskModel,
)
from RAG_benchmark.app.components import retrieval as retrieval_mod
from RAG_benchmark.app.components.retrieval import (
    AGENTIC_RERANKER_RETRIEVER_COMPONENT,
    ALL_RETRIEVER_CONFIGS,
    CROSS_ENCODER_RETRIEVER_COMPONENT,
    RETRIEVER_CONFIGS,
    RETRIEVER_FAMILIES,
    _build_component,
    _build_retriever,
    _ensure_retriever_downloads,
    _execute_retriever_config,
    _prepare_chunks,
)

#: Function the fake filter model calls.
SELECT_BEST_CHUNKS = "select_best_chunks"

#: Key holding the selected 1-based candidate indices.
SELECTED_CHUNKS = "selected_chunks"

#: Query the filter test retrieves for.
FILTER_QUERY = "retrieval augmented generation"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def components() -> Dict[str, type]:
    """Return the registered component classes keyed by class name."""
    return {cls.__name__: cls for cls in get_initial_components()}


@pytest.fixture(autouse=True)
def _reset_fakes() -> Iterator[None]:
    """Keep the recorded fake instances scoped to a single test."""
    _FakeRecorder.instances.clear()
    _FakeFunctionCallingLLM.instances.clear()
    yield
    _FakeRecorder.instances.clear()
    _FakeFunctionCallingLLM.instances.clear()


def _patch_component_class(
    monkeypatch: pytest.MonkeyPatch,
    components: Dict[str, type],
    extra: Dict[str, type],
) -> None:
    """Resolve benchmark component names against the registry plus *extra*."""
    mapping = {**components, **extra}
    monkeypatch.setattr(retrieval_mod, "_component_class", mapping.__getitem__)


def _cleanup(tmpdirs: List[str]) -> None:
    """Remove every temporary directory the builder created."""
    for tmpdir in tmpdirs:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _without_iteration_keys(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *params* without the run bookkeeping keys."""
    cleaned = copy.deepcopy(params)
    cleaned.pop(retrieval_mod.ITERATION_KEY, None)
    cleaned.pop(retrieval_mod.TOTAL_ITERATIONS_KEY, None)
    return cleaned


def _iter_refs(node: Any) -> Iterator[Dict[str, Any]]:
    """Yield every ``{component, params}`` reference found in *node*."""
    if isinstance(node, dict):
        if is_component_ref(node):
            yield node
        for value in node.values():
            yield from _iter_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_refs(item)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class _FakeRecorder:
    """Component double recording the kwargs and lifecycle calls it received."""

    instances: ClassVar[List["_FakeRecorder"]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.infra: Dict[str, Any] = {}
        self.init_called = False
        self.closed = False
        _FakeRecorder.instances.append(self)

    def inject_infra(self, **kwargs: Any) -> None:
        """Record the injected runtime infrastructure."""
        self.infra = kwargs

    def init_model(self) -> None:
        """Record that the model was initialised."""
        self.init_called = True

    def retrieve(self, query: str, **kwargs: Any) -> tuple[List[Any], Dict[str, Any]]:
        """Return an empty retrieval result."""
        return [], {"name": type(self).__name__}

    def close(self) -> None:
        """Record that the component was closed."""
        self.closed = True


class _FakeChildRetriever(_FakeRecorder):
    """Fake leaf retriever."""


class _FakeCompositeRetriever(_FakeRecorder):
    """Fake composite retriever holding children and nested components."""


class _FakeDenseRetriever(_FakeRecorder):
    """Fake retriever declared through its ``embedding_model`` reference."""

    IS_DENSE = True


class _FakeEmbedding(_FakeRecorder):
    """Fake text embedding converter."""


class _FakePrompt(_FakeRecorder):
    """Fake prompt component."""


class _FakeFunctionCallingLLM(TextToTextGenerationTaskModel):
    """Fake function-calling model selecting the first two candidates."""

    SUPPORTS_FUNCTION_CALLING = True
    SCHEMA = None
    instances: ClassVar[List["_FakeFunctionCallingLLM"]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.params = dict(kwargs)
        self.function_calls: List[Dict[str, Any]] = []
        _FakeFunctionCallingLLM.instances.append(self)

    def generate(self, input: Any) -> List[str]:
        """Reject the free-form route: the filter must use the function call."""
        raise AssertionError("The reranker retriever must use generate_function_call.")

    def generate_function_call(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
    ) -> FunctionCallResult:
        """Record the call and select the two best candidates."""
        self.function_calls.append({"messages": messages, "functions": functions})
        return FunctionCallResult(SELECT_BEST_CHUNKS, {SELECTED_CHUNKS: [1, 2]})


def _filter_params() -> Dict[str, Any]:
    """Return reranker retriever params wired to the fake function-calling model."""
    return {
        "children": [retrieval_mod._bm25_ref(10)],
        "k1": 10,
        "top_k": 5,
        "prompt": retrieval_mod._prompt_ref(retrieval_mod.FILTER_PROMPT_COMPONENT),
        "llm_model": {"component": "FakeFunctionCallingLLM", "params": {}},
        "function_call_max_trials": 1,
    }


# ---------------------------------------------------------------------------
# sparse families run against the real paper chunks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cfg",
    RETRIEVER_CONFIGS,
    ids=[cfg["config_name"] for cfg in RETRIEVER_CONFIGS],
)
def test_sparse_config_executes_against_paper_chunks(cfg: Dict[str, Any]) -> None:
    """BM25 and TF-IDF configs retrieve real chunks without downloading models."""
    status, exec_time, load_time, error = _execute_retriever_config(
        copy.deepcopy(cfg), download_missing_models=False
    )

    assert status == "passed", error
    assert error == ""
    assert exec_time >= 0.0
    assert load_time >= 0.0


def test_cross_encoder_preflight_fails_fast_without_download(monkeypatch) -> None:
    """A missing cross-encoder repo raises under --no-download."""
    import huggingface_hub

    monkeypatch.setattr(
        huggingface_hub,
        "snapshot_download",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("missing")),
    )
    ref = {
        "component": CROSS_ENCODER_RETRIEVER_COMPONENT,
        "params": {
            "model_name": "cross-encoder/missing",
            "top_k": 5,
            "children": [],
        },
    }

    with pytest.raises(RuntimeError, match="--no-download"):
        _ensure_retriever_downloads(ref, False)


def test_cross_encoder_preflight_downloads_before_loading(monkeypatch) -> None:
    """With downloads enabled, the missing repo is fetched up front."""
    import huggingface_hub

    calls = []

    def fake_snapshot(**kwargs):
        calls.append(kwargs)
        if kwargs.get("local_files_only"):
            raise RuntimeError("missing")
        return "C:/cache/cross-encoder"

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot)
    ref = {
        "component": CROSS_ENCODER_RETRIEVER_COMPONENT,
        "params": {
            "model_name": "cross-encoder/missing",
            "top_k": 5,
            "children": [],
        },
    }

    _ensure_retriever_downloads(ref, True)

    assert calls[-1] == {"repo_id": "cross-encoder/missing"}


def test_build_component_rejects_unknown_nested_params() -> None:
    """An unknown nested parameter fails loudly instead of being dropped."""
    with pytest.raises(TypeError, match="unknown params"):
        _build_component(
            {"component": "BagOfWordsConverter", "params": {"nope": 1}},
            False,
        )


def test_build_component_coerces_valid_nested_params(monkeypatch) -> None:
    """Schema coercion is applied before the strict constructor runs."""
    monkeypatch.setattr(
        retrieval_mod, "ensure_component_downloaded", lambda *args, **kwargs: None
    )
    embedding = _build_component(
        {
            "component": "AllMiniLML6V2Embedding",
            "params": {
                "device": "CPU",
                "batch_size": "8",
                "normalize": 1,
                "overflow_strategy": "truncate",
            },
        },
        False,
    )

    assert embedding.batch_size == 8
    assert embedding.normalize is True


# ---------------------------------------------------------------------------
# builder
# ---------------------------------------------------------------------------


def test_build_retriever_resolves_nested_refs(
    monkeypatch: pytest.MonkeyPatch, components: Dict[str, type]
) -> None:
    """Children, prompt and LLM refs are instantiated and injected."""
    _patch_component_class(
        monkeypatch,
        components,
        {
            "FakeCompositeRetriever": _FakeCompositeRetriever,
            "FakeChildRetriever": _FakeChildRetriever,
            "FakePrompt": _FakePrompt,
            "FakeFunctionCallingLLM": _FakeFunctionCallingLLM,
        },
    )
    ref = {
        "component": "FakeCompositeRetriever",
        "params": {
            "children": [{"component": "FakeChildRetriever", "params": {"top_k": 3}}],
            "prompt": {"component": "FakePrompt", "params": {"language": "en"}},
            "llm_model": {
                "component": "FakeFunctionCallingLLM",
                "params": {"max_tokens": 7},
            },
        },
    }
    chunks = _prepare_chunks()
    tmpdirs: List[str] = []
    try:
        retriever = _build_retriever(ref, chunks, tmpdirs, False)
    finally:
        _cleanup(tmpdirs)

    assert isinstance(retriever, _FakeCompositeRetriever)
    child = retriever.kwargs["children"][0]
    assert isinstance(child, _FakeChildRetriever)
    assert child.kwargs == {"top_k": 3}
    assert isinstance(retriever.kwargs["prompt"], _FakePrompt)
    assert retriever.kwargs["prompt"].kwargs == {"language": "en"}
    llm = retriever.kwargs["llm_model"]
    assert isinstance(llm, _FakeFunctionCallingLLM)
    assert llm.params == {"max_tokens": 7}
    assert retriever.infra["chunks"] is chunks
    assert isinstance(retriever.infra["persistence"], SparsePersistence)
    assert retriever.infra["persistence"].model_dir is None
    assert isinstance(child.infra["persistence"], SparsePersistence)
    assert retriever.init_called
    assert child.init_called
    assert tmpdirs


def test_build_retriever_wires_dense_persistence_per_document(
    monkeypatch: pytest.MonkeyPatch, components: Dict[str, type]
) -> None:
    """A retriever declaring ``embedding_model`` gets one matrix dir per doc."""
    _patch_component_class(
        monkeypatch,
        components,
        {"FakeDenseRetriever": _FakeDenseRetriever, "FakeEmbedding": _FakeEmbedding},
    )
    ref = {
        "component": "FakeDenseRetriever",
        "params": {
            "embedding_model": {
                "component": "FakeEmbedding",
                "params": {"device": "CPU"},
            },
            "top_k": 2,
        },
    }
    chunks = _prepare_chunks()
    tmpdirs: List[str] = []
    try:
        retriever = _build_retriever(ref, chunks, tmpdirs, False)
        persistence = retriever.infra["persistence"]
        assert isinstance(persistence, DensePersistence)
        assert persistence.embedding_model_id == 0
        assert set(persistence.matrix_dirs) == set(chunks)
        assert all(Path(path).is_dir() for path in persistence.matrix_dirs.values())
        embedding = retriever.kwargs["embedding_model"]
        assert isinstance(embedding, _FakeEmbedding)
        assert embedding.kwargs == {"device": "CPU"}
        assert retriever.init_called
    finally:
        _cleanup(tmpdirs)


# ---------------------------------------------------------------------------
# agentic reranker retriever over a real child
# ---------------------------------------------------------------------------


def test_agentic_reranker_retriever_selects_through_the_function_call(
    monkeypatch: pytest.MonkeyPatch, components: Dict[str, type]
) -> None:
    """The real reranker retriever uses the fake LLM and reports ``llm_used``."""
    _patch_component_class(
        monkeypatch,
        components,
        {"FakeFunctionCallingLLM": _FakeFunctionCallingLLM},
    )
    chunks = _prepare_chunks()
    tmpdirs: List[str] = []
    retriever = None
    try:
        retriever = _build_retriever(
            {
                "component": AGENTIC_RERANKER_RETRIEVER_COMPONENT,
                "params": copy.deepcopy(_filter_params()),
            },
            chunks,
            tmpdirs,
            False,
        )
        results, trace = retriever.retrieve(FILTER_QUERY)
    finally:
        if retriever is not None:
            retriever.close()
        _cleanup(tmpdirs)

    assert results, "The reranker retriever returned no chunks"
    assert trace["selection"]["llm_used"] is True
    assert trace["children"][0]["name"] == "BM25Retriever"
    llm = _FakeFunctionCallingLLM.instances[0]
    assert llm.function_calls
    assert llm.function_calls[0]["functions"][0]["name"] == SELECT_BEST_CHUNKS


def test_execute_retriever_config_accepts_the_llm_trace(
    monkeypatch: pytest.MonkeyPatch, components: Dict[str, type]
) -> None:
    """The shared executor passes once the LLM trace evidence is present."""
    _patch_component_class(
        monkeypatch,
        components,
        {"FakeFunctionCallingLLM": _FakeFunctionCallingLLM},
    )
    cfg = {
        "component_class": AGENTIC_RERANKER_RETRIEVER_COMPONENT,
        "model_name": "fake-qwen",
        "config_name": "fake_llm",
        "params": _filter_params(),
    }

    status, exec_time, load_time, error = _execute_retriever_config(
        cfg, download_missing_models=False
    )

    assert status == "passed", error
    assert error == ""
    assert exec_time > 0.0
    assert load_time > 0.0


# ---------------------------------------------------------------------------
# config metadata and schema validation
# ---------------------------------------------------------------------------


def test_config_keys_are_unique() -> None:
    """``(component_class, model_name, config_name)`` identifies one config."""
    keys = [
        (cfg["component_class"], cfg["model_name"], cfg["config_name"])
        for cfg in ALL_RETRIEVER_CONFIGS
    ]

    assert len(keys) == len(set(keys))


def test_every_retriever_class_has_at_least_two_configs() -> None:
    """Each retrieval family contributes two comparable configurations."""
    counts = Counter(cfg["component_class"] for cfg in ALL_RETRIEVER_CONFIGS)

    for component, count in counts.items():
        assert count >= 2, f"{component} declares {count} config(s)"


def test_every_registered_retriever_is_benchmarked(
    components: Dict[str, type],
) -> None:
    """Every concrete retriever in the registry has a benchmark config."""
    from DashAI.back.models.RAG.retrievers.base_retriever import BaseRetriever

    registered = {
        name
        for name, component in components.items()
        if isinstance(component, type)
        and issubclass(component, BaseRetriever)
        and component is not BaseRetriever
    }
    configured = {cfg["component_class"] for cfg in ALL_RETRIEVER_CONFIGS}

    assert configured == registered


def test_family_names_match_the_report_groups() -> None:
    """The component_type groups the logger records stay stable."""
    assert [name for name, _ in RETRIEVER_FAMILIES] == [
        "sparse_retriever",
        "dense_retriever",
        "composite_retriever",
        "cross_encoder_retriever",
        "sequential_retriever",
        "parallel_retriever",
        "llm_retriever",
    ]


def test_every_config_component_is_registered(components: Dict[str, type]) -> None:
    """Every configured class is part of ``get_initial_components()``."""
    for cfg in ALL_RETRIEVER_CONFIGS:
        assert cfg["component_class"] in components


def test_llm_retrievers_use_qwen_7b_with_eight_function_call_trials() -> None:
    """Every LLM retriever calls Qwen 2.5 7B and retries the call up to 8 times."""
    assert retrieval_mod.FUNCTION_CALL_TRIALS == 8
    assert retrieval_mod.FUNCTION_CALLING_LLM_COMPONENT == "Qwen25_7BInstruct"
    assert (
        retrieval_mod.FUNCTION_CALLING_LLM_MODEL_NAME == "Qwen/Qwen2.5-7B-Instruct-GGUF"
    )

    llm_configs = [
        cfg
        for cfg in ALL_RETRIEVER_CONFIGS
        if cfg["component_class"] in retrieval_mod.LLM_RETRIEVER_COMPONENTS
    ]
    assert len(llm_configs) == len(retrieval_mod.LLM_RETRIEVER_CONFIGS)

    for cfg in llm_configs:
        assert cfg["model_name"] == retrieval_mod.FUNCTION_CALLING_LLM_MODEL_NAME
        assert cfg["params"]["llm_model"]["component"] == "Qwen25_7BInstruct"
        assert cfg["params"]["function_call_max_trials"] == 8


def test_top_level_params_validate_against_the_component_schema(
    components: Dict[str, type],
) -> None:
    """Each config's params pass its own component schema."""
    for cfg in ALL_RETRIEVER_CONFIGS:
        component_class = components[cfg["component_class"]]
        schema = getattr(component_class, "SCHEMA", None)
        assert schema is not None, f"{cfg['component_class']} declares no SCHEMA"
        params = _without_iteration_keys(cfg["params"])
        unknown = sorted(set(params) - set(schema.model_fields))
        assert not unknown, (
            f"{cfg['component_class']} declares unknown params {unknown}"
        )
        schema.model_validate(params)


def test_nested_component_refs_validate_against_their_schemas(
    components: Dict[str, type],
) -> None:
    """Every nested ref passes its schema once the form placeholders are seeded.

    The prompt schemas require a ``template`` the backend resolves from the
    ``language`` at construction time, so the benchmark form values are seeded
    with the placeholders the frontend also sends.
    """
    for cfg in ALL_RETRIEVER_CONFIGS:
        for ref in _iter_refs(cfg["params"]):
            component_class = components[ref["component"]]
            schema = getattr(component_class, "SCHEMA", None)
            if schema is None:
                continue
            raw = _without_iteration_keys(ref["params"])
            unknown = sorted(set(raw) - set(schema.model_fields))
            assert not unknown, f"{ref['component']} declares unknown params {unknown}"
            params = {
                **schema_placeholder_defaults(component_class),
                **raw,
            }
            schema.model_validate(params)
