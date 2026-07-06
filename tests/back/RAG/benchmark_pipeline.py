"""Benchmark for full RAG pipeline execution with thesis publication configurations.

Each test constructs and runs the complete RAG pipeline chain:
document -> chunking -> retrieval -> prompt formatting -> LLM generation.
"""

import copy
import importlib
import shutil
import tempfile

import pytest

from tests.back.RAG.benchmark_data import (
    _MockDocument,
    make_corpus_documents,
    CORPUS_QA_PAIRS,
    LLM_MAP,
    EMBEDDING_MAP,
    CHUNKER_MAP,
    PROMPT_MAP,
)

from tests.back.RAG.benchmark_utils import (
    BenchmarkLogger,
    Timer,
    run_configs,
)

pytestmark = pytest.mark.slow


def _apply_device(configs: list[dict], device: str) -> list[dict]:
    """Deep-copy configs and inject ``device`` into pipeline params.

    LLM params (``llm_params``) receive the full descriptive device string;
    embedding params (``embedding_params``) receive ``"cuda"`` or ``"cpu"``.
    Children of composite retrievers are handled recursively.
    """

    updated = []
    for cfg in configs:
        cfg_copy = copy.deepcopy(cfg)

        llm_params = cfg_copy.get("llm_params", {})
        if "device" in llm_params:
            llm_params["device"] = device

        emb_params = cfg_copy.get("embedding_params", {})
        if "device" in emb_params:
            emb_params["device"] = "cuda" if device != "CPU" else "cpu"

        child_retrievers = cfg_copy.get("child_retrievers", [])
        for child in child_retrievers:
            child_emb = child.get("embedding_params", {})
            if "device" in child_emb:
                child_emb["device"] = "cuda" if device != "CPU" else "cpu"

        updated.append(cfg_copy)
    return updated

# ---------------------------------------------------------------------------
#  Pipeline configs — 5 thesis publication configurations
# ---------------------------------------------------------------------------

