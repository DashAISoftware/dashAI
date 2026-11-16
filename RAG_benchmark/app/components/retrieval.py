"""Retrieval component benchmarks built from real component references.

Every config is a real ``{component, params}`` recipe: nested embedding models,
vectorizers, prompts and evaluation LLMs are resolved through the live
component registry, so the benchmark instantiates the same classes the app
builds instead of re-implementing their wiring. Class names are resolved once
through ``get_initial_components()``; no module path is hardcoded here.
"""

from __future__ import annotations

import copy
import functools
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator, Optional

from DashAI.back.models.RAG.prompts.evaluation.default_agentic_reranker_prompt import (
    TEMPLATES as FILTER_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.evaluation.default_agentic_retriever_prompt import (  # noqa: E501
    TEMPLATES as SUFFICIENCY_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.retrievers.ref_utils import is_component_ref
from RAG_benchmark.app.benchmark_data import load_paper_texts
from RAG_benchmark.app.benchmark_utils import (
    Timer,
    ensure_component_downloaded,
    load_last_run_statuses,
    run_configs,
)
from RAG_benchmark.app.components.llm import _resolve_llm_device

# ═══════════════════════════════════════════════════════════════════════
#  Component names the configs reference
# ═══════════════════════════════════════════════════════════════════════

BM25_RETRIEVER_COMPONENT = "BM25Retriever"
TFIDF_RETRIEVER_COMPONENT = "TFIDFRetriever"
DENSE_RETRIEVER_COMPONENT = "DenseEmbeddingRetriever"
MMR_RETRIEVER_COMPONENT = "MMRRerankerRetriever"
CROSS_ENCODER_RETRIEVER_COMPONENT = "SentenceTransformerCrossEncoderRetriever"
SEQUENTIAL_RETRIEVER_COMPONENT = "SequentialRetriever"
PARALLEL_RETRIEVER_COMPONENT = "ParallelRetriever"
AGENTIC_RERANKER_RETRIEVER_COMPONENT = "AgenticRerankerRetriever"
LLM_DEPTH_RETRIEVER_COMPONENT = "AgenticSingleRetriever"
LLM_ENSEMBLE_RETRIEVER_COMPONENT = "AgenticEnsembleRetriever"

BAG_OF_WORDS_COMPONENT = "BagOfWordsConverter"
TFIDF_CONVERTER_COMPONENT = "TFIDFConverter"
DENSE_EMBEDDING_COMPONENT = "AllMiniLML6V2Embedding"
FUNCTION_CALLING_LLM_COMPONENT = "Qwen25_7BInstruct"
SUFFICIENCY_PROMPT_COMPONENT = "DefaultAgenticRetrieverPrompt"
FILTER_PROMPT_COMPONENT = "DefaultAgenticRerankerPrompt"

#: Retrievers whose traces must prove the language model was consulted.
LLM_RETRIEVER_COMPONENTS = frozenset(
    {
        AGENTIC_RERANKER_RETRIEVER_COMPONENT,
        LLM_DEPTH_RETRIEVER_COMPONENT,
        LLM_ENSEMBLE_RETRIEVER_COMPONENT,
    }
)

# ═══════════════════════════════════════════════════════════════════════
#  Config and parameter keys
# ═══════════════════════════════════════════════════════════════════════

#: Nested retriever references of a composite retriever.
CHILDREN_KEY = "children"

#: Nested embedding model reference of a dense retriever.
EMBEDDING_MODEL_KEY = "embedding_model"

#: Nested evaluation prompt reference of an LLM retriever.
PROMPT_KEY = "prompt"

#: Nested evaluation LLM reference of an LLM retriever.
LLM_MODEL_KEY = "llm_model"

#: Device parameter shared by the LLM schemas.
DEVICE_KEY = "device"

#: Run bookkeeping keys injected per iteration and stripped before building.
ITERATION_KEY = "iteration"
TOTAL_ITERATIONS_KEY = "total_iterations"

#: Trace keys the LLM retrievers must report.
SELECTION_TRACE_KEY = "selection"
ROUNDS_TRACE_KEY = "rounds"
LLM_USED_TRACE_KEY = "llm_used"

# ═══════════════════════════════════════════════════════════════════════
#  Shared values
# ═══════════════════════════════════════════════════════════════════════

#: Query used when a config does not override it.
DEFAULT_QUERY = "retrieval augmented generation"

#: Language every benchmark prompt is rendered in.
PROMPT_LANGUAGE = "en"

#: Display label of the sparse retrieval techniques.
BM25_MODEL_NAME = "BM25"
TFIDF_MODEL_NAME = "TFIDF"
MMR_MODEL_NAME = "MMR"
HYBRID_MODEL_NAME = "BM25_TFIDF"

#: Display label of the dense checkpoint every dense config embeds with.
DENSE_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

#: Display label of the checkpoint the LLM retrievers call.
FUNCTION_CALLING_LLM_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct-GGUF"

#: Sampling parameters of the LLM retrievers' function-calling model. The
#: device is overwritten with the resolved run device on every iteration.
FUNCTION_CALLING_LLM_PARAMS: dict[str, Any] = {
    "max_tokens": 300,
    "temperature": 0.1,
    "frequency_penalty": 0.1,
    "context_window": 10000,
    DEVICE_KEY: "CPU",
}

#: Number of LLM evaluation attempts, the first call included. A 7B model
#: occasionally emits a malformed function call, so the retrievers get a larger
#: budget than the previous 1.5B checkpoint needed.
FUNCTION_CALL_TRIALS = 8

#: Complete bag-of-words parameters (the schema fills nothing in).
BAG_OF_WORDS_PARAMS: dict[str, Any] = {
    "max_features": None,
    "lowercase": True,
    "strip_accents": None,
    "analyzer": "word",
    "stop_words": None,
    "custom_stop_words": None,
    "lower_bound_ngrams": 1,
    "upper_bound_ngrams": 1,
    "min_df": 0.0,
    "max_df": 1.0,
}

#: Complete TF-IDF vectorizer parameters: the shared options plus the weights.
TFIDF_VECTORIZER_PARAMS: dict[str, Any] = {
    **BAG_OF_WORDS_PARAMS,
    "max_features": 1000,
    "norm": "l2",
    "use_idf": True,
    "smooth_idf": True,
    "sublinear_tf": False,
}

#: Complete text embedding parameters (the schema fills nothing in).
DENSE_EMBEDDING_PARAMS: dict[str, Any] = {
    DEVICE_KEY: "CPU",
    "batch_size": 32,
    "normalize": True,
    "overflow_strategy": "truncate",
}


# ═══════════════════════════════════════════════════════════════════════
#  Reference builders
# ═══════════════════════════════════════════════════════════════════════


def _ref(component: str, params: dict[str, Any]) -> dict[str, Any]:
    """Return a fresh ``{component, params}`` reference."""
    return {"component": component, "params": params}


def _bag_of_words_ref(**overrides: Any) -> dict[str, Any]:
    """Return a bag-of-words vectorizer reference."""
    return _ref(BAG_OF_WORDS_COMPONENT, {**BAG_OF_WORDS_PARAMS, **overrides})


def _tfidf_vectorizer_ref(**overrides: Any) -> dict[str, Any]:
    """Return a TF-IDF vectorizer reference."""
    return _ref(TFIDF_CONVERTER_COMPONENT, {**TFIDF_VECTORIZER_PARAMS, **overrides})


def _dense_embedding_ref(**overrides: Any) -> dict[str, Any]:
    """Return the shared dense embedding converter reference."""
    return _ref(DENSE_EMBEDDING_COMPONENT, {**DENSE_EMBEDDING_PARAMS, **overrides})


#: Default evaluation prompt templates keyed by component name.
_PROMPT_TEMPLATES: dict[str, dict[str, str]] = {
    SUFFICIENCY_PROMPT_COMPONENT: SUFFICIENCY_PROMPT_TEMPLATES,
    FILTER_PROMPT_COMPONENT: FILTER_PROMPT_TEMPLATES,
}


def _prompt_ref(component: str) -> dict[str, Any]:
    """Return an evaluation prompt reference in the benchmark language."""
    templates = _PROMPT_TEMPLATES[component]
    return _ref(
        component,
        {"language": PROMPT_LANGUAGE, "template": templates[PROMPT_LANGUAGE]},
    )


def _function_calling_llm_ref() -> dict[str, Any]:
    """Return a fresh reference to the shared function-calling LLM."""
    return _ref(FUNCTION_CALLING_LLM_COMPONENT, dict(FUNCTION_CALLING_LLM_PARAMS))


def _bm25_ref(
    top_k: int,
    *,
    k1: float = 1.5,
    b: float = 0.75,
    delta: float = 0.0,
    similarity_function: str = "cosine",
    vectorizer: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return a BM25 retriever reference."""
    return _ref(
        BM25_RETRIEVER_COMPONENT,
        {
            "vectorizer": (_bag_of_words_ref() if vectorizer is None else vectorizer),
            "k1": k1,
            "b": b,
            "delta": delta,
            "similarity_function": similarity_function,
            "top_k": top_k,
        },
    )


def _tfidf_retriever_ref(
    top_k: int,
    *,
    similarity_function: str = "cosine",
    vectorizer: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Return a TF-IDF retriever reference."""
    return _ref(
        TFIDF_RETRIEVER_COMPONENT,
        {
            "vectorizer": (
                _tfidf_vectorizer_ref() if vectorizer is None else vectorizer
            ),
            "similarity_function": similarity_function,
            "top_k": top_k,
        },
    )


def _dense_ref(top_k: int, *, similarity_metric: str = "cosine") -> dict[str, Any]:
    """Return a dense embedding retriever reference."""
    return _ref(
        DENSE_RETRIEVER_COMPONENT,
        {
            EMBEDDING_MODEL_KEY: _dense_embedding_ref(),
            "similarity_metric": similarity_metric,
            "top_k": top_k,
        },
    )


def _children_params(children: list[dict[str, Any]], **params: Any) -> dict[str, Any]:
    """Return composite parameters holding the nested child references."""
    return {CHILDREN_KEY: children, **params}


def _config(
    component_class: str,
    model_name: str,
    config_name: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Return one benchmark config in the shape ``run_configs`` expects."""
    return {
        "component_class": component_class,
        "model_name": model_name,
        "config_name": config_name,
        "params": params,
    }


def _bm25_config(config_name: str, ref: dict[str, Any]) -> dict[str, Any]:
    """Return a BM25 benchmark config."""
    return _config(
        BM25_RETRIEVER_COMPONENT, BM25_MODEL_NAME, config_name, ref["params"]
    )


def _tfidf_config(config_name: str, ref: dict[str, Any]) -> dict[str, Any]:
    """Return a TF-IDF benchmark config."""
    return _config(
        TFIDF_RETRIEVER_COMPONENT, TFIDF_MODEL_NAME, config_name, ref["params"]
    )


def _dense_config(config_name: str, ref: dict[str, Any]) -> dict[str, Any]:
    """Return a dense retriever benchmark config."""
    return _config(
        DENSE_RETRIEVER_COMPONENT, DENSE_MODEL_NAME, config_name, ref["params"]
    )


def _cross_encoder_config(
    config_name: str, model_name: str, top_k: int, child: dict[str, Any]
) -> dict[str, Any]:
    """Return a cross-encoder retriever benchmark config."""
    return _config(
        CROSS_ENCODER_RETRIEVER_COMPONENT,
        model_name,
        config_name,
        _children_params([child], model_name=model_name, top_k=top_k),
    )


def _llm_evaluated_params(
    children: list[dict[str, Any]],
    *,
    max_chunks: int,
    max_iters: int,
) -> dict[str, Any]:
    """Return the depth/ensemble retriever parameters."""
    return {
        CHILDREN_KEY: children,
        "max_chunks": max_chunks,
        "max_iters": max_iters,
        "function_call_max_trials": FUNCTION_CALL_TRIALS,
        PROMPT_KEY: _prompt_ref(SUFFICIENCY_PROMPT_COMPONENT),
        LLM_MODEL_KEY: _function_calling_llm_ref(),
    }


def _llm_filter_params(child: dict[str, Any], *, k1: int, top_k: int) -> dict[str, Any]:
    """Return the agentic reranker retriever parameters."""
    return {
        CHILDREN_KEY: [child],
        "k1": k1,
        "top_k": top_k,
        "function_call_max_trials": FUNCTION_CALL_TRIALS,
        PROMPT_KEY: _prompt_ref(FILTER_PROMPT_COMPONENT),
        LLM_MODEL_KEY: _function_calling_llm_ref(),
    }


# ═══════════════════════════════════════════════════════════════════════
#  Configs
# ═══════════════════════════════════════════════════════════════════════

#: Sparse retrievers: BM25 and TF-IDF over the same bag-of-words family.
RETRIEVER_CONFIGS = [
    _bm25_config("default", _bm25_ref(5)),
    _bm25_config(
        "custom",
        _bm25_ref(
            10,
            k1=2.0,
            b=0.5,
            delta=0.5,
            similarity_function="euclidean",
            vectorizer=_bag_of_words_ref(max_features=2000),
        ),
    ),
    _tfidf_config("default", _tfidf_retriever_ref(5)),
    _tfidf_config(
        "custom",
        _tfidf_retriever_ref(
            10,
            vectorizer=_tfidf_vectorizer_ref(
                max_features=2000, stop_words="english", sublinear_tf=True
            ),
        ),
    ),
]

#: Dense retriever over the small English Sentence Transformers checkpoint.
DENSE_RETRIEVER_CONFIGS = [
    _dense_config("cosine_k5", _dense_ref(5)),
    _dense_config("euclidean_k10", _dense_ref(10, similarity_metric="euclidean")),
]

#: MMR re-ranking over a wider dense candidate set.
COMPOSITE_RETRIEVER_CONFIGS = [
    _config(
        MMR_RETRIEVER_COMPONENT,
        MMR_MODEL_NAME,
        "lambda05_factor3",
        _children_params([_dense_ref(15)], mmr_lambda=0.5, top_k=5),
    ),
    _config(
        MMR_RETRIEVER_COMPONENT,
        MMR_MODEL_NAME,
        "lambda07_factor2",
        _children_params([_dense_ref(20)], mmr_lambda=0.7, top_k=10),
    ),
]

#: Sentence Transformers cross-encoder re-ranking the four usual checkpoints.
CROSS_ENCODER_RETRIEVER_CONFIGS = [
    _cross_encoder_config(
        "msmarco_minilm6_dense",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        5,
        _dense_ref(15),
    ),
    _cross_encoder_config(
        "msmarco_minilm12_bm25",
        "cross-encoder/ms-marco-MiniLM-L-12-v2",
        5,
        _bm25_ref(15),
    ),
    _cross_encoder_config(
        "stsb_distilroberta_dense",
        "cross-encoder/stsb-distilroberta-base",
        10,
        _dense_ref(20),
    ),
    _cross_encoder_config(
        "mmarco_multilingual_dense",
        "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        5,
        _dense_ref(15),
    ),
]

#: Sequential cascades: the children must narrow their top_k at every stage.
SEQUENTIAL_RETRIEVER_CONFIGS = [
    _config(
        SEQUENTIAL_RETRIEVER_COMPONENT,
        "BM25_x2",
        "cascade_bm25_top10_to_bm25_top5",
        _children_params([_bm25_ref(10), _bm25_ref(5)]),
    ),
    _config(
        SEQUENTIAL_RETRIEVER_COMPONENT,
        HYBRID_MODEL_NAME,
        "cascade_bm25_top10_to_tfidf_top5",
        _children_params([_bm25_ref(10), _tfidf_retriever_ref(5)]),
    ),
]

#: Parallel retrievers merging a keyword and a TF-IDF child.
PARALLEL_RETRIEVER_CONFIGS = [
    _config(
        PARALLEL_RETRIEVER_COMPONENT,
        HYBRID_MODEL_NAME,
        "round_robin",
        _children_params(
            [_bm25_ref(5), _tfidf_retriever_ref(5)], merge_strategy="round_robin"
        ),
    ),
    _config(
        PARALLEL_RETRIEVER_COMPONENT,
        HYBRID_MODEL_NAME,
        "interleave",
        _children_params(
            [_bm25_ref(5), _tfidf_retriever_ref(5)], merge_strategy="interleave"
        ),
    ),
]

#: LLM-backed retrievers: two configurations per evaluated/filter technique.
LLM_RETRIEVER_CONFIGS = [
    _config(
        LLM_DEPTH_RETRIEVER_COMPONENT,
        FUNCTION_CALLING_LLM_MODEL_NAME,
        "bm25_k6_iters2",
        _llm_evaluated_params([_bm25_ref(5)], max_chunks=6, max_iters=2),
    ),
    _config(
        LLM_DEPTH_RETRIEVER_COMPONENT,
        FUNCTION_CALLING_LLM_MODEL_NAME,
        "dense_k8_iters3",
        _llm_evaluated_params([_dense_ref(5)], max_chunks=8, max_iters=3),
    ),
    _config(
        LLM_ENSEMBLE_RETRIEVER_COMPONENT,
        FUNCTION_CALLING_LLM_MODEL_NAME,
        "bm25_tfidf_k8_iters2",
        _llm_evaluated_params(
            [_bm25_ref(5), _tfidf_retriever_ref(5)], max_chunks=8, max_iters=2
        ),
    ),
    _config(
        LLM_ENSEMBLE_RETRIEVER_COMPONENT,
        FUNCTION_CALLING_LLM_MODEL_NAME,
        "dense_bm25_k10_iters3",
        _llm_evaluated_params(
            [_dense_ref(5), _bm25_ref(5)], max_chunks=10, max_iters=3
        ),
    ),
    _config(
        AGENTIC_RERANKER_RETRIEVER_COMPONENT,
        FUNCTION_CALLING_LLM_MODEL_NAME,
        "bm25_k1_10_top5",
        _llm_filter_params(_bm25_ref(10), k1=10, top_k=5),
    ),
    _config(
        AGENTIC_RERANKER_RETRIEVER_COMPONENT,
        FUNCTION_CALLING_LLM_MODEL_NAME,
        "dense_k1_8_top3",
        _llm_filter_params(_dense_ref(8), k1=8, top_k=3),
    ),
]

#: ``component_type`` group name -> the configs benchmarked under it.
RETRIEVER_FAMILIES: list[tuple[str, list[dict[str, Any]]]] = [
    ("sparse_retriever", RETRIEVER_CONFIGS),
    ("dense_retriever", DENSE_RETRIEVER_CONFIGS),
    ("composite_retriever", COMPOSITE_RETRIEVER_CONFIGS),
    ("cross_encoder_retriever", CROSS_ENCODER_RETRIEVER_CONFIGS),
    ("sequential_retriever", SEQUENTIAL_RETRIEVER_CONFIGS),
    ("parallel_retriever", PARALLEL_RETRIEVER_CONFIGS),
    ("llm_retriever", LLM_RETRIEVER_CONFIGS),
]

#: Every config the retrieval benchmarks execute.
ALL_RETRIEVER_CONFIGS: list[dict[str, Any]] = [
    cfg for _, configs in RETRIEVER_FAMILIES for cfg in configs
]


# ═══════════════════════════════════════════════════════════════════════
#  Component resolution
# ═══════════════════════════════════════════════════════════════════════


@functools.lru_cache(maxsize=1)
def _registered_components() -> dict[str, type]:
    """Return the registered component classes keyed by class name."""
    from DashAI.back.initial_components import get_initial_components

    return {component.__name__: component for component in get_initial_components()}


def _component_class(name: str) -> type:
    """Return the registered class behind *name*.

    Parameters
    ----------
    name : str
        Component class name, such as ``"BM25Retriever"``.

    Returns
    -------
    type
        The registered component class.

    Raises
    ------
    KeyError
        If no registered component carries that class name.
    """
    components = _registered_components()
    if name not in components:
        raise KeyError(
            f"Component '{name}' is not registered in get_initial_components(); "
            "cannot build it for the retrieval benchmark."
        )
    return components[name]


def _iter_component_refs(value: Any) -> Iterator[dict[str, Any]]:
    """Yield every nested component reference found in *value*."""
    if is_component_ref(value):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_component_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_component_refs(item)


def _ensure_hf_repo(model_name: str, download: bool) -> None:
    """Gate a Hugging Face repo that a benchmark component loads directly.

    ``SentenceTransformerCrossEncoderRetriever`` is not a downloadable DashAI
    component, so the generic gate cannot see its checkpoint. Check the local
    cache here: fail under ``--no-download`` when missing, and populate the
    cache before the load timer otherwise.
    """
    from huggingface_hub import snapshot_download

    try:
        snapshot_download(repo_id=model_name, local_files_only=True)
        return
    except Exception:
        if not download:
            raise RuntimeError(
                f"Cross-encoder artifacts for '{model_name}' are missing from "
                "the Hugging Face cache. Re-run without --no-download to fetch "
                "them, or download them in the DashAI app first."
            ) from None
    print(f"  Downloading cross-encoder ({model_name})...")
    snapshot_download(repo_id=model_name)


def _ensure_retriever_downloads(ref: dict[str, Any], download: bool) -> None:
    """Download every missing artifact a retriever reference depends on.

    Runs before the load timer so download time is never reported as model
    load time.

    Parameters
    ----------
    ref : dict[str, Any]
        Retriever reference, possibly nesting other component references.
    download : bool
        When False, a missing artifact raises instead of downloading.
    """
    ensure_component_downloaded(_component_class(ref["component"]), download=download)
    if ref["component"] == CROSS_ENCODER_RETRIEVER_COMPONENT:
        model_name = (ref.get("params") or {}).get("model_name")
        if isinstance(model_name, str) and model_name:
            _ensure_hf_repo(model_name, download)
    for nested in _iter_component_refs(ref.get("params") or {}):
        _ensure_retriever_downloads(nested, download)


def _resolve_nested(value: Any, download: bool) -> Any:
    """Instantiate the component references nested in *value*.

    Parameters
    ----------
    value : Any
        A component reference, a list of references, or a plain value.
    download : bool
        When False, a missing artifact raises instead of downloading.

    Returns
    -------
    Any
        The value with every reference replaced by its instance.
    """
    if is_component_ref(value):
        return _build_component(value, download)
    if isinstance(value, list):
        return [_resolve_nested(item, download) for item in value]
    return value


def _build_component(ref: dict[str, Any], download: bool) -> Any:
    """Instantiate a non-retriever component reference.

    Parameters
    ----------
    ref : dict[str, Any]
        ``{component, params}`` reference of an embedding model, vectorizer,
        prompt or language model.
    download : bool
        When False, a missing artifact raises instead of downloading.

    Returns
    -------
    Any
        The instantiated component.
    """
    component_class = _component_class(ref["component"])
    ensure_component_downloaded(component_class, download=download)
    raw_params = ref.get("params") or {}
    schema = getattr(component_class, "SCHEMA", None)
    if schema is not None:
        unknown = sorted(set(raw_params) - set(schema.model_fields))
        if unknown:
            raise TypeError(f"{ref['component']} declares unknown params {unknown}.")
        raw_params = schema.model_validate(raw_params).model_dump()
    params = {
        key: _resolve_nested(value, download)
        for key, value in copy.deepcopy(raw_params).items()
    }
    return component_class(**params)


def _dense_persistence(chunks: dict[int, dict[int, Any]], tmpdirs: list[str]) -> Any:
    """Return a ``DensePersistence`` with one fresh matrix dir per document.

    Parameters
    ----------
    chunks : dict[int, dict[int, Any]]
        Corpus the retriever indexes; its keys are the document ids.
    tmpdirs : list[str]
        Temporary directories the caller must remove afterwards.

    Returns
    -------
    DensePersistence
        Persistence pointing at empty per-document matrix directories.
    """
    from DashAI.back.models.RAG.retrievers.persistence import DensePersistence

    root = tempfile.mkdtemp()
    tmpdirs.append(root)
    matrix_dirs: dict[int, str] = {}
    for doc_id in chunks:
        matrix_dir = Path(root) / f"doc_{doc_id}"
        matrix_dir.mkdir(parents=True, exist_ok=True)
        matrix_dirs[doc_id] = str(matrix_dir)
    return DensePersistence(matrix_dirs=matrix_dirs, embedding_model_id=0)


def _sparse_persistence() -> Any:
    """Return a ``SparsePersistence`` that fits every retriever from scratch."""
    from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence

    return SparsePersistence(model_dir=None)


def _is_dense_retriever(retriever: Any) -> bool:
    """Return whether *retriever* is a dense embedding retriever.

    Real retrievers are identified by class; a test double can opt in with an
    ``IS_DENSE = True`` class attribute.
    """
    from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
        DenseEmbeddingRetriever,
    )

    return isinstance(retriever, DenseEmbeddingRetriever) or bool(
        getattr(retriever, "IS_DENSE", False)
    )


def _build_retriever(
    ref: dict[str, Any],
    chunks: dict[int, dict[int, Any]],
    tmpdirs: list[str],
    download: bool,
) -> Any:
    """Build a retriever with its children, components and infrastructure.

    Parameters
    ----------
    ref : dict[str, Any]
        Retriever reference, possibly nesting child retrievers.
    chunks : dict[int, dict[int, Any]]
        Corpus the retriever indexes.
    tmpdirs : list[str]
        Temporary directories the caller must remove afterwards; every created
        directory is appended here.
    download : bool
        When False, a missing artifact raises instead of downloading.

    Returns
    -------
    Any
        The retriever, already initialised and ready to retrieve.
    """
    retriever_class = _component_class(ref["component"])
    raw_params = ref.get("params") or {}
    schema = getattr(retriever_class, "SCHEMA", None)
    if schema is not None:
        schema.model_validate(raw_params)

    params = copy.deepcopy(raw_params)
    children = params.pop(CHILDREN_KEY, None)
    if children is not None:
        params[CHILDREN_KEY] = [
            _build_retriever(child, chunks, tmpdirs, download) for child in children
        ]
    params = {key: _resolve_nested(value, download) for key, value in params.items()}
    retriever = retriever_class(**params)
    set_trace_params = getattr(retriever, "set_trace_params", None)
    if callable(set_trace_params):
        set_trace_params(raw_params)

    persistence = (
        _dense_persistence(chunks, tmpdirs)
        if _is_dense_retriever(retriever)
        else _sparse_persistence()
    )
    env_path = tempfile.mkdtemp()
    tmpdirs.append(env_path)
    retriever.inject_infra(
        env_RAG_path=env_path, chunks=chunks, persistence=persistence
    )
    retriever.init_model()
    return retriever


# ═══════════════════════════════════════════════════════════════════════
#  Execution
# ═══════════════════════════════════════════════════════════════════════


def _prepare_chunks(max_docs: int = 2) -> dict:
    """Split the benchmark papers into chunks the retrievers can index."""
    from DashAI.back.models.RAG.documents.chunk import Chunk

    texts = load_paper_texts(max_docs=max_docs)
    chunks: dict[int, dict[int, Chunk]] = {}
    global_id = 0
    for doc_id, text in texts.items():
        doc_chunks: dict[int, Chunk] = {}
        pos = 0
        start = 0
        while start < len(text):
            end = min(start + 300, len(text))
            if end < len(text):
                for sep in (". ", ".\n", "\n\n", "\n", " "):
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start + 150:
                        end = last_sep + len(sep)
                        break
            chunk_text = text[start:end].strip()
            if chunk_text:
                doc_chunks[pos] = Chunk(
                    id=global_id,
                    document_id=doc_id,
                    document_position=pos,
                    text=chunk_text,
                )
                global_id += 1
                pos += 1
            start = end
        chunks[doc_id] = doc_chunks
    return chunks


def _assert_llm_trace(component_class: str, trace: dict[str, Any]) -> None:
    """Assert the trace proves the LLM retrievers consulted their model.

    Parameters
    ----------
    component_class : str
        Class name of the retriever that produced *trace*.
    trace : dict[str, Any]
        The retriever's trace node.

    Raises
    ------
    AssertionError
        If the technique's LLM evidence is missing from the trace.
    """
    if component_class == AGENTIC_RERANKER_RETRIEVER_COMPONENT:
        selection = trace.get(SELECTION_TRACE_KEY) or {}
        assert selection.get(LLM_USED_TRACE_KEY) is True, (
            "AgenticRerankerRetriever did not use its language model; "
            f"selection trace was {selection}"
        )
    elif component_class in LLM_RETRIEVER_COMPONENTS:
        assert trace.get(ROUNDS_TRACE_KEY), (
            f"{component_class} reported no evaluation rounds; "
            f"trace keys were {sorted(trace)}"
        )


def _execute_retriever_config(
    cfg: dict,
    *,
    download_missing_models: bool = True,
    chunks: Optional[dict] = None,
) -> tuple[str, float, float, str]:
    """Benchmark one retriever config, returning ``(status, exec, load, error)``.

    Parameters
    ----------
    cfg : dict
        Benchmark config carrying ``component_class`` and ``params``.
    download_missing_models : bool
        When False, a missing artifact fails the execution instead of being
        downloaded.
    chunks : dict or None
        Corpus prepared by the caller. A whole run passes the same corpus to
        every config so the PDFs are parsed once, not once per config.

    Returns
    -------
    tuple[str, float, float, str]
        Status, retrieval time, load time and error message (empty on success).
    """
    params = copy.deepcopy(cfg.get("params") or {})
    params.pop(ITERATION_KEY, None)
    params.pop(TOTAL_ITERATIONS_KEY, None)
    ref = {"component": cfg["component_class"], "params": params}
    query = cfg.get("query") or DEFAULT_QUERY

    chunks = _prepare_chunks() if chunks is None else chunks
    tmpdirs: list[str] = []
    retriever = None
    try:
        _ensure_retriever_downloads(ref, download_missing_models)
        with Timer() as load_timer:
            retriever = _build_retriever(ref, chunks, tmpdirs, download_missing_models)

        with Timer() as exec_timer:
            result_chunks, trace = retriever.retrieve(query)

        assert result_chunks, "No chunks returned"
        assert isinstance(trace, dict), (
            f"trace must be a dict, got {type(trace).__name__}"
        )
        _assert_llm_trace(cfg["component_class"], trace)
        return "passed", exec_timer.elapsed, load_timer.elapsed, ""
    finally:
        try:
            if retriever is not None:
                close = getattr(retriever, "close", None)
                if callable(close):
                    close()
        finally:
            for tmpdir in tmpdirs:
                shutil.rmtree(tmpdir, ignore_errors=True)


def _inject_iteration(
    cfg: dict[str, Any], iteration: int, total_iterations: int, device: str
) -> dict[str, Any]:
    """Return a deep copy of *cfg* carrying the run bookkeeping keys.

    Parameters
    ----------
    cfg : dict[str, Any]
        Benchmark config to prepare.
    iteration : int
        1-based iteration number.
    total_iterations : int
        Iterations this run executes.
    device : str
        Resolved device every LLM retriever must run on.

    Returns
    -------
    dict[str, Any]
        The prepared config; the input mapping is never mutated.
    """
    prepared = copy.deepcopy(cfg)
    params = prepared.setdefault("params", {})
    params[ITERATION_KEY] = iteration
    params[TOTAL_ITERATIONS_KEY] = total_iterations
    if prepared["component_class"] in LLM_RETRIEVER_COMPONENTS:
        llm_ref = params[LLM_MODEL_KEY]
        llm_ref["params"] = {**llm_ref["params"], DEVICE_KEY: device}
    return prepared


def run_all_retrieval_benchmarks(
    logger,
    iterations: int = 1,
    device: str = "CPU",
    skip_passes: bool = False,
    results_dir: Optional[Path] = None,
    download_missing_models: bool = True,
) -> None:
    """Run all retriever family benchmarks, optionally skipping passed configs.

    Parameters
    ----------
    logger : BenchmarkLogger
    iterations : int
        Number of iterations per config.
    device : str
        Device for local LLM inference: ``auto`` resolves to the first
        llama.cpp GPU (falling back to ``CPU``), and ``GPU``/``CUDA`` ask for
        that GPU explicitly.
    skip_passes : bool
        If True, skip configs that passed in the last benchmark run.
    results_dir : Path or None
        Base results directory scanned for previous runs (falls back to
        the logger's output directory when None).
    download_missing_models : bool
        If True, download missing model artifacts before loading. If False, a
        missing model fails that execution instead (``--no-download``).
    """
    device = _resolve_llm_device(device)
    statuses = (
        load_last_run_statuses(results_dir or logger.output_dir)
        if skip_passes
        else None
    )
    chunks = _prepare_chunks()
    execute_fn = functools.partial(
        _execute_retriever_config,
        download_missing_models=download_missing_models,
        chunks=chunks,
    )
    for iteration in range(1, iterations + 1):
        for component_type, configs in RETRIEVER_FAMILIES:
            prepared = [
                _inject_iteration(cfg, iteration, iterations, device) for cfg in configs
            ]
            run_configs(
                prepared,
                component_type,
                execute_fn,
                logger,
                skip_statuses=statuses,
            )
