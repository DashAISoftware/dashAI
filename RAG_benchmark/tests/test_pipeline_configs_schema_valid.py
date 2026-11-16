"""Schema validation and structure tests for the pipeline benchmark configs.

Every component reference declared in ``PIPELINE_REGISTRY`` must carry
all fields required by the component's ``SCHEMA``. Session creation only
validates the top-level ``{component, params}`` shape, so this test
reproduces the failures the RAG job hits when ``SetupService``
instantiates each component.

The structure tests pin the value-level shape of the publication 5 pipelines
(cross-encoder re-ranking over a sparse or dense candidate pool plus an LLM
query-transformation stage), which the component-name assertions cannot see:
a wrong ``top_k`` or a swapped child retriever keeps the same component set.
"""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from DashAI.back.app import create_app
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from RAG_benchmark.app.pipelines import base as pipelines_base
from RAG_benchmark.app.pipelines.configs import PIPELINE_REGISTRY

# The exact component names each pipeline config must declare. Any change
# to the config structure (or a walker regression) fails loudly here.
# The API-key-bearing converter (``OpenAIEmbedding``) is validated with the
# empty placeholder key the config carries when ``OPENAI_API_KEY`` is unset:
# schema validation must not require a real credential.
EXPECTED_COMPONENTS: dict[str, set[str]] = {
    "pub1": {
        "RecursiveCharacterChunkModel",
        "DenseEmbeddingRetriever",
        "OpenAIEmbedding",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
    },
    "pub2": {
        "CharacterChunkModel",
        "MMRRerankerRetriever",
        "DenseEmbeddingRetriever",
        "AllMiniLML6V2Embedding",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
    },
    "pub3": {
        "RecursiveCharacterChunkModel",
        "DenseEmbeddingRetriever",
        "OpenAIEmbedding",
        "Llama32_1BInstruct",
        "DefaultRAGGenerationPrompt",
    },
    "pub4a": {
        "TokenChunkModel",
        "DenseEmbeddingRetriever",
        "E5MistralGGUFEmbedding",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
    },
    "pub4b": {
        "TokenChunkModel",
        "BM25Retriever",
        "BagOfWordsConverter",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
    },
    "pub5a": {
        "TokenChunkModel",
        "SentenceTransformerCrossEncoderRetriever",
        "BM25Retriever",
        "BagOfWordsConverter",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
        "LLMQueryRewriter",
        "DefaultQueryRewritingPrompt",
        "Qwen25_7BInstruct",
    },
    "pub5b": {
        "TokenChunkModel",
        "SentenceTransformerCrossEncoderRetriever",
        "DenseEmbeddingRetriever",
        "AllMiniLML6V2Embedding",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
        "LLMQueryDecomposer",
        "DefaultQueryDecompositionPrompt",
        "Qwen25_7BInstruct",
    },
    "pub5c": {
        "TokenChunkModel",
        "SentenceTransformerCrossEncoderRetriever",
        "TFIDFRetriever",
        "TFIDFConverter",
        "Llama32_3BInstruct",
        "DefaultRAGGenerationPrompt",
        "LLMQueryExpander",
        "DefaultQueryExpansionPrompt",
        "Qwen25_7BInstruct",
    },
}

#: Cross-encoder checkpoint every publication 5 pipeline re-ranks with.
PUB5_CROSS_ENCODER_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

#: Candidate pool the initial retriever returns before re-ranking (K1).
PUB5_RETRIEVER_TOP_K = 10

#: Chunks the cross-encoder hands to the generator (K2).
PUB5_RERANK_TOP_K = 5

#: Query-transformation LLM shared by the publication 5 pipelines.
PUB5_TRANSFORMATION_LLM = "Qwen25_7BInstruct"

#: Generation component shared by the publication 5 pipelines.
PUB5_GENERATION_MODEL = "Llama32_3BInstruct"

#: Initial retriever, transformer and transformation prompt each pub5 pipeline
#: must declare: ``(child component, transformer, prompt)``.
PUB5_EXPECTED_STRUCTURE: dict[str, tuple[str, str, str]] = {
    "pub5a": ("BM25Retriever", "LLMQueryRewriter", "DefaultQueryRewritingPrompt"),
    "pub5b": (
        "DenseEmbeddingRetriever",
        "LLMQueryDecomposer",
        "DefaultQueryDecompositionPrompt",
    ),
    "pub5c": ("TFIDFRetriever", "LLMQueryExpander", "DefaultQueryExpansionPrompt"),
}


def iter_component_refs(node: Any) -> Iterator[dict[str, Any]]:
    """Yield every component reference dict found in *node*.

    A component ref is any dict containing a ``"component"`` key
    (``"params"`` is required by the callers). Recurses into nested dicts
    and lists, e.g. ``MMRRerankerRetriever`` ``params.children`` is a
    list of component refs.
    """
    if isinstance(node, dict):
        if "component" in node:
            yield node
        for value in node.values():
            yield from iter_component_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_component_refs(item)


@pytest.fixture(scope="module")
def registry(tmp_path_factory) -> Iterator[ComponentRegistry]:
    """Build the FastAPI app and yield its component registry."""
    tmp = tmp_path_factory.mktemp("rag_cfg_test")
    app = create_app(local_path=tmp, logging_level="ERROR")
    reg = app.container["component_registry"]
    yield reg
    app.container["engine"].dispose()