PIPELINE_CONFIGS = [
    # Pub 1 — Medical Fitness
    {
        "config_name": "Pub 1 - Medical Fitness",
        "publication": (
            "Retrieval augmented generation for 10 large language models and its "
            "generalizability in assessing medical fitness"
        ),
        "substitutions": (
            "Original: OpenAIEmbedding (ada-002). "
            "Using SentenceTransformerEmbedding (all-MiniLM-L6-v2) as local substitute."
        ),
        "component_class": "RAGPipeline",
        "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "params": {
            "chunker": "RecursiveCharacterChunkModel",
            "retriever": "DenseEmbeddingRetriever",
            "embedding": "SentenceTransformerEmbedding",
            "prompt": "DefaultRAGGenerationPrompt",
            "llm": "LlamaModel",
        },
        "doc_ids": [0],
        "test_query": CORPUS_QA_PAIRS[0]["query"],
        "expected_answer_hint": CORPUS_QA_PAIRS[0]["hint"],
        "chunking_component": "RecursiveCharacterChunkModel",
        "chunking_params": {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "separators": ["\n\n", "\n", ".", " ", ""],
        },
        "retriever_type": "dense",
        "retriever_component": "DenseEmbeddingRetriever",
        "retriever_params": {"similarity_metric": "cosine", "top_k": 5},
        "embedding_component": "SentenceTransformerEmbedding",
        "embedding_params": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "normalize": True,
            "device": "cpu",
        },
        "prompt_component": "DefaultRAGGenerationPrompt",
        "prompt_params": {"language": "en", "template": ""},
        "llm_component": "LlamaModel",
        "llm_params": {
            "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 512,
            "device": "CPU",
        },
    },
    # Pub 2 — EHR Summarization (composite retriever)
    {
        "config_name": "Pub 2 - EHR Summarization",
        "publication": (
            "Applying generative AI with retrieval augmented generation to summarize "
            "and extract key clinical information from electronic health records"
        ),
        "substitutions": "None -- all components run locally.",
        "component_class": "RAGPipeline",
        "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "params": {
            "chunker": "CharacterChunkModel",
            "retriever": "MMRRerankerRetriever",
            "embedding": "SentenceTransformerEmbedding",
            "prompt": "DefaultRAGGenerationPrompt",
            "llm": "LlamaModel",
        },
        "doc_ids": [1],
        "test_query": CORPUS_QA_PAIRS[1]["query"],
        "expected_answer_hint": CORPUS_QA_PAIRS[1]["hint"],
        "chunking_component": "CharacterChunkModel",
        "chunking_params": {"chunk_size": 600, "chunk_overlap": 40},
        "retriever_type": "composite",
        "retriever_component": "MMRRerankerRetriever",
        "retriever_params": {
            "mmr_lambda": 0.5,
            "retrieval_factor": 3,
            "top_k": 10,
        },
        "child_retrievers": [
            {
                "retriever_type": "dense",
                "retriever_component": "DenseEmbeddingRetriever",
                "retriever_params": {
                    "similarity_metric": "cosine",
                    "top_k": 30,
                },
                "embedding_component": "SentenceTransformerEmbedding",
                "embedding_params": {
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "normalize": True,
                    "device": "cpu",
                },
            }
        ],
        "prompt_component": "DefaultRAGGenerationPrompt",
        "prompt_params": {"language": "en", "template": ""},
        "llm_component": "LlamaModel",
        "llm_params": {
            "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 512,
            "device": "CPU",
        },
    },
    # Pub 3 — Case Study
    {
        "config_name": "Pub 3 - Case Study",
        "publication": (
            "Development and Testing of Retrieval Augmented Generation in Large "
            "Language Models -- A Case Study Report"
        ),
        "substitutions": (
            "Original: OpenAIEmbedding (ada-002). "
            "Using SentenceTransformerEmbedding (all-MiniLM-L6-v2) as local substitute."
        ),
        "component_class": "RAGPipeline",
        "model_name": "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "params": {
            "chunker": "RecursiveCharacterChunkModel",
            "retriever": "DenseEmbeddingRetriever",
            "embedding": "SentenceTransformerEmbedding",
            "prompt": "DefaultRAGGenerationPrompt",
            "llm": "LlamaModel",
        },
        "doc_ids": [3],
        "test_query": CORPUS_QA_PAIRS[2]["query"],
        "expected_answer_hint": CORPUS_QA_PAIRS[2]["hint"],
        "chunking_component": "RecursiveCharacterChunkModel",
        "chunking_params": {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "separators": ["\n\n", "\n", ".", " ", ""],
        },
        "retriever_type": "dense",
        "retriever_component": "DenseEmbeddingRetriever",
        "retriever_params": {"similarity_metric": "cosine", "top_k": 5},
        "embedding_component": "SentenceTransformerEmbedding",
        "embedding_params": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "normalize": True,
            "device": "cpu",
        },
        "prompt_component": "DefaultRAGGenerationPrompt",
        "prompt_params": {"language": "en", "template": ""},
        "llm_component": "LlamaModel",
        "llm_params": {
            "model_name": "bartowski/Llama-3.2-1B-Instruct-GGUF",
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 512,
            "device": "CPU",
        },
    },
    # Pub 4a — RAGChecker Dense
    {
        "config_name": "Pub 4a - RAGChecker Dense",
        "publication": (
            "RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented "
            "Generation (dense variant)"
        ),
        "substitutions": (
            "Original: E5Embedding (e5-mistral-7b-instruct, 7B, ~14GB). "
            "Using E5Embedding (e5-small-v2, 118M) as local substitute."
        ),
        "component_class": "RAGPipeline",
        "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "params": {
            "chunker": "TokenChunkModel",
            "retriever": "DenseEmbeddingRetriever",
            "embedding": "E5Embedding",
            "prompt": "DefaultRAGGenerationPrompt",
            "llm": "LlamaModel",
        },
        "doc_ids": [6],
        "test_query": CORPUS_QA_PAIRS[3]["query"],
        "expected_answer_hint": CORPUS_QA_PAIRS[3]["hint"],
        "chunking_component": "TokenChunkModel",
        "chunking_params": {
            "tokenizer_name": "intfloat/e5-mistral-7b-instruct",
            "chunk_size": 300,
            "chunk_overlap": 60,
        },
        "retriever_type": "dense",
        "retriever_component": "DenseEmbeddingRetriever",
        "retriever_params": {"similarity_metric": "cosine", "top_k": 5},
        "embedding_component": "E5Embedding",
        "embedding_params": {
            "model_name": "intfloat/e5-small-v2",
            "device": "cpu",
            "overflow_strategy": "truncate",
        },
        "prompt_component": "DefaultRAGGenerationPrompt",
        "prompt_params": {"language": "en", "template": ""},
        "llm_component": "LlamaModel",
        "llm_params": {
            "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 512,
            "device": "CPU",
        },
    },
    # Pub 4b — RAGChecker Sparse
    {
        "config_name": "Pub 4b - RAGChecker Sparse",
        "publication": (
            "RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented "
            "Generation (sparse variant)"
        ),
        "substitutions": "None -- all components run locally.",
        "component_class": "RAGPipeline",
        "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "params": {
            "chunker": "TokenChunkModel",
            "retriever": "BM25Retriever",
            "prompt": "DefaultRAGGenerationPrompt",
            "llm": "LlamaModel",
        },
        "doc_ids": [7],
        "test_query": CORPUS_QA_PAIRS[4]["query"],
        "expected_answer_hint": CORPUS_QA_PAIRS[4]["hint"],
        "chunking_component": "TokenChunkModel",
        "chunking_params": {
            "tokenizer_name": "intfloat/e5-mistral-7b-instruct",
            "chunk_size": 300,
            "chunk_overlap": 60,
        },
        "retriever_type": "sparse",
        "retriever_component": "BM25Retriever",
        "retriever_params": {
            "k1": 1.5,
            "b": 0.75,
            "delta": 0.0,
            "similarity_function": "cosine",
            "top_k": 5,
        },
        "vectorizer_component": "BM25VectorizerModel",
        "vectorizer_params": {
            "strip_accents": None,
            "lowercase": True,
            "stop_words": None,
            "max_df": 1.0,
            "min_df": 0.0,
            "max_features": None,
        },
        "prompt_component": "DefaultRAGGenerationPrompt",
        "prompt_params": {"language": "en", "template": ""},
        "llm_component": "LlamaModel",
        "llm_params": {
            "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 512,
            "device": "CPU",
        },
    },
]

