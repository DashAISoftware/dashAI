"""Centralized RAG backend defaults.

This module is the single source of truth for the backend defaults shared by
the retriever presets, the RAG session defaults and the placeholders of the
LLM-evaluated composite retrievers:

* the default keyword, semantic and hybrid retrievers,
* the default semantic embedding model,
* the default RAG function-calling LLM (the registered Qwen 2.5 1.5B, with
  the sampling parameters and context window the RAG helper stages need),
* the RAG *LLM parameter overrides* shared by the query-transformation stage
  and the LLM-evaluated retrievers, plus the merge rule that applies them.

The recipes are expressed as plain ``{component, params}`` dictionaries with
component names as strings, so this module never imports component classes and
cannot introduce import cycles. Every factory returns a fresh dictionary:
callers can mutate the result without affecting a later call or another
caller.
"""

import copy
import math
from collections.abc import Mapping
from typing import Any, Dict

#: Number of chunks the default retrievers select.
DEFAULT_TOP_K = 10

#: Small multilingual Sentence Transformer used by the semantic default.
DEFAULT_SEMANTIC_MODEL_NAME = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

#: Context window the default RAG function-calling LLM needs to judge a
#: retrieval pool together with the sufficiency prompt. Shared with the
#: session-level generation budget so both cannot drift apart.
DEFAULT_RAG_CONTEXT_WINDOW = 10_000
DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW = DEFAULT_RAG_CONTEXT_WINDOW

#: Sampling temperature for the RAG helper LLMs (query transformation and the
#: LLM-evaluated retrievers). Lower than the shared text-generation
#: placeholder: those stages must emit a structured function call, not prose.
DEFAULT_RAG_LLM_TEMPERATURE = 0.1

#: Completion budget for the RAG helper LLMs. Their function calls carry the
#: queries or the sufficiency verdict, which does not fit the shared 100-token
#: text-generation placeholder.
DEFAULT_RAG_LLM_MAX_TOKENS = 300

#: Default pool and round budgets for the LLM-evaluated retrievers.
DEFAULT_MAX_CHUNKS = 10
DEFAULT_MAX_ITERS = 3

#: Default candidate and final budgets for the LLM filter retriever.
DEFAULT_FILTER_K1 = 10
DEFAULT_FILTER_TOP_K = 5

#: Default maximum number of function-call attempts (first call included).
DEFAULT_FUNCTION_CALL_MAX_TRIALS = 3

#: Upper bound for the configurable function-call attempts, so a typo cannot
#: turn a single RAG turn into an effectively unbounded LLM retry loop.
MAX_FUNCTION_CALL_TRIALS = 10

#: Default retrieval-sufficiency prompt component.
DEFAULT_SUFFICIENCY_PROMPT_COMPONENT = "DefaultRetrievalSufficiencyPrompt"

#: Default LLM filter prompt component.
DEFAULT_LLM_FILTER_PROMPT_COMPONENT = "DefaultLLMFilterPrompt"

#: Component names used by the recipes.
KEYWORD_RETRIEVER_COMPONENT = "BM25Retriever"
SEMANTIC_RETRIEVER_COMPONENT = "DenseEmbeddingRetriever"
HYBRID_RETRIEVER_COMPONENT = "ParallelRetriever"
FUNCTION_CALLING_LLM_COMPONENT = "Qwen25_15BInstruct"
BM25_VECTORIZER_COMPONENT = "BM25VectorizerModel"
SENTENCE_TRANSFORMER_EMBEDDING_COMPONENT = "SentenceTransformerEmbedding"

#: Complete BM25 vectorizer parameters (the schema fills no missing values).
_BM25_VECTORIZER_PARAMS: Dict[str, Any] = {
    "strip_accents": None,
    "lowercase": True,
    "stop_words": None,
    "max_df": 1.0,
    "min_df": 0.0,
    "max_features": None,
}

#: Complete keyword retriever parameters, before applying ``top_k``.
_KEYWORD_PARAMS: Dict[str, Any] = {
    "BM25Vectorizer": {
        "component": BM25_VECTORIZER_COMPONENT,
        "params": _BM25_VECTORIZER_PARAMS,
    },
    "k1": 1.5,
    "b": 0.75,
    "delta": 0.0,
    "similarity_function": "cosine",
    "top_k": DEFAULT_TOP_K,
}

