"""Standalone RAG pipeline benchmark — run with: python run_rag_benchmark.py

No pytest, no conftest, no initial_components.  Direct leaf-module imports only.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from datetime import datetime

from tests.back.RAG.benchmark_utils import BenchmarkResult, Timer, BenchmarkLogger
from tests.back.RAG.benchmark_data import (
    _MockDocument,
    make_corpus_documents,
    CORPUS_QA_PAIRS,
    LLM_MAP,
    EMBEDDING_MAP,
    CHUNKER_MAP,
    PROMPT_MAP,
)
# ---------------------------------------------------------------------------
#  Pipeline configs  (5 thesis-publication configurations)
# ---------------------------------------------------------------------------

PIPELINE_CONFIGS = [
    {
        "config_name": "Pub 1 - Medical Fitness",
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
    {
        "config_name": "Pub 2 - EHR Summarization (MMR composite)",
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
                "retriever_params": {"similarity_metric": "cosine", "top_k": 30},
                "embedding_component": "SentenceTransformerEmbedding",
                "embedding_params": {
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "normalize": True,
                    "device": "cpu",
                    "overflow_strategy": "truncate",
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
    {
        "config_name": "Pub 3 - Case Study",
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
            "overflow_strategy": "truncate",
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
    {
        "config_name": "Pub 4a - RAGChecker Dense (E5)",
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
    {
        "config_name": "Pub 4b - RAGChecker Sparse (BM25)",
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
#  Pipeline execution
# ---------------------------------------------------------------------------


def _build_sparse_retriever(cfg, chunks, tmpdirs):
    from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence
    from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import (
        BM25Retriever,
        BM25VectorizerModel,
    )
    from DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever import (
        TFIDFRetriever,
        TFIDFVectorizerModel,
    )

    class_name = cfg["retriever_component"]
    vec_class = cfg["vectorizer_component"]
    vec_params = cfg["vectorizer_params"]

    if class_name == "BM25Retriever":
        VecCls = BM25VectorizerModel
        RetCls = BM25Retriever
        vec_key = "BM25Vectorizer"
    elif class_name == "TFIDFRetriever":
        VecCls = TFIDFVectorizerModel
        RetCls = TFIDFRetriever
        vec_key = "TFIDFVectorizer"
    else:
        raise ValueError(f"Unknown sparse retriever: {class_name}")

    vec = VecCls(**vec_params)
    params = dict(cfg["retriever_params"])
    params[vec_key] = vec

    tmpdir = tempfile.mkdtemp()
    tmpdirs.append(tmpdir)
    retriever = RetCls(**params)
    retriever.inject_infra(
        env_rag_path=tmpdir,
        chunks=chunks,
        persistence=SparsePersistence(model_dir=None),
    )
    retriever.init_model()
    return retriever


def _build_dense_retriever(cfg, chunks, tmpdirs):
    from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
        DenseEmbeddingRetriever,
    )
    from DashAI.back.models.RAG.retrievers.persistence import DensePersistence

    # Dynamically import embedding class
    emb_name = cfg["embedding_component"]
    emb_module = {
        "SentenceTransformerEmbedding": (
            "DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding",
            "SentenceTransformerEmbedding",
        ),
        "BERTEmbedding": (
            "DashAI.back.models.RAG.embeddings.dense.bert_embedding",
            "BERTEmbedding",
        ),
        "E5Embedding": (
            "DashAI.back.models.RAG.embeddings.dense.e5_embedding",
            "E5Embedding",
        ),
        "GemmaEmbedding": (
            "DashAI.back.models.RAG.embeddings.dense.gemma_embedding",
            "GemmaEmbedding",
        ),
    }[emb_name]

    import importlib

    mod = importlib.import_module(emb_module[0])
    EmbCls = getattr(mod, emb_module[1])

    emb_params = dict(cfg["embedding_params"])
    emb = EmbCls(**emb_params)
    emb.load()

    tmpdir = tempfile.mkdtemp()
    tmpdirs.append(tmpdir)
    retriever = DenseEmbeddingRetriever(**cfg["retriever_params"], embedding_model=emb)
    retriever.inject_infra(
        env_rag_path=tmpdir,
        chunks=chunks,
        persistence=DensePersistence(matrix_dirs={doc_id: tmpdir for doc_id in chunks.keys()}, embedding_model_id=0),
    )
    retriever.init_model()
    return retriever


def _build_composite_retriever(cfg, chunks, tmpdirs):
    from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
        MMRRerankerRetriever,
    )

    children = []
    for child_cfg in cfg["child_retrievers"]:
        if child_cfg["retriever_type"] == "dense":
            child = _build_dense_retriever(child_cfg, chunks, tmpdirs)
        else:
            raise ValueError(f"Unsupported child type: {child_cfg['retriever_type']}")
        children.append(child)

    return MMRRerankerRetriever(**cfg["retriever_params"], children=children)


def _execute_pipeline(cfg: dict) -> tuple[str, float, float, str]:
    """Run full RAG pipeline: chunk → retrieve → prompt → generate."""
    import importlib

    query = cfg["test_query"]
    expected_hint = cfg["expected_answer_hint"]

    # ── 1. Chunking ──
    chunker_map = {
        "CharacterChunkModel": (
            "DashAI.back.models.RAG.chunking_models.character_chunk_model",
            "CharacterChunkModel",
        ),
        "RecursiveCharacterChunkModel": (
            "DashAI.back.models.RAG.chunking_models.recursive_character_chunk_model",
            "RecursiveCharacterChunkModel",
        ),
        "TokenChunkModel": (
            "DashAI.back.models.RAG.chunking_models.token_chunk_model",
            "TokenChunkModel",
        ),
    }
    ch_mod, ch_cls = chunker_map[cfg["chunking_component"]]
    ChunkerClass = getattr(importlib.import_module(ch_mod), ch_cls)

    doc_ids = cfg.get("doc_ids", [0])
    corpus_docs = make_corpus_documents()
    docs = {doc_id: corpus_docs[doc_id] for doc_id in doc_ids}

    with Timer() as chunk_load:
        chunker = ChunkerClass(**cfg["chunking_params"], documents=docs)
    with Timer() as chunk_exec:
        chunks = chunker.get_chunks()

    assert len(chunks) == len(docs), f"Expected {len(docs)} doc(s), got {len(chunks)}"
    assert all(len(c) >= 1 for c in chunks.values()), "Expected >= 1 chunk per doc"

    # ── 2. Retrieval ──
    tmpdirs: list[str] = []
    rtype = cfg["retriever_type"]

    with Timer() as ret_load:
        if rtype == "sparse":
            retriever = _build_sparse_retriever(cfg, chunks, tmpdirs)
        elif rtype == "dense":
            retriever = _build_dense_retriever(cfg, chunks, tmpdirs)
        elif rtype == "composite":
            retriever = _build_composite_retriever(cfg, chunks, tmpdirs)
        else:
            raise ValueError(f"Unknown retriever_type: {rtype}")

    with Timer() as ret_exec:
        results = retriever.retrieve(query)

    assert len(results) > 0, "No results"
    assert expected_hint.lower() in results[0].text.lower(), (
        f"Expected '{expected_hint}' in top result, got: {results[0].text}"
    )

    # ── 3. Prompt ──
    prompt_map = {
        "DefaultRAGGenerationPrompt": (
            "DashAI.back.models.RAG.prompts.generation.default_rag_generation_prompt",
            "DefaultRAGGenerationPrompt",
        ),
        "DefaultQnARAGGenerationPrompt": (
            "DashAI.back.models.RAG.prompts.generation.default_qna_rag_generation_prompt",
            "DefaultQnARAGGenerationPrompt",
        ),
    }
    pr_mod, pr_cls = prompt_map[cfg["prompt_component"]]
    PromptClass = getattr(importlib.import_module(pr_mod), pr_cls)

    with Timer() as prompt_load:
        prompt_model = PromptClass(**cfg["prompt_params"])

    chunks_text = "\n\n".join(c.text for c in results)
    with Timer() as prompt_exec:
        prompt_text = prompt_model.format(input=query, chunks=chunks_text)

    assert "{input}" not in prompt_text
    assert len(prompt_text) > 10

    # ── 4. LLM Generation ──
    llm_map = {
        "LlamaModel": (
            "DashAI.back.models.hugging_face.llama_model",
            "LlamaModel",
        ),
        "MistralModel": (
            "DashAI.back.models.hugging_face.mistral_model",
            "MistralModel",
        ),
        "QwenModel": (
            "DashAI.back.models.hugging_face.qwen_model",
            "QwenModel",
        ),
    }
    ll_mod, ll_cls = llm_map[cfg["llm_component"]]
    ModelClass = getattr(importlib.import_module(ll_mod), ll_cls)

    with Timer() as llm_load:
        model = ModelClass(**cfg["llm_params"])

    with Timer() as llm_exec:
        result = model.generate([{"role": "user", "content": prompt_text}])

    output = result[0].strip()
    assert len(output) > 0, "Empty LLM output"

    # ── Cleanup ──
    del chunker, retriever, model
    for d in tmpdirs:
        shutil.rmtree(d, ignore_errors=True)

    total_wall = sum(
        t.elapsed
        for t in (
            chunk_load,
            chunk_exec,
            ret_load,
            ret_exec,
            prompt_load,
            prompt_exec,
            llm_load,
            llm_exec,
        )
    )
    total_load = sum(
        t.elapsed for t in (chunk_load, ret_load, prompt_load, llm_load)
    )

    return "passed", total_wall, total_load, ""


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------


def main():
    import sys

    # -- Parse CLI args
    config_filter = None
    if len(sys.argv) > 1:
        config_filter = sys.argv[1].lower()

    logger = BenchmarkLogger(output_dir="benchmark_results")

    configs_to_run = []
    for cfg in PIPELINE_CONFIGS:
        if (
            config_filter is None
            or config_filter in cfg["config_name"].lower()
            or config_filter in cfg["params"].get("retriever", "").lower()
        ):
            configs_to_run.append(cfg)

    if not configs_to_run:
        print(f"No configs match filter '{config_filter}'. Available:")
        for c in PIPELINE_CONFIGS:
            print(f"  - {c['config_name']}")
        return

    print(f"Running {len(configs_to_run)} pipeline config(s)...\n")

    for cfg in configs_to_run:
        ts = datetime.now().isoformat()
        print(f"  [{ts}] {cfg['config_name']} ... ", end="", flush=True)
        try:
            status, wall, load_t, err = _execute_pipeline(cfg)
            icon = "PASS" if status == "passed" else "FAIL"
            print(f"{icon}  wall={wall:.1f}s  load={load_t:.1f}s", flush=True)
        except Exception as exc:
            status, wall, load_t, err = "failed", 0.0, 0.0, str(exc)
            print(f"FAIL  {err[:120]}", flush=True)
            import traceback

            traceback.print_exc()

        result = BenchmarkResult(
            component_type="pipeline",
            component_class=cfg.get("component_class", ""),
            model_name=cfg.get("model_name", ""),
            config_name=cfg.get("config_name", "default"),
            params=cfg.get("params", {}),
            status=status,
            time_seconds=wall,
            first_load_time=load_t,
            error_message=err or "",
            timestamp=ts,
        )
        logger.log(result)

    print(logger.summary())


if __name__ == "__main__":
    main()