# ---------------------------------------------------------------------------
#  Execution function
# ---------------------------------------------------------------------------


def _execute_pipeline(cfg: dict):
    """Execute a full RAG pipeline from config dict.

    Pipeline stages:
        1. Chunking       -- build chunker from config, chunk test doc text
        2. Retrieval      -- build retriever (sparse/dense/composite), retrieve
        3. Prompt         -- build prompt model, format with query + chunks
        4. LLM generation -- build LLM model, generate response

    Returns
    -------
    tuple[str, float, float, str]
        ``(status, total_wall_time, total_load_time, error_message)``.
    """

    query = cfg["test_query"]
    expected_hint = cfg["expected_answer_hint"]

    # ── Step 1: Chunking ──────────────────────────────────────────────

    chunker_cls_name = cfg["chunking_component"]
    chunker_params = dict(cfg["chunking_params"])
    module_path, cls_name = CHUNKER_MAP[chunker_cls_name]
    module = importlib.import_module(module_path)
    ChunkerClass = getattr(module, cls_name)

    doc_ids = cfg.get("doc_ids", [0])
    corpus_docs = make_corpus_documents()
    docs = {doc_id: corpus_docs[doc_id] for doc_id in doc_ids}

    with Timer() as chunk_load_timer:
        chunker = ChunkerClass(**chunker_params, documents=docs)

    with Timer() as chunk_exec_timer:
        chunks = chunker.get_chunks()

    assert len(chunks) == len(docs), f"Expected {len(docs)} doc(s) in chunks, got {len(chunks)}"
    assert all(len(c) >= 1 for c in chunks.values()), "Expected at least 1 chunk per document"
    chunk_load_time = chunk_load_timer.elapsed
    chunk_exec_time = chunk_exec_timer.elapsed

    # ── Step 2: Retrieval ─────────────────────────────────────────────

    retriever_type = cfg["retriever_type"]
    _tmpdirs: list[str] = []

    with Timer() as ret_load_timer:
        if retriever_type == "sparse":
            retriever = _build_sparse_retriever(cfg, chunks, _tmpdirs)
        elif retriever_type == "dense":
            retriever = _build_dense_retriever(cfg, chunks, _tmpdirs)
        elif retriever_type == "composite":
            retriever = _build_composite_retriever(cfg, chunks, _tmpdirs)
        else:
            raise ValueError(f"Unknown retriever_type: {retriever_type}")
    retriever_load_time = ret_load_timer.elapsed

    with Timer() as ret_exec_timer:
        results = retriever.retrieve(query)

    assert len(results) > 0, "No retrieval results returned"
    assert expected_hint in results[0].text, (
        f"Top result should contain {expected_hint}, "
        f"got: {results[0].text}"
    )
    retriever_time = ret_exec_timer.elapsed

    retrieved_chunks = results

    # ── Step 3: Prompt ───────────────────────────────────────────────

    prompt_cls_name = cfg["prompt_component"]
    prompt_params = dict(cfg["prompt_params"])
    module_path, cls_name = PROMPT_MAP[prompt_cls_name]
    module = importlib.import_module(module_path)
    PromptClass = getattr(module, cls_name)

    with Timer() as prompt_load_timer:
        prompt_model = PromptClass(**prompt_params)

    chunks_text = "\n\n".join(c.text for c in retrieved_chunks)
    with Timer() as prompt_exec_timer:
        prompt_text = prompt_model.format(input=query, chunks=chunks_text)

    assert "{input}" not in prompt_text, "Placeholder {{input}} not replaced"
    assert len(prompt_text) > 10, f"Formatted prompt too short: {prompt_text}"
    prompt_time = prompt_exec_timer.elapsed
    prompt_load_time = prompt_load_timer.elapsed

    # ── Step 4: LLM Generation ────────────────────────────────────────

    llm_cls_name = cfg["llm_component"]
    llm_params = dict(cfg["llm_params"])
    module_path, cls_name = LLM_MAP[llm_cls_name]
    module = importlib.import_module(module_path)
    ModelClass = getattr(module, cls_name)

    with Timer() as llm_load_timer:
        model = ModelClass(**llm_params)

    with Timer() as llm_exec_timer:
        result = model.generate(
            [{"role": "user", "content": prompt_text}]
        )

    output = result[0].strip()
    assert len(output) > 0, "Empty LLM output"
    llm_time = llm_exec_timer.elapsed
    llm_load_time = llm_load_timer.elapsed

    total_wall_time = (
        chunk_load_time + chunk_exec_time
        + retriever_load_time + retriever_time
        + prompt_load_time + prompt_time
        + llm_load_time + llm_time
    )
    total_load_time = (
        chunk_load_time + retriever_load_time
        + prompt_load_time + llm_load_time
    )

    del chunker, retriever, model
    for d in _tmpdirs:
        shutil.rmtree(d, ignore_errors=True)
    return "passed", total_wall_time, total_load_time, ""