#: Complete semantic retriever parameters, before applying ``top_k``.
_SEMANTIC_PARAMS: Dict[str, Any] = {
    "embedding_model": {
        "component": SENTENCE_TRANSFORMER_EMBEDDING_COMPONENT,
        "params": {
            "model_name": DEFAULT_SEMANTIC_MODEL_NAME,
            "overflow_strategy": "truncate",
            "normalize": True,
            "device": "cpu",
        },
    },
    "similarity_metric": "cosine",
    "top_k": DEFAULT_TOP_K,
}

#: Complete RAG function-calling LLM parameters.
_FUNCTION_CALLING_LLM_PARAMS: Dict[str, Any] = {
    "max_tokens": DEFAULT_RAG_LLM_MAX_TOKENS,
    "temperature": DEFAULT_RAG_LLM_TEMPERATURE,
    "frequency_penalty": 0.1,
    "context_window": DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW,
    "device": "CPU",
}


def default_keyword_retriever(top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """Return the default keyword (BM25) retriever recipe.

    Parameters
    ----------
    top_k : int, optional
        Number of chunks the retriever selects. Defaults to
        :data:`DEFAULT_TOP_K`.

    Returns
    -------
    Dict[str, Any]
        A fresh ``{"component": "BM25Retriever", "params": {...}}`` reference
        with every schema parameter populated.
    """
    params = copy.deepcopy(_KEYWORD_PARAMS)
    params["top_k"] = top_k
    return {"component": KEYWORD_RETRIEVER_COMPONENT, "params": params}


def default_semantic_retriever(top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """Return the default semantic (dense embedding) retriever recipe.

    Parameters
    ----------
    top_k : int, optional
        Number of chunks the retriever selects. Defaults to
        :data:`DEFAULT_TOP_K`.

    Returns
    -------
    Dict[str, Any]
        A fresh ``{"component": "DenseEmbeddingRetriever", "params": {...}}``
        reference using :data:`DEFAULT_SEMANTIC_MODEL_NAME`.
    """
    params = copy.deepcopy(_SEMANTIC_PARAMS)
    params["top_k"] = top_k
    return {"component": SEMANTIC_RETRIEVER_COMPONENT, "params": params}


def default_hybrid_retriever(top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """Return the default hybrid retriever recipe.

    The hybrid is a ``ParallelRetriever`` that round-robins the keyword and
    semantic defaults. The budget is split with ``ceil`` for keyword retrieval
    and ``floor`` for semantic retrieval, so the children add up to ``top_k``.

    Parameters
    ----------
    top_k : int, optional
        Total number of chunks the hybrid retriever returns. Defaults to
        :data:`DEFAULT_TOP_K`.

    Returns
    -------
    Dict[str, Any]
        A fresh ``{"component": "ParallelRetriever", "params": {...}}``
        reference with fully configured children.
    """
    # Each child must keep a valid positive top_k. With top_k=1 the raw split
    # would give the semantic child 0, which its schema rejects; the endpoint
    # accepts top_k>=1, so clamp both branches.
    keyword_top_k = max(1, math.ceil(top_k / 2))
    semantic_top_k = max(1, math.floor(top_k / 2))
    return {
        "component": HYBRID_RETRIEVER_COMPONENT,
        "params": {
            "merge_strategy": "round_robin",
            "children": [
                default_keyword_retriever(keyword_top_k),
                default_semantic_retriever(semantic_top_k),
            ],
        },
    }


def default_retrieval_sufficiency_prompt() -> Dict[str, Any]:
    """Return the default retrieval-sufficiency prompt reference.

    Returns
    -------
    Dict[str, Any]
        A fresh
        ``{"component": "DefaultRetrievalSufficiencyPrompt", "params": {}}``
        reference. The backend injects the language template.
    """
    return {
        "component": DEFAULT_SUFFICIENCY_PROMPT_COMPONENT,
        "params": {},
    }


def default_llm_filter_prompt() -> Dict[str, Any]:
    """Return the default LLM filter prompt reference.

    Returns
    -------
    Dict[str, Any]
        A fresh ``{"component": "DefaultLLMFilterPrompt", "params": {}}``
        reference. The backend injects the language template.
    """
    return {
        "component": DEFAULT_LLM_FILTER_PROMPT_COMPONENT,
        "params": {},
    }


def default_function_calling_llm() -> Dict[str, Any]:
    """Return the default RAG function-calling LLM recipe.

    The default is the registered Qwen 2.5 1.5B Instruct component. Its schema
    ships conservative text-generation placeholders (512 context window, 0.7
    temperature, 100 max tokens); the RAG default raises the context window to
    :data:`DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW`, lowers the temperature
    to :data:`DEFAULT_RAG_LLM_TEMPERATURE` and grows the budget to
    :data:`DEFAULT_RAG_LLM_MAX_TOKENS`, because retrieval evaluation must fit
    the sufficiency prompt plus the retrieved chunks in one pass and answer with
    a structured function call.

    Returns
    -------
    Dict[str, Any]
        A fresh ``{"component": "Qwen25_15BInstruct", "params": {...}}``
        reference using the RAG sampling parameters and context window.
    """
    return {
        "component": FUNCTION_CALLING_LLM_COMPONENT,
        "params": copy.deepcopy(_FUNCTION_CALLING_LLM_PARAMS),
    }


def rag_llm_param_overrides() -> Dict[str, Any]:
    """Return the LLM parameters the RAG helper stages set on every model.

    Both the query-transformation stage and the LLM-evaluated retrievers call
    a text-generation model to emit a function call. The shared model schemas
    are tuned for free-form generation, so RAG overrides the three parameters
    that decide whether the call fits and stays deterministic.

    Returns
    -------
    Dict[str, Any]
        A fresh ``{temperature, context_window, max_tokens}`` mapping. Models
        without one of those parameters simply ignore the extra key.
    """
    return {
        "temperature": DEFAULT_RAG_LLM_TEMPERATURE,
        "context_window": DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW,
        "max_tokens": DEFAULT_RAG_LLM_MAX_TOKENS,
    }


def _same_llm_value(left: Any, right: Any) -> bool:
    """Compare two LLM parameter values, tolerating numeric strings.

    The merge runs before pydantic coerces the payload, so a caller may send
    ``"512"`` where the schema placeholder is ``512``. Booleans are compared
    strictly: ``True`` is not the numeric value ``1`` for this purpose.

    Parameters
    ----------
    left : Any
        Caller value.
    right : Any
        Schema placeholder value.

    Returns
    -------
    bool
        ``True`` when both values represent the same non-boolean value.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if left == right:
        return True
    try:
        return float(left) == float(right)
    except (TypeError, ValueError):
        return False


def merge_rag_llm_params(
    schema_defaults: Dict[str, Any],
    caller_params: Dict[str, Any] | None,
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Merge the RAG LLM overrides above the schema placeholders.

    A caller value that equals the model's schema placeholder is treated as
    *not customized*: the shared RAG frontend writes those placeholders when a
    different LLM is selected, so honouring them verbatim would silently clamp
    every RAG stage back to the text-generation defaults. Such a value is
    dropped and the RAG override applies instead.

    Any caller value that differs from the schema placeholder is an explicit
    customization and wins over the override. Caller keys the overrides do not
    track (``device``, ``frequency_penalty``, ...) are always preserved.

    Overrides are only applied for keys the selected schema actually declares,
    so a model that names its context window differently (for example
    DeepSeek's ``n_ctx``) is never handed an unknown ``context_window`` key.

    Parameters
    ----------
    schema_defaults : Dict[str, Any]
        The selected LLM's resolved schema placeholders.
    caller_params : Dict[str, Any] | None
        The parameters sent by the caller. The top-level mapping is never
        mutated.
    overrides : Dict[str, Any] | None, optional
        RAG overrides to apply. Defaults to :func:`rag_llm_param_overrides`.

    Returns
    -------
    Dict[str, Any]
        ``{**schema_defaults, **applicable_overrides, **customized_caller_params}``.

    Raises
    ------
    TypeError
        If ``schema_defaults``, ``caller_params`` or ``overrides`` is not a
        mapping (``caller_params`` and ``overrides`` may also be ``None``).
    """
    if not isinstance(schema_defaults, Mapping):
        raise TypeError(
            f"schema_defaults must be a mapping, got {type(schema_defaults).__name__}."
        )
    if caller_params is not None and not isinstance(caller_params, Mapping):
        raise TypeError(
            "caller_params must be a mapping or None, got "
            f"{type(caller_params).__name__}."
        )
    if overrides is not None and not isinstance(overrides, Mapping):
        raise TypeError(
            f"overrides must be a mapping or None, got {type(overrides).__name__}."
        )
    requested_overrides = (
        rag_llm_param_overrides() if overrides is None else dict(overrides)
    )
    effective_overrides = {
        key: value
        for key, value in requested_overrides.items()
        if key in schema_defaults
    }
    customized = dict(caller_params or {})
    for key in effective_overrides:
        if key in customized and _same_llm_value(
            customized[key], schema_defaults.get(key)
        ):
            del customized[key]
    return {**schema_defaults, **effective_overrides, **customized}
