"""Tests for the centralized RAG backend defaults.

The defaults module is the single source of truth for the retriever preset
identities and parameters, the default RAG function-calling LLM, and the
placeholders of the LLM-evaluated composite retrievers.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any, Dict

import pytest

from DashAI.back.converters.hugging_face.text_embedding import (
    ParaphraseMultilingualMiniLML12V2Embedding,
)
from DashAI.back.converters.scikit_learn.bag_of_words import BagOfWordsConverter
from DashAI.back.initial_components import get_initial_components
from DashAI.back.models.hugging_face.qwen_model import Qwen25_15BInstruct
from DashAI.back.models.RAG.RAG_constants import (
    COMPOSITE_RETRIEVER_NAMES,
    LLM_EVALUATED_RETRIEVER_NAMES,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_EMBEDDING_BATCH_SIZE,
    DEFAULT_EMBEDDING_DEVICE,
    DEFAULT_EMBEDDING_OVERFLOW_STRATEGY,
    DEFAULT_FILTER_K1,
    DEFAULT_FILTER_TOP_K,
    DEFAULT_FUNCTION_CALL_MAX_TRIALS,
    DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW,
    DEFAULT_MAX_CHUNKS,
    DEFAULT_MAX_ITERS,
    DEFAULT_RAG_LLM_MAX_TOKENS,
    DEFAULT_RAG_LLM_TEMPERATURE,
    DEFAULT_SEMANTIC_MODEL_NAME,
    DEFAULT_TOP_K,
    default_function_calling_llm,
    default_hybrid_retriever,
    default_keyword_retriever,
    default_llm_filter_prompt,
    default_retrieval_sufficiency_prompt,
    default_semantic_retriever,
    merge_rag_llm_params,
    rag_llm_param_overrides,
)
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_depth_retriever import (
    LLMEvaluatedDepthRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.llm_evaluated_ensemble_retriever import (  # noqa: E501
    LLMEvaluatedEnsembleRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.llm_filter_retriever import (
    LLMFilterRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.parallel_retriever import (
    ParallelRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import BM25Retriever

#: Bag-of-words parameters the keyword default ships: the schema placeholders,
#: with ``max_features`` unset so BM25 weights the whole vocabulary.
BAG_OF_WORDS_DEFAULTS = {
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

#: Embedding parameters the semantic default ships: the schema placeholders.
EMBEDDING_DEFAULTS = {
    "device": DEFAULT_EMBEDDING_DEVICE,
    "batch_size": DEFAULT_EMBEDDING_BATCH_SIZE,
    "normalize": True,
    "overflow_strategy": DEFAULT_EMBEDDING_OVERFLOW_STRATEGY,
}

# ---------------------------------------------------------------------------
# retriever factories
# ---------------------------------------------------------------------------


class TestRetrieverFactories:
    """The keyword, semantic and hybrid recipes are centralized and complete."""

    def test_default_keyword_retriever(self):
        ref = default_keyword_retriever()

        assert ref["component"] == "BM25Retriever"
        params = ref["params"]
        assert params["top_k"] == DEFAULT_TOP_K
        assert params["k1"] == 1.5
        assert params["b"] == 0.75
        assert params["delta"] == 0.0
        assert params["similarity_function"] == "cosine"

        vectorizer = params["vectorizer"]
        assert vectorizer["component"] == "BagOfWordsConverter"
        assert vectorizer["params"] == BAG_OF_WORDS_DEFAULTS

    def test_default_keyword_retriever_custom_top_k(self):
        ref = default_keyword_retriever(top_k=3)

        assert ref["params"]["top_k"] == 3

    def test_default_semantic_retriever(self):
        ref = default_semantic_retriever()

        assert ref["component"] == "DenseEmbeddingRetriever"
        params = ref["params"]
        assert params["top_k"] == DEFAULT_TOP_K
        assert params["similarity_metric"] == "cosine"

        embedding = params["embedding_model"]
        assert embedding["component"] == "ParaphraseMultilingualMiniLML12V2Embedding"
        assert embedding["params"] == EMBEDDING_DEFAULTS
        assert ParaphraseMultilingualMiniLML12V2Embedding.MODEL_NAME == (
            DEFAULT_SEMANTIC_MODEL_NAME
        )
        assert DEFAULT_SEMANTIC_MODEL_NAME == (
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )

    def test_default_recipes_name_registered_components(self):
        registered = {component.__name__ for component in get_initial_components()}
        keyword = default_keyword_retriever()
        semantic = default_semantic_retriever()

        assert keyword["component"] in registered
        assert keyword["params"]["vectorizer"]["component"] in registered
        assert semantic["component"] in registered
        assert semantic["params"]["embedding_model"]["component"] in registered

    def test_nested_component_params_cover_every_schema_field(self):
        """A nested recipe must be complete: it replaces the resolved defaults.

        The preset builders merge ``{**resolve_component_defaults(...), **ref}``,
        so a nested ``params`` mapping that omits a field would drop that field
        instead of inheriting its placeholder.
        """
        keyword = default_keyword_retriever()
        semantic = default_semantic_retriever()

        assert set(keyword["params"]["vectorizer"]["params"]) == set(
            BagOfWordsConverter.get_schema()["properties"]
        )
        assert set(semantic["params"]["embedding_model"]["params"]) == set(
            ParaphraseMultilingualMiniLML12V2Embedding.get_schema()["properties"]
        )

    def test_default_hybrid_retriever_splits_top_k(self):
        ref = default_hybrid_retriever(top_k=15)

        assert ref["component"] == "ParallelRetriever"
        params = ref["params"]
        assert params["merge_strategy"] == "round_robin"

        keyword, semantic = params["children"]
        assert keyword["component"] == "BM25Retriever"
        assert keyword["params"]["top_k"] == 8  # ceil(15 / 2)
        assert semantic["component"] == "DenseEmbeddingRetriever"
        assert semantic["params"]["top_k"] == 7  # floor(15 / 2)

    def test_default_hybrid_retriever_defaults_to_ten(self):
        ref = default_hybrid_retriever()

        keyword, semantic = ref["params"]["children"]
        assert keyword["params"]["top_k"] == 5
        assert semantic["params"]["top_k"] == 5

    def test_default_hybrid_retriever_keeps_small_top_k_valid(self):
        ref = default_hybrid_retriever(top_k=1)

        keyword, semantic = ref["params"]["children"]
        assert keyword["params"]["top_k"] == 1
        assert semantic["params"]["top_k"] == 1

    def test_factories_return_fresh_dicts(self):
        first = default_keyword_retriever()
        first["params"]["top_k"] = 999
        first["params"]["vectorizer"]["params"]["lowercase"] = False
        assert default_keyword_retriever()["params"]["top_k"] == DEFAULT_TOP_K
        assert (
            default_keyword_retriever()["params"]["vectorizer"]["params"]["lowercase"]
            is True
        )

        semantic = default_semantic_retriever()
        semantic["params"]["embedding_model"]["params"]["device"] = "cuda"
        assert (
            default_semantic_retriever()["params"]["embedding_model"]["params"][
                "device"
            ]
            == DEFAULT_EMBEDDING_DEVICE
        )

        hybrid = default_hybrid_retriever()
        hybrid["params"]["children"][0]["params"]["top_k"] = 999
        assert (
            default_hybrid_retriever()["params"]["children"][0]["params"]["top_k"] == 5
        )

        llm = default_function_calling_llm()
        llm["params"]["context_window"] = 1
        assert (
            default_function_calling_llm()["params"]["context_window"]
            == DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW
        )


# ---------------------------------------------------------------------------
# default function-calling LLM
# ---------------------------------------------------------------------------


class TestDefaultFunctionCallingLLM:
    """The default RAG LLM is a complete, valid Qwen 1.5B recipe."""

    def test_default_function_calling_llm(self):
        ref = default_function_calling_llm()

        assert ref["component"] == "Qwen25_15BInstruct"
        assert ref["params"] == {
            "max_tokens": 300,
            "temperature": 0.1,
            "frequency_penalty": 0.1,
            "context_window": DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW,
            "device": "CPU",
        }
        assert DEFAULT_FUNCTION_CALLING_LLM_CONTEXT_WINDOW == 10_000
        assert DEFAULT_RAG_LLM_MAX_TOKENS == 300
        assert DEFAULT_RAG_LLM_TEMPERATURE == 0.1

    def test_default_llm_overrides_the_qwen_context_window(self):
        """The registered Qwen keeps its schema default; RAG overrides it."""
        schema = Qwen25_15BInstruct.get_schema()
        assert schema["properties"]["context_window"]["placeholder"] == 512

        ref = default_function_calling_llm()
        assert ref["params"]["context_window"] == 10_000
        Qwen25_15BInstruct.SCHEMA.model_validate(ref["params"])

    def test_qwen_supports_function_calling(self):
        assert Qwen25_15BInstruct.supports_function_calling() is True

    def test_default_params_validate_against_their_schemas(self):
        keyword = default_keyword_retriever()
        semantic = default_semantic_retriever()
        BM25Retriever.SCHEMA.model_validate(keyword["params"])
        DenseEmbeddingRetriever.SCHEMA.model_validate(semantic["params"])
        ParallelRetriever.SCHEMA.model_validate(default_hybrid_retriever()["params"])
        Qwen25_15BInstruct.SCHEMA.model_validate(
            default_function_calling_llm()["params"]
        )

        # component_field only validates the {component, params} container, so
        # the nested schemas need their own check.
        BagOfWordsConverter.SCHEMA.model_validate(
            keyword["params"]["vectorizer"]["params"]
        )
        ParaphraseMultilingualMiniLML12V2Embedding.SCHEMA.model_validate(
            semantic["params"]["embedding_model"]["params"]
        )

    def test_default_llm_component_is_registered(self):
        registered = {component.__name__ for component in get_initial_components()}
        assert "Qwen25_15BInstruct" in registered

    def test_default_llm_params_cover_every_schema_field(self):
        validated = Qwen25_15BInstruct.SCHEMA.model_validate(
            default_function_calling_llm()["params"]
        )
        assert set(validated.model_dump()) == {
            "max_tokens",
            "temperature",
            "frequency_penalty",
            "context_window",
            "device",
        }


# ---------------------------------------------------------------------------
# RAG LLM overrides and their merge rule
# ---------------------------------------------------------------------------


class TestRagLLMParamOverrides:
    """The three RAG-owned LLM params are exposed as one override mapping."""

    def test_overrides_are_the_three_rag_params(self):
        assert rag_llm_param_overrides() == {
            "temperature": 0.1,
            "context_window": 10_000,
            "max_tokens": 300,
        }

    def test_overrides_match_the_default_llm_recipe(self):
        overrides = rag_llm_param_overrides()
        params = default_function_calling_llm()["params"]

        assert {key: params[key] for key in overrides} == overrides

    def test_overrides_return_a_fresh_dict(self):
        first = rag_llm_param_overrides()
        first["max_tokens"] = 1

        assert rag_llm_param_overrides()["max_tokens"] == 300


class TestMergeRagLLMParams:
    """Schema placeholders mean "not customized"; explicit values win."""

    #: Mirrors the shared GGUF text-generation placeholders.
    SCHEMA: Dict[str, Any] = {
        "max_tokens": 100,
        "temperature": 0.7,
        "context_window": 512,
        "device": "CPU",
    }

    def test_schema_placeholders_are_replaced_by_the_overrides(self):
        merged = merge_rag_llm_params(
            self.SCHEMA,
            {"max_tokens": 100, "temperature": 0.7, "context_window": 512},
        )

        assert merged["max_tokens"] == 300
        assert merged["temperature"] == 0.1
        assert merged["context_window"] == 10_000
        assert merged["device"] == "CPU"

    def test_explicit_non_default_values_win(self):
        merged = merge_rag_llm_params(
            self.SCHEMA,
            {"max_tokens": 500, "temperature": 0.3, "context_window": 4096},
        )

        assert merged["max_tokens"] == 500
        assert merged["temperature"] == 0.3
        assert merged["context_window"] == 4096

    def test_untracked_caller_keys_are_preserved(self):
        merged = merge_rag_llm_params(
            self.SCHEMA,
            {"frequency_penalty": 0.4, "device": "GPU"},
        )

        assert merged["frequency_penalty"] == 0.4
        assert merged["device"] == "GPU"

    def test_only_the_customized_values_survive_a_mixed_payload(self):
        merged = merge_rag_llm_params(
            self.SCHEMA,
            {"max_tokens": 100, "temperature": 0.3},
        )

        assert merged["max_tokens"] == 300
        assert merged["temperature"] == 0.3

    def test_absent_caller_params_resolve_schema_and_overrides(self):
        merged = merge_rag_llm_params(self.SCHEMA, None)

        assert merged == {
            "max_tokens": 300,
            "temperature": 0.1,
            "context_window": 10_000,
            "device": "CPU",
        }

    def test_caller_params_are_not_mutated(self):
        caller = {"max_tokens": 100, "temperature": 0.7}

        merge_rag_llm_params(self.SCHEMA, caller)

        assert caller == {"max_tokens": 100, "temperature": 0.7}

    def test_non_mapping_caller_params_raise_type_error(self):
        with pytest.raises(TypeError, match="caller_params must be a mapping"):
            merge_rag_llm_params(self.SCHEMA, ["max_tokens"])

    def test_non_mapping_schema_defaults_raise_type_error(self):
        with pytest.raises(TypeError, match="schema_defaults must be a mapping"):
            merge_rag_llm_params(None, {})

    def test_non_mapping_overrides_raise_type_error(self):
        with pytest.raises(TypeError, match="overrides must be a mapping"):
            merge_rag_llm_params(self.SCHEMA, {}, ["max_tokens"])

    def test_numeric_strings_compare_like_numbers(self):
        merged = merge_rag_llm_params(
            self.SCHEMA,
            {"max_tokens": "100", "temperature": "0.7", "context_window": "512"},
        )

        assert merged["max_tokens"] == 300
        assert merged["temperature"] == 0.1
        assert merged["context_window"] == 10_000

    def test_override_keys_missing_from_the_schema_are_skipped(self):
        """A model with ``n_ctx`` instead of ``context_window`` keeps n_ctx."""
        schema = {"max_tokens": 100, "temperature": 0.7, "n_ctx": 4096}

        merged = merge_rag_llm_params(
            schema, {"max_tokens": 100, "temperature": 0.7, "n_ctx": 4096}
        )

        assert merged == {"max_tokens": 300, "temperature": 0.1, "n_ctx": 4096}

    def test_explicit_overrides_argument_replaces_the_rag_defaults(self):
        merged = merge_rag_llm_params(
            self.SCHEMA,
            {"max_tokens": 100, "temperature": 0.7},
            {"max_tokens": 42},
        )

        assert merged["max_tokens"] == 42
        assert merged["temperature"] == 0.7
        assert merged["context_window"] == 512


# ---------------------------------------------------------------------------
# LLM-evaluated retriever placeholders
# ---------------------------------------------------------------------------


class TestLLMEvaluatedRetrieverPlaceholders:
    """The adaptive retrievers seed their component fields with the defaults."""

    def _placeholder(self, component: Any, field: str) -> Dict[str, Any]:
        return component.get_schema()["properties"][field]["placeholder"]

    def test_depth_retriever_placeholders(self):
        assert self._placeholder(LLMEvaluatedDepthRetriever, "children") == [
            default_hybrid_retriever()
        ]
        assert (
            self._placeholder(LLMEvaluatedDepthRetriever, "llm_model")
            == default_function_calling_llm()
        )
        assert (
            self._placeholder(LLMEvaluatedDepthRetriever, "prompt")
            == default_retrieval_sufficiency_prompt()
        )
        assert (
            self._placeholder(LLMEvaluatedDepthRetriever, "max_chunks")
            == DEFAULT_MAX_CHUNKS
        )
        assert (
            self._placeholder(LLMEvaluatedDepthRetriever, "max_iters")
            == DEFAULT_MAX_ITERS
        )
        assert (
            self._placeholder(LLMEvaluatedDepthRetriever, "function_call_max_trials")
            == DEFAULT_FUNCTION_CALL_MAX_TRIALS
        )

    def test_ensemble_retriever_placeholders(self):
        assert self._placeholder(LLMEvaluatedEnsembleRetriever, "children") == [
            default_semantic_retriever(),
            default_keyword_retriever(),
        ]
        assert (
            self._placeholder(LLMEvaluatedEnsembleRetriever, "llm_model")
            == default_function_calling_llm()
        )
        assert (
            self._placeholder(LLMEvaluatedEnsembleRetriever, "prompt")
            == default_retrieval_sufficiency_prompt()
        )
        assert (
            self._placeholder(LLMEvaluatedEnsembleRetriever, "max_chunks")
            == DEFAULT_MAX_CHUNKS
        )
        assert (
            self._placeholder(LLMEvaluatedEnsembleRetriever, "max_iters")
            == DEFAULT_MAX_ITERS
        )
        assert (
            self._placeholder(LLMEvaluatedEnsembleRetriever, "function_call_max_trials")
            == DEFAULT_FUNCTION_CALL_MAX_TRIALS
        )

    def test_filter_retriever_placeholders(self):
        assert self._placeholder(LLMFilterRetriever, "children") == [
            default_hybrid_retriever()
        ]
        assert self._placeholder(LLMFilterRetriever, "k1") == DEFAULT_FILTER_K1
        assert self._placeholder(LLMFilterRetriever, "top_k") == DEFAULT_FILTER_TOP_K
        assert (
            self._placeholder(LLMFilterRetriever, "llm_model")
            == default_function_calling_llm()
        )
        assert (
            self._placeholder(LLMFilterRetriever, "prompt")
            == default_llm_filter_prompt()
        )
        assert (
            self._placeholder(LLMFilterRetriever, "function_call_max_trials")
            == DEFAULT_FUNCTION_CALL_MAX_TRIALS
        )

    def test_default_llm_filter_prompt(self):
        ref = default_llm_filter_prompt()

        assert ref == {"component": "DefaultLLMFilterPrompt", "params": {}}

    def test_default_llm_filter_prompt_is_fresh(self):
        first = default_llm_filter_prompt()
        first["params"]["language"] = "es"

        assert default_llm_filter_prompt() == {
            "component": "DefaultLLMFilterPrompt",
            "params": {},
        }

    def test_filter_defaults_are_sane(self):
        assert DEFAULT_FILTER_K1 >= 1
        assert DEFAULT_FILTER_TOP_K >= 1
        assert DEFAULT_FILTER_TOP_K <= DEFAULT_FILTER_K1

    def test_filter_retriever_and_prompts_are_registered(self):
        registered = {component.__name__ for component in get_initial_components()}

        assert "LLMFilterRetriever" in registered
        assert "DefaultLLMFilterPrompt" in registered
        assert "CustomLLMFilterPrompt" in registered
        assert "LLMFilterRetriever" in COMPOSITE_RETRIEVER_NAMES
        assert "LLMFilterRetriever" in LLM_EVALUATED_RETRIEVER_NAMES

    def test_placeholders_are_independent_copies(self):
        depth_schema = LLMEvaluatedDepthRetriever.get_schema()
        depth_schema["properties"]["children"]["placeholder"][0]["params"][
            "merge_strategy"
        ] = "interleave"

        assert self._placeholder(LLMEvaluatedDepthRetriever, "children") == [
            default_hybrid_retriever()
        ]


def test_defaults_module_only_imports_the_standard_library():
    """The defaults module cannot create import cycles with component classes."""
    import DashAI.back.models.RAG.RAG_defaults as module

    tree = ast.parse(inspect.getsource(module))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert not any(name.startswith("DashAI") for name in imported)