def _build_sparse_retriever(cfg, chunks, _tmpdirs=None):
    """Build a sparse retriever (BM25Retriever / TFIDFRetriever) with infra.

    Parameters
    ----------
    cfg : dict
        Pipeline config with ``retriever_component``, ``retriever_params``,
        ``vectorizer_component``, ``vectorizer_params``.
    chunks : dict
        Chunks dict in ``{doc_id: {chunk_id: Chunk}}`` format.
    _tmpdirs : list or None
        Optional list to append created temporary directory paths for cleanup.

    Returns
    -------
    BM25Retriever | TFIDFRetriever
        Initialised retriever ready for ``.retrieve()``.
    """
    from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence

    class_name = cfg["retriever_component"]
    vectorizer_class = cfg["vectorizer_component"]
    vectorizer_params = cfg["vectorizer_params"]

    retriever_map = {
        "BM25Retriever": (
            "DashAI.back.models.RAG.retrievers.sparse.bm25_retriever",
            "BM25Retriever",
            "BM25VectorizerModel",
        ),
        "TFIDFRetriever": (
            "DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever",
            "TFIDFRetriever",
            "TFIDFVectorizerModel",
        ),
    }
    module_path, cls_name, vec_cls_name = retriever_map[class_name]
    module = importlib.import_module(module_path)
    RetrieverClass = getattr(module, cls_name)
    VectorizerClass = getattr(module, vec_cls_name)

    vec = VectorizerClass(**vectorizer_params)
    params = dict(cfg["retriever_params"])
    if class_name == "BM25Retriever":
        params["BM25Vectorizer"] = vec
    else:
        params["TFIDFVectorizer"] = vec

    tmpdir = tempfile.mkdtemp()
    if _tmpdirs is not None:
        _tmpdirs.append(tmpdir)
    retriever = RetrieverClass(**params)
    retriever.inject_infra(
        env_rag_path=tmpdir,
        chunks=chunks,
        persistence=SparsePersistence(model_dir=None),
    )
    retriever.init_model()
    return retriever


