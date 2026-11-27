"""The query transformation reranker is a retriever, resolved from its schema.

``QueryTransformationValidationService.apply_defaults`` turns the reference a
session stores into the params the job hands to ``TransformationFactory``. A
reranker saved with only its own ``top_k`` must complete from the retriever's
schema, an absent reference takes the backend default (the multilingual
paraphrase semantic retriever), and an explicit ``null`` stays disabled.

The factory deliberately does not build the reranker: a retriever needs the
retrieval infrastructure, which the index setup supplies. The transformer
therefore carries ``reranker = None`` until that setup attaches it.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from DashAI.back.converters.hugging_face.text_embedding.sentence_transformer import (
    ParaphraseMultilingualMiniLML12V2Embedding,
)
from DashAI.back.core.schema_fields.defaults import resolve_component_defaults
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.prompts.transformation import (
    DefaultQueryDecompositionPrompt,
)
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_DEVICE,
    DEFAULT_TOP_K,
    PARAPHRASE_MULTILINGUAL_EMBEDDING_COMPONENT,
    default_query_reranker,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.transformation import (
    LLMQueryDecomposer,
    TransformationFactory,
)
from DashAI.back.models.RAG.transformation.decomposition import (
    DEFAULT_MAX_SUBQUERIES,
)
from DashAI.back.services.RAG.query_transformation_validation import (
    QueryTransformationValidationService,
)
from tests.back.RAG.test_RAG_transformation_smoke import (
    COMPONENTS as TRANSFORMATION_COMPONENTS,
)

#: Sentinel: the ``reranker`` key is absent from the stored transformer params.
_NOT_SET = object()

#: Top-k of the partial reranker reference saved by a non-default selection.
_PARTIAL_TOP_K = 5


def _registry() -> ComponentRegistry:
    """Return a registry with the transformers, the stub LLM and the retriever."""
    return ComponentRegistry(
        [
            *TRANSFORMATION_COMPONENTS,
            DenseEmbeddingRetriever,
            ParaphraseMultilingualMiniLML12V2Embedding,
        ]
    )


def _service() -> QueryTransformationValidationService:
    """Return the validator the API builds, with a no-op prompt checker."""
    return QueryTransformationValidationService(
        _registry(), lambda name, template: None
    )


def _decomposition_template() -> str:
    """Return the English template the API injects into the default prompt."""
    return DefaultQueryDecompositionPrompt.get_metadata()["templates"]["en"]


def _stored_params(reranker: Any = _NOT_SET) -> Dict[str, Any]:
    """Return the session parameters a save request carries."""
    params: Dict[str, Any] = {
        "prompt": {
            "component": "DefaultQueryDecompositionPrompt",
            "params": {"language": "en", "template": _decomposition_template()},
        },
        "llm_model": {"component": "TransformationStubLLM", "params": {}},
        "history_window": 1,
    }
    if reranker is not _NOT_SET:
        params["reranker"] = reranker
    return {
        "query_transformation": {"component": "LLMQueryDecomposer", "params": params}
    }


def _resolved(reranker: Any = _NOT_SET, is_new: bool = True) -> Dict[str, Any]:
    """Run the stored parameters through the validation service's defaults."""
    parameters = _stored_params(reranker)
    _service().apply_defaults(parameters, is_new=is_new)
    return parameters["query_transformation"]


def _transformer(reranker: Any = _NOT_SET) -> LLMQueryDecomposer:
    """Build the transformer the job builds from the resolved parameters."""
    reference = _resolved(reranker)
    return (
        TransformationFactory(_registry())
        .create(reference["component"], reference["params"])
        .model
    )


class TestRerankerDefaults:
    """The reranker retriever's own parameters resolve from its schema."""

    def test_partial_reference_is_completed_from_the_retriever_schema(self):
        reference = _resolved(
            {"component": "DenseEmbeddingRetriever", "params": {"top_k": 5}}
        )["params"]["reranker"]

        assert reference["component"] == "DenseEmbeddingRetriever"
        assert reference["params"]["top_k"] == _PARTIAL_TOP_K
        assert (
            reference["params"]["embedding_model"]["component"]
            == PARAPHRASE_MULTILINGUAL_EMBEDDING_COMPONENT
        )
        assert (
            reference["params"]["embedding_model"]["params"]["device"] == DEFAULT_DEVICE
        )

    def test_empty_params_resolve_to_the_retriever_schema_defaults(self):
        """Missing params take the reranker retriever's own schema defaults."""
        reference = _resolved({"component": "DenseEmbeddingRetriever", "params": {}})[
            "params"
        ]["reranker"]

        expected = resolve_component_defaults("DenseEmbeddingRetriever", _registry())
        assert reference["params"]["top_k"] == expected["top_k"]
        assert (
            reference["params"]["embedding_model"]["component"]
            == PARAPHRASE_MULTILINGUAL_EMBEDDING_COMPONENT
        )

    def test_absent_reference_stores_the_backend_default_recipe(self):
        """A new session omits the key: the server supplies its default."""
        reference = _resolved()["params"]["reranker"]

        assert reference["component"] == default_query_reranker()["component"]
        assert reference["params"]["top_k"] == DEFAULT_TOP_K
        assert (
            reference["params"]["embedding_model"]["component"]
            == PARAPHRASE_MULTILINGUAL_EMBEDDING_COMPONENT
        )

    def test_update_without_the_key_keeps_the_reranker_off(self):
        """Editing a stored session must not silently turn reranking on."""
        params = _resolved(is_new=False)["params"]

        assert params["reranker"] is None

    def test_update_with_an_explicit_reranker_keeps_it(self):
        reference = _resolved(
            {"component": "BM25Retriever", "params": {}}, is_new=False
        )

        assert reference["params"]["reranker"]["component"] == "BM25Retriever"

    def test_stored_session_without_the_key_runs_without_a_reranker(self):
        """The job path never applies defaults, so an absent key means off."""
        parameters = _stored_params()["query_transformation"]

        transformer = (
            TransformationFactory(_registry())
            .create(parameters["component"], parameters["params"])
            .model
        )

        assert transformer.reranker is None

    def test_explicit_null_stays_disabled(self):
        reference = _resolved(None)

        assert reference["params"]["reranker"] is None

    def test_non_dict_reference_is_left_for_the_schema_to_reject(self):
        reference = _resolved("DenseEmbeddingRetriever")["params"]["reranker"]

        assert reference == "DenseEmbeddingRetriever"


class TestFactoryLeavesTheRerankerToTheIndexSetup:
    """The factory never builds the retriever; the index setup attaches it."""

    def test_stored_reference_does_not_build_a_reranker_in_the_factory(self):
        model = _transformer(
            {"component": "DenseEmbeddingRetriever", "params": {"top_k": 5}}
        )

        assert model.reranker is None

    def test_default_reference_does_not_build_a_reranker_in_the_factory(self):
        assert _transformer().reranker is None


class TestStoredDecompositionCapThroughTheFactory:
    """A stored decomposition keeps its meaning of an omitted cap in the job."""

    @staticmethod
    def _build(is_new: bool = False, **extra: Any) -> LLMQueryDecomposer:
        parameters = _stored_params()
        parameters["query_transformation"]["params"].update(extra)
        _service().apply_defaults(parameters, is_new=is_new)
        reference = parameters["query_transformation"]
        return (
            TransformationFactory(_registry())
            .create(reference["component"], reference["params"])
            .model
        )

    @staticmethod
    def _build_stored_without_defaults(**extra: Any) -> LLMQueryDecomposer:
        """Build from the stored dict directly, as the job path does."""
        reference = _stored_params()["query_transformation"]
        reference["params"].update(extra)
        return (
            TransformationFactory(_registry())
            .create(reference["component"], reference["params"])
            .model
        )

    def test_a_stored_stage_without_the_key_is_uncapped(self):
        assert self._build_stored_without_defaults().max_subqueries is None

    def test_an_update_without_the_key_stays_uncapped(self):
        assert self._build(is_new=False).max_subqueries is None

    def test_an_explicit_null_is_uncapped(self):
        assert (
            self._build_stored_without_defaults(max_subqueries=None).max_subqueries
            is None
        )

    def test_an_explicit_integer_is_kept(self):
        assert self._build_stored_without_defaults(max_subqueries=2).max_subqueries == 2

    def test_a_new_session_starts_from_the_default(self):
        assert self._build(is_new=True).max_subqueries == DEFAULT_MAX_SUBQUERIES


class TestMalformedRerankerParams:
    """A reranker whose params is not a dict is rejected, not replaced."""

    def test_apply_defaults_rejects_non_dict_params(self):
        parameters = _stored_params({"component": "DenseEmbeddingRetriever"})
        parameters["query_transformation"]["params"]["reranker"]["params"] = "abc"

        with pytest.raises(ValueError, match="must be a dict"):
            _service().apply_defaults(parameters, is_new=True)