@pytest.mark.parametrize("name", list(PIPELINE_REGISTRY))
def test_pipeline_config_schemas_valid(name: str, registry: ComponentRegistry) -> None:
    """Every component ref in a pipeline config validates against its schema."""
    config_fn = PIPELINE_REGISTRY[name]["config_fn"]
    config = config_fn([1])
    refs = list(iter_component_refs(config["parameters"]))
    found = {ref["component"] for ref in refs}
    assert found == EXPECTED_COMPONENTS[name], (
        f"Component refs mismatch for {name}: expected "
        f"{EXPECTED_COMPONENTS[name]}, got {found}"
    )
    for ref in refs:
        assert "params" in ref, f"Malformed component ref missing 'params': {ref}"
        cls = registry[ref["component"]]["class"]
        if cls.SCHEMA is not None:
            unknown = sorted(set(ref["params"]) - set(cls.SCHEMA.model_fields))
            assert not unknown, (
                f"{name}: {ref['component']} declares unknown params {unknown}"
            )
            cls.SCHEMA(**ref["params"])


def _pipeline_parameters(name: str) -> dict[str, Any]:
    """Return the session parameters of the pipeline registered under *name*."""
    return PIPELINE_REGISTRY[name]["config_fn"]([1])["parameters"]


@pytest.mark.parametrize("name", list(PUB5_EXPECTED_STRUCTURE))
def test_pub5_pipeline_declares_the_reranking_structure(name: str) -> None:
    """Pub 5a/5b/5c re-rank a K1=10 candidate pool down to K2=5 chunks."""
    parameters = _pipeline_parameters(name)
    child_component, transformer, prompt_component = PUB5_EXPECTED_STRUCTURE[name]

    chunking = parameters["chunking_model"]
    assert chunking["component"] == "TokenChunkModel"
    assert chunking["params"]["chunk_size"] == 300
    assert chunking["params"]["chunk_overlap"] == 60

    retriever = parameters["retriever_model"]
    assert retriever["component"] == "SentenceTransformerCrossEncoderRetriever"
    assert retriever["params"]["model_name"] == PUB5_CROSS_ENCODER_MODEL
    assert retriever["params"]["top_k"] == PUB5_RERANK_TOP_K

    children = retriever["params"]["children"]
    assert len(children) == 1, f"{name} must re-rank exactly one candidate pool"
    assert children[0]["component"] == child_component
    assert children[0]["params"]["top_k"] == PUB5_RETRIEVER_TOP_K

    transformation = parameters["query_transformation"]
    assert transformation["component"] == transformer
    assert transformation["params"]["prompt"]["component"] == prompt_component
    assert transformation["params"]["llm_model"]["component"] == PUB5_TRANSFORMATION_LLM
    assert parameters["generation_model"]["component"] == PUB5_GENERATION_MODEL


def test_pub5b_dense_child_embeds_with_minilm() -> None:
    """The decomposition pipeline retrieves candidates through MiniLM."""
    child = _pipeline_parameters("pub5b")["retriever_model"]["params"]["children"][0]

    assert child["params"]["embedding_model"]["component"] == "AllMiniLML6V2Embedding"


def test_pub5c_tfidf_child_uses_the_tfidf_converter() -> None:
    """The expansion pipeline retrieves candidates through the TF-IDF vectorizer."""
    child = _pipeline_parameters("pub5c")["retriever_model"]["params"]["children"][0]

    assert child["params"]["vectorizer"]["component"] == "TFIDFConverter"


# ---------------------------------------------------------------------------
# Cross-encoder pre-flight
# ---------------------------------------------------------------------------
# The cross-encoder checkpoint is a retriever *parameter*, so the generic
# downloadable-component gate cannot see it. These tests pin the explicit gate
# the pub5 pipelines depend on.


def test_cross_encoder_preflight_detects_only_the_pub5_checkpoint() -> None:
    """Only the publication 5 pipelines declare a cross-encoder checkpoint."""
    for name in PIPELINE_REGISTRY:
        parameters = _pipeline_parameters(name)
        models = sorted(set(pipelines_base._iter_cross_encoder_models(parameters)))
        if name.startswith("pub5"):
            assert models == [PUB5_CROSS_ENCODER_MODEL], name
        else:
            assert models == [], name


def test_cross_encoder_preflight_accepts_a_cached_checkpoint(monkeypatch) -> None:
    """A cached checkpoint makes the pre-flight a no-op."""
    import huggingface_hub

    calls = []
    monkeypatch.setattr(
        huggingface_hub,
        "snapshot_download",
        lambda **kwargs: calls.append(kwargs) or "C:/cache/cross-encoder",
    )

    pipelines_base.ensure_cross_encoder_available(
        PUB5_CROSS_ENCODER_MODEL, download=False
    )

    assert calls == [{"repo_id": PUB5_CROSS_ENCODER_MODEL, "local_files_only": True}]


def test_cross_encoder_preflight_fails_fast_without_download(monkeypatch) -> None:
    """A missing checkpoint raises under --no-download, naming the model."""
    import huggingface_hub

    def fake_snapshot(**kwargs):
        raise RuntimeError("missing")

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot)

    with pytest.raises(RuntimeError) as excinfo:
        pipelines_base.ensure_cross_encoder_available(
            PUB5_CROSS_ENCODER_MODEL, download=False
        )

    message = str(excinfo.value)
    assert PUB5_CROSS_ENCODER_MODEL in message
    assert "--no-download" in message


def test_cross_encoder_preflight_downloads_before_loading(monkeypatch) -> None:
    """With downloads enabled, the missing checkpoint is fetched up front."""
    import huggingface_hub

    calls = []

    def fake_snapshot(**kwargs):
        calls.append(kwargs)
        if kwargs.get("local_files_only"):
            raise RuntimeError("missing")
        return "C:/cache/cross-encoder"

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot)

    pipelines_base.ensure_cross_encoder_available(
        PUB5_CROSS_ENCODER_MODEL, download=True
    )

    assert calls == [
        {"repo_id": PUB5_CROSS_ENCODER_MODEL, "local_files_only": True},
        {"repo_id": PUB5_CROSS_ENCODER_MODEL},
    ]