def _build_dense_retriever(cfg, chunks, _tmpdirs=None):
    """Build a DenseEmbeddingRetriever with embedding model and infra.

    Parameters
    ----------
    cfg : dict
        Pipeline config with ``retriever_params``, ``embedding_component``,
        ``embedding_params``.
    chunks : dict
        Chunks dict in ``{doc_id: {chunk_id: Chunk}}`` format.
    _tmpdirs : list or None
        Optional list to append created temporary directory paths for cleanup.

    Returns
    -------
    DenseEmbeddingRetriever
        Initialised retriever ready for ``.retrieve()``.
    """
    from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
        DenseEmbeddingRetriever,
    )
    from DashAI.back.models.RAG.retrievers.persistence import DensePersistence

    emb_cls_name = cfg["embedding_component"]
    emb_params = dict(cfg["embedding_params"])
    module_path, cls_name = EMBEDDING_MAP[emb_cls_name]
    module = importlib.import_module(module_path)
    EmbeddingClass = getattr(module, cls_name)

    emb = EmbeddingClass(**emb_params)
    emb.load()

    tmpdir = tempfile.mkdtemp()
    if _tmpdirs is not None:
        _tmpdirs.append(tmpdir)
    retriever = DenseEmbeddingRetriever(
        **cfg["retriever_params"], embedding_model=emb
    )
    retriever.inject_infra(
        env_rag_path=tmpdir,
        chunks=chunks,
        persistence=DensePersistence(
            matrix_dirs={doc_id: tmpdir for doc_id in chunks.keys()}, embedding_model_id=0
        ),
    )
    retriever.init_model()
    return retriever


def _build_composite_retriever(cfg, chunks, _tmpdirs=None):
    """Build a composite (e.g. MMRReranker) retriever with child dense retriever.

    Parameters
    ----------
    cfg : dict
        Pipeline config with ``child_retrievers``, ``retriever_params``.
    chunks : dict
        Chunks dict in ``{doc_id: {chunk_id: Chunk}}`` format.
    _tmpdirs : list or None
        Optional list to append created temporary directory paths for cleanup.

    Returns
    -------
    MMRRerankerRetriever
        Initialised composite retriever ready for ``.retrieve()``.
    """
    from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
        MMRRerankerRetriever,
    )

    children = []
    for child_cfg in cfg["child_retrievers"]:
        if child_cfg["retriever_type"] == "dense":
            child = _build_dense_retriever(child_cfg, chunks, _tmpdirs)
        else:
            raise ValueError(
                f"Unsupported child retriever type: {child_cfg['retriever_type']}"
            )
        children.append(child)

    retriever = MMRRerankerRetriever(
        **cfg["retriever_params"], children=children
    )
    return retriever


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def device(request) -> str:
    """Return the device string from --device CLI option."""
    return request.config.getoption("--device")


@pytest.fixture(scope="module")
def benchmark_logger():
    """Yield a ``BenchmarkLogger`` and print a summary after all tests."""
    logger = BenchmarkLogger(output_dir="benchmark_results")
    yield logger
    print(logger.summary())


# ---------------------------------------------------------------------------
#  Test class
# ---------------------------------------------------------------------------


class TestPipelineBenchmark:
    """Execute full RAG pipelines from thesis publications."""

    PIPELINE_CONFIGS = PIPELINE_CONFIGS

    def test_pipeline_benchmark(self, benchmark_logger, device):
        """Run all 5 publication pipeline configs through ``_execute_pipeline``.

        Results are logged to ``benchmark_results/benchmark_<timestamp>.csv``
        and ``.jsonl`` via ``BenchmarkLogger``.
        """
        configs = _apply_device(self.PIPELINE_CONFIGS, device)
        run_configs(configs, "pipeline", _execute_pipeline, benchmark_logger)


# ═══════════════════════════════════════════════════════════════════════
#  Standalone entry point (run with: python benchmark_pipeline.py)
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-m", "slow", *sys.argv[1:]]))