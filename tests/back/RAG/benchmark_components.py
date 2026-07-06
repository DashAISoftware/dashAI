"""Data-driven benchmarks for ALL RAG components with CSV/JSONL logging."""

import importlib
import json
import tempfile
from datetime import datetime

import numpy as np
import pytest

from DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding import (
    ST_MODELS,
)

from tests.back.RAG.benchmark_data import (
    _MockDocument,
    BENCHMARK_TEXT,
    TEST_CHUNKS,
    CHUNKING_DOCUMENT,
    MULTI_TURN_CONVERSATION,
    CORPUS_QA_PAIRS,
    REALISTIC_CORPUS,
    make_corpus_documents,
    build_test_chunks,
    LLM_MAP,
    EMBEDDING_MAP,
)

from tests.back.RAG.benchmark_utils import (
    BenchmarkLogger,
    BenchmarkResult,
    Timer,
    run_configs,
    read_benchmark_csv,
)

pytestmark = pytest.mark.slow


@pytest.fixture(scope="session")
def device(request) -> str:
    """Return the device string from --device CLI option."""
    return request.config.getoption("--device")


def _apply_device(configs: list[dict], device: str) -> list[dict]:
    """Deep-copy configs and inject ``device`` into every param dict.

    LLM configs receive the full descriptive device string (e.g.
    ``"GPU 0: NVIDIA GeForce RTX 4060 Laptop GPU - Compute Capability 8.9"``)
    because their schema (``LLAMA_DEVICE_ENUM``) uses that format.

    Embedding configs receive ``"cuda"`` when any GPU device is
    requested, since their schemas use a simple ``["cpu", "cuda"]`` enum.

    Configs whose component does not accept a ``device`` param
    (e.g. ``FastTextEmbedding``) are left unchanged.
    """
    import copy

    _EMBEDDING_CLASSES = {
        "SentenceTransformerEmbedding", "BERTEmbedding", "DistilBERTEmbedding",
        "RoBERTaEmbedding", "E5Embedding", "GemmaEmbedding",
        "InstructorEmbedding", "LaBSEmbedding",
    }

    updated = []
    for cfg in configs:
        cfg_copy = copy.deepcopy(cfg)
        if "device" not in cfg_copy.get("params", {}):
            updated.append(cfg_copy)
            continue

        comp_cls = cfg_copy["component_class"]
        if comp_cls in _EMBEDDING_CLASSES:
            # Embedding schemas use simple ["cpu", "cuda"] enum
            cfg_copy["params"]["device"] = "cuda" if device != "CPU" else "cpu"
        else:
            # LLM schemas accept the full descriptive device string
            cfg_copy["params"]["device"] = device

        updated.append(cfg_copy)
    return updated


# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURATION TABLES
# ═══════════════════════════════════════════════════════════════════════

LLM_CONFIGS = [
    # ── LlamaModel ──
    {
        "component_class": "LlamaModel",
        "model_name": "TheBloke/Llama-2-7B-Chat-GGUF",
        "config_name": "default",
        "params": {
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "LlamaModel",
        "model_name": "TheBloke/Llama-2-7B-Chat-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "quantization": "Q4_K_M",
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    {
        "component_class": "LlamaModel",
        "model_name": "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "LlamaModel",
        "model_name": "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "quantization": "Q4_K_M",
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    {
        "component_class": "LlamaModel",
        "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "quantization": "Q4_K_M",
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "LlamaModel",
        "model_name": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "quantization": "Q4_K_M",
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    # ── QwenModel ──
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "QwenModel",
        "model_name": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    # ── MistralModel ──
    {
        "component_class": "MistralModel",
        "model_name": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "MistralModel",
        "model_name": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    # ── SmolLMModel ──
    {
        "component_class": "SmolLMModel",
        "model_name": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "SmolLMModel",
        "model_name": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    {
        "component_class": "SmolLMModel",
        "model_name": "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        "config_name": "default",
        "params": {
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "SmolLMModel",
        "model_name": "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
    # ── Phi4MiniInstructModel ──
    {
        "component_class": "Phi4MiniInstructModel",
        "model_name": "unsloth/Phi-4-mini-instruct-GGUF",
        "config_name": "default",
        "params": {
            "quantization": "Phi-4-mini-instruct.Q8_0.gguf",
            "max_tokens": 100,
            "temperature": 0.7,
            "frequency_penalty": 0.1,
            "context_window": 512,
            "device": "CPU",
        },
    },
    {
        "component_class": "Phi4MiniInstructModel",
        "model_name": "unsloth/Phi-4-mini-instruct-GGUF",
        "config_name": "low_temp_fast",
        "params": {
            "quantization": "Phi-4-mini-instruct.Q8_0.gguf",
            "max_tokens": 30,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 256,
            "device": "CPU",
        },
    },
]

# ── SentenceTransformerEmbedding — models <= 4B ────────────────────
# Generated from ST_MODELS (see sentence_transformer_embedding.py).
# Models >=8B (8B, 27B) excluded from default benchmark — they require
# ~16GB+ GPU memory each.  Run them with `-k LargeEmbedding`.
_LARGE_ST_MODELS = {
    "microsoft/harrier-oss-v1-27b",          # 27B
    "Qwen/Qwen3-Embedding-8B",               # 8B  (BF16 → ~16GB)
}
_ST_BASE_PARAMS = {"device": "cpu", "normalize": True, "overflow_strategy": "truncate"}
ST_EMBEDDING_CONFIGS = []
LARGE_ST_EMBEDDING_CONFIGS = []
for model_name in sorted(ST_MODELS):
    label = model_name.rstrip("/").split("/")[-1]
    cfg = {
        "component_class": "SentenceTransformerEmbedding",
        "model_name": model_name,
        "config_name": label,
        "params": dict(_ST_BASE_PARAMS),
    }
    if model_name in _LARGE_ST_MODELS:
        LARGE_ST_EMBEDDING_CONFIGS.append(cfg)
    else:
        ST_EMBEDDING_CONFIGS.append(cfg)

EMBEDDING_CONFIGS = list(ST_EMBEDDING_CONFIGS) + [
    # ── BERTEmbedding ──
    {
        "component_class": "BERTEmbedding",
        "model_name": "google-bert/bert-base-uncased",
        "config_name": "base",
        "params": {"device": "cpu", "pooling_strategy": "mean", "overflow_strategy": "truncate"},
    },
    {
        "component_class": "BERTEmbedding",
        "model_name": "google-bert/bert-large-uncased",
        "config_name": "large",
        "params": {
            "device": "cpu",
            "pooling_strategy": "mean",
            "overflow_strategy": "truncate",
        },
    },
    # DistilBERTEmbedding
    {
        "component_class": "DistilBERTEmbedding",
        "model_name": "distilbert/distilbert-base-uncased",
        "config_name": "base",
        "params": {
            "device": "cpu",
            "pooling_strategy": "mean",
            "overflow_strategy": "truncate",
        },
    },
    # RoBERTaEmbedding
    {
        "component_class": "RoBERTaEmbedding",
        "model_name": "FacebookAI/roberta-base",
        "config_name": "base",
        "params": {
            "device": "cpu",
            "pooling_strategy": "mean",
            "overflow_strategy": "truncate",
        },
    },
    {
        "component_class": "RoBERTaEmbedding",
        "model_name": "FacebookAI/xlm-roberta-base",
        "config_name": "xlm_base",
        "params": {
            "device": "cpu",
            "pooling_strategy": "mean",
            "overflow_strategy": "truncate",
        },
    },
    # E5Embedding
    {
        "component_class": "E5Embedding",
        "model_name": "intfloat/e5-small-v2",
        "config_name": "small",
        "params": {"device": "cpu", "overflow_strategy": "truncate"},
    },
    # NOTE: intfloat/e5-mistral-7b-instruct moved to LARGE_EMBEDDING_CONFIGS (7B, ~14GB RAM)
    # GemmaEmbedding
    {
        "component_class": "GemmaEmbedding",
        "model_name": "google/embeddinggemma-300m",
        "config_name": "default",
        "params": {
            "device": "cpu",
            "overflow_strategy": "truncate",
            "task_type": "search_result",
        },
    },
    # InstructorEmbedding
    {
        "component_class": "InstructorEmbedding",
        "model_name": "hkunlp/instructor-base",
        "config_name": "base",
        "params": {
            "device": "cpu",
            "instruction": "Represent the document for retrieval:",
        },
    },
    # LaBSEmbedding
    {
        "component_class": "LaBSEmbedding",
        "model_name": "sentence-transformers/LaBSE",
        "config_name": "default",
        "params": {"device": "cpu", "overflow_strategy": "truncate"},
    },
    # FastTextEmbedding
    {
        "component_class": "FastTextEmbedding",
        "model_name": "facebook/fasttext-en-vectors",
        "config_name": "english",
        "params": {"pooling_strategy": "mean"},
    },
    {
        "component_class": "FastTextEmbedding",
        "model_name": "facebook/fasttext-es-vectors",
        "config_name": "spanish",
        "params": {"pooling_strategy": "mean"},
    },
    # OpenAIEmbedding
    {
        "component_class": "OpenAIEmbedding",
        "model_name": "text-embedding-3-small",
        "config_name": "default",
        "params": {"api_key": "", "model_name": "text-embedding-3-small"},
        "skip": "Requires OpenAI API key",
    },
]

# Large embedding models (>3B params) excluded from default benchmark
# because they require 8-16GB+ RAM each and cause swap/crash on laptops.
LARGE_EMBEDDING_CONFIGS = list(LARGE_ST_EMBEDDING_CONFIGS) + [
    {
        "component_class": "E5Embedding",
        "model_name": "intfloat/e5-mistral-7b-instruct",
        "config_name": "mistral_7b",
        "params": {"device": "cpu", "overflow_strategy": "truncate"},
    },
]

RETRIEVER_CONFIGS = [
    # BM25Retriever
    {
        "component_class": "BM25Retriever",
        "model_name": "BM25",
        "config_name": "default",
        "params": {
            "k1": 1.5,
            "b": 0.75,
            "delta": 0.0,
            "similarity_function": "cosine",
            "top_k": 5,
        },
        "vectorizer_class": "BM25VectorizerModel",
        "vectorizer_params": {
            "strip_accents": None,
            "lowercase": True,
            "stop_words": None,
            "max_df": 1.0,
            "min_df": 0.0,
            "max_features": None,
        },
    },
    {
        "component_class": "BM25Retriever",
        "model_name": "BM25",
        "config_name": "custom",
        "params": {
            "k1": 2.0,
            "b": 0.5,
            "delta": 0.5,
            "similarity_function": "euclidean",
            "top_k": 10,
        },
        "vectorizer_class": "BM25VectorizerModel",
        "vectorizer_params": {
            "strip_accents": None,
            "lowercase": True,
            "stop_words": None,
            "max_df": 1.0,
            "min_df": 0.0,
            "max_features": None,
        },
    },
    # TFIDFRetriever
    {
        "component_class": "TFIDFRetriever",
        "model_name": "TFIDF",
        "config_name": "default",
        "params": {"similarity_function": "cosine", "top_k": 5},
        "vectorizer_class": "TFIDFVectorizerModel",
        "vectorizer_params": {
            "strip_accents": "None",
            "lowercase": True,
            "analyzer": "word",
            "stop_words": [],
            "ngram_range": [1, 1],
            "max_df": 1.0,
            "min_df": 0.0,
            "max_features": 1000,
            "norm": "l2",
            "use_idf": True,
            "smooth_idf": True,
            "sublinear_tf": False,
        },
    },
    {
        "component_class": "TFIDFRetriever",
        "model_name": "TFIDF",
        "config_name": "custom",
        "params": {"similarity_function": "manhattan", "top_k": 15},
        "vectorizer_class": "TFIDFVectorizerModel",
        "vectorizer_params": {
            "strip_accents": "None",
            "lowercase": True,
            "analyzer": "word",
            "stop_words": [],
            "ngram_range": [1, 1],
            "max_df": 1.0,
            "min_df": 0.0,
            "max_features": 1000,
            "norm": "l2",
            "use_idf": True,
            "smooth_idf": True,
            "sublinear_tf": False,
        },
    },
]

DENSE_RETRIEVER_CONFIGS = [
    {
        "component_class": "DenseEmbeddingRetriever",
        "model_name": "all-MiniLM-L6-v2",
        "config_name": "cosine_k5",
        "params": {"similarity_metric": "cosine", "top_k": 5},
        "embedding_class": "SentenceTransformerEmbedding",
        "embedding_params": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "device": "cpu",
            "normalize": True,
            "overflow_strategy": "truncate",
        },
    },
    {
        "component_class": "DenseEmbeddingRetriever",
        "model_name": "all-MiniLM-L6-v2",
        "config_name": "euclidean_k10",
        "params": {"similarity_metric": "euclidean", "top_k": 10},
        "embedding_class": "SentenceTransformerEmbedding",
        "embedding_params": {
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "device": "cpu",
            "normalize": True,
            "overflow_strategy": "truncate",
        },
    },
]

COMPOSITE_RETRIEVER_CONFIGS = [
    {
        "component_class": "MMRRerankerRetriever",
        "model_name": "MMR",
        "config_name": "lambda05_factor3",
        "params": {"mmr_lambda": 0.5, "retrieval_factor": 3, "top_k": 5},
        "child_config": {
            "component_class": "DenseEmbeddingRetriever",
            "model_name": "all-MiniLM-L6-v2",
            "params": {"similarity_metric": "cosine", "top_k": 15},
            "embedding_class": "SentenceTransformerEmbedding",
            "embedding_params": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "device": "cpu",
                "normalize": True,
                "overflow_strategy": "truncate",
            },
        },
    },
    {
        "component_class": "MMRRerankerRetriever",
        "model_name": "MMR",
        "config_name": "lambda07_factor2",
        "params": {"mmr_lambda": 0.7, "retrieval_factor": 2, "top_k": 10},
        "child_config": {
            "component_class": "DenseEmbeddingRetriever",
            "model_name": "all-MiniLM-L6-v2",
            "params": {"similarity_metric": "cosine", "top_k": 20},
            "embedding_class": "SentenceTransformerEmbedding",
            "embedding_params": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "device": "cpu",
                "normalize": True,
                "overflow_strategy": "truncate",
            },
        },
    },
]

CHUNKER_CONFIGS = [
    {
        "component_class": "CharacterChunkModel",
        "model_name": "CharacterChunk",
        "config_name": "paragraph",
        "params": {"chunk_size": 500, "chunk_overlap": 50},
    },
    {
        "component_class": "CharacterChunkModel",
        "model_name": "CharacterChunk",
        "config_name": "page",
        "params": {"chunk_size": 2000, "chunk_overlap": 200},
    },
    {
        "component_class": "RecursiveCharacterChunkModel",
        "model_name": "RecursiveChar",
        "config_name": "default",
        "params": {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "separators": ["\n\n", "\n", ".", " ", ""],
        },
    },
    {
        "component_class": "RecursiveCharacterChunkModel",
        "model_name": "RecursiveChar",
        "config_name": "small",
        "params": {
            "chunk_size": 200,
            "chunk_overlap": 20,
            "separators": ["\n\n", "\n", ".", " ", ""],
        },
    },
    {
        "component_class": "TokenChunkModel",
        "model_name": "e5-mistral",
        "config_name": "default",
        "params": {
            "tokenizer_name": "intfloat/e5-mistral-7b-instruct",
            "chunk_size": 300,
            "chunk_overlap": 60,
        },
    },
    {
        "component_class": "TokenChunkModel",
        "model_name": "bert-spanish",
        "config_name": "default",
        "params": {
            "tokenizer_name": "dccuchile/bert-base-spanish-wwm-uncased",
            "chunk_size": 512,
            "chunk_overlap": 50,
        },
    },
]

PROMPT_CONFIGS = [
    {
        "component_class": "DefaultRAGGenerationPrompt",
        "model_name": "DefaultRAG",
        "config_name": "en",
        "params": {"language": "en", "template": ""},
    },
    {
        "component_class": "DefaultRAGGenerationPrompt",
        "model_name": "DefaultRAG",
        "config_name": "es",
        "params": {"language": "es", "template": ""},
    },
    {
        "component_class": "DefaultQnARAGGenerationPrompt",
        "model_name": "DefaultQnA",
        "config_name": "en",
        "params": {"language": "en", "template": ""},
    },
    {
        "component_class": "DefaultQnARAGGenerationPrompt",
        "model_name": "DefaultQnA",
        "config_name": "es",
        "params": {"language": "es", "template": ""},
    },
    {
        "component_class": "CustomRAGGenerationPrompt",
        "model_name": "Custom",
        "config_name": "qa_template",
        "params": {
            "template": "CONTEXT:\n{chunks}\n\nQUERY: {input}\n\nANSWER:"
        },
    },
    {
        "component_class": "CustomRAGGenerationPrompt",
        "model_name": "Custom",
        "config_name": "summarize_template",
        "params": {
            "template": "Summarize using:\n{chunks}\n\nQuestion: {input}\n\nSummary:"
        },
    },
]

# ═══════════════════════════════════════════════════════════════════════
#  Execution functions
# ═══════════════════════════════════════════════════════════════════════


def _execute_llm(cfg: dict):
    class_name = cfg["component_class"]
    model_name = cfg["model_name"]
    params = dict(cfg["params"])
    params["model_name"] = model_name

    module_path, cls_name = LLM_MAP[class_name]
    module = importlib.import_module(module_path)
    ModelClass = getattr(module, cls_name)

    print(f"  Creating LLM... {model_name}\n")
    with Timer() as load_timer:
        model = ModelClass(**params)

    with Timer() as exec_timer:
        result = model.generate(MULTI_TURN_CONVERSATION[:3])

    output = result[0].strip() if isinstance(result, list) and result else str(result).strip()
    assert len(output) > 0, "Empty output"

    del model
    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _execute_embedding(cfg: dict):
    class_name = cfg["component_class"]
    model_name = cfg["model_name"]
    params = dict(cfg["params"])

    module_path, cls_name = EMBEDDING_MAP[class_name]
    module = importlib.import_module(module_path)
    EmbeddingClass = getattr(module, cls_name)

    if "model_name" not in params:
        params["model_name"] = model_name

    import os
    with open("benchmark_trace.txt", "a") as _f:
        _f.write(f"LOADING {model_name}\n")
        _f.flush()
        os.fsync(_f.fileno())
    with Timer() as load_timer:
        emb = EmbeddingClass(**params)
        emb.load()

    with Timer() as exec_timer:
        # Use a realistic sentence from the medical corpus document
        test_sentence = "Metformin remains the first-line pharmacological therapy due to its efficacy and safety profile."
        vec = emb.encode(test_sentence)

    assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
    assert vec.ndim == 1, f"Expected 1-D, got {vec.ndim}D"
    assert vec.shape[0] > 0, f"Expected positive dimension, got {vec.shape[0]}"
    assert np.isfinite(vec).all(), "Embedding contains non-finite values"

    del emb
    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _execute_sparse_retriever(cfg: dict):
    from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence

    class_name = cfg["component_class"]
    vectorizer_class = cfg["vectorizer_class"]
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
    params = dict(cfg["params"])
    if class_name == "BM25Retriever":
        params["BM25Vectorizer"] = vec
    else:
        params["TFIDFVectorizer"] = vec

    with Timer() as load_timer:
        retriever = RetrieverClass(**params)
        retriever.inject_infra(
            env_rag_path=tempfile.mkdtemp(),
            chunks=TEST_CHUNKS,
            persistence=SparsePersistence(model_dir=None),
        )
        retriever.init_model()

    with Timer() as exec_timer:
        results = retriever.retrieve("capital of France")

    assert len(results) > 0, "No results returned"
    assert "Paris" in results[0].text, (
        f"Top result should be Paris, got: {results[0].text}"
    )

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _execute_dense_retriever(cfg: dict):
    from DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding import (
        SentenceTransformerEmbedding,
    )
    from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
        DenseEmbeddingRetriever,
    )
    from DashAI.back.models.RAG.retrievers.persistence import DensePersistence

    emb_cfg = cfg["embedding_params"]
    emb = SentenceTransformerEmbedding(**emb_cfg)

    with Timer() as load_timer:
        emb.load()
        retriever = DenseEmbeddingRetriever(**cfg["params"], embedding_model=emb)
        tmpdir = tempfile.mkdtemp()
        retriever.inject_infra(
            env_rag_path=tmpdir,
            chunks=TEST_CHUNKS,
            persistence=DensePersistence(
                matrix_dirs={0: tmpdir}, embedding_model_id=0
            ),
        )
        retriever.init_model()

    with Timer() as exec_timer:
        results = retriever.retrieve("capital of France")

    assert len(results) > 0, "No results returned"
    assert "Paris" in results[0].text, (
        f"Top result should be Paris, got: {results[0].text}"
    )

    del emb, retriever
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _execute_composite_retriever(cfg: dict):
    from DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding import (
        SentenceTransformerEmbedding,
    )
    from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
        MMRRerankerRetriever,
    )
    from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
        DenseEmbeddingRetriever,
    )
    from DashAI.back.models.RAG.retrievers.persistence import DensePersistence

    child_cfg = cfg["child_config"]
    emb_cfg = child_cfg["embedding_params"]
    emb = SentenceTransformerEmbedding(**emb_cfg)

    with Timer() as load_timer:
        emb.load()
        child = DenseEmbeddingRetriever(
            **child_cfg["params"], embedding_model=emb
        )
        tmpdir = tempfile.mkdtemp()
        child.inject_infra(
            env_rag_path=tmpdir,
            chunks=TEST_CHUNKS,
            persistence=DensePersistence(
                matrix_dirs={0: tmpdir}, embedding_model_id=0
            ),
        )
        child.init_model()
        mmr = MMRRerankerRetriever(**cfg["params"], children=[child])

    with Timer() as exec_timer:
        results = mmr.retrieve("capital of France")

    assert len(results) > 0, "No results returned"

    del emb, child, mmr
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _execute_chunker(cfg: dict):
    class_name = cfg["component_class"]
    params = dict(cfg["params"])

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
    module_path, cls_name = chunker_map[class_name]
    module = importlib.import_module(module_path)
    ChunkerClass = getattr(module, cls_name)

    doc = _MockDocument(0, CHUNKING_DOCUMENT)

    with Timer() as load_timer:
        chunker = ChunkerClass(**params, documents={0: doc})

    with Timer() as exec_timer:
        chunks = chunker.get_chunks()

    assert len(chunks) == 1, f"Expected 1 doc in chunks, got {len(chunks)}"
    assert len(chunks[0]) >= 1, "Expected at least 1 chunk"
    first = list(chunks[0].values())[0]
    assert len(first.text) > 0, "Chunk text should not be empty"

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


def _execute_prompt(cfg: dict):
    class_name = cfg["component_class"]
    params = dict(cfg["params"])

    prompt_map = {
        "DefaultRAGGenerationPrompt": (
            "DashAI.back.models.RAG.prompts.generation.default_rag_generation_prompt",
            "DefaultRAGGenerationPrompt",
        ),
        "DefaultQnARAGGenerationPrompt": (
            "DashAI.back.models.RAG.prompts.generation.default_qna_rag_generation_prompt",
            "DefaultQnARAGGenerationPrompt",
        ),
        "CustomRAGGenerationPrompt": (
            "DashAI.back.models.RAG.prompts.generation.custom_rag_generation_prompt",
            "CustomRAGGenerationPrompt",
        ),
    }
    module_path, cls_name = prompt_map[class_name]
    module = importlib.import_module(module_path)
    PromptClass = getattr(module, cls_name)

    with Timer() as load_timer:
        prompt = PromptClass(**params)

    with Timer() as exec_timer:
        # Use realistic RAG query and chunk from the medical corpus
        test_query = CORPUS_QA_PAIRS[0]["query"]
        test_chunk = "Metformin remains the first-line pharmacological therapy due to its efficacy, safety profile, low cost, and potential cardiovascular benefits."
        formatted = prompt.format(
            input=test_query,
            chunks=test_chunk,
        )

    assert "{input}" not in formatted, (
        f"Placeholder not replaced: {formatted[:100]}"
    )
    assert len(formatted) > 10, f"Formatted prompt too short: {formatted}"
    assert "Metformin" in formatted, (
        f"Expected Metformin in formatted prompt, got: {formatted[:100]}"
    )

    return "passed", exec_timer.elapsed, load_timer.elapsed, ""


# ═══════════════════════════════════════════════════════════════════════
#  Fixture
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def benchmark_logger():
    logger = BenchmarkLogger(output_dir="benchmark_results")
    yield logger
    print(logger.summary())


# ═══════════════════════════════════════════════════════════════════════
#  Test classes
# ═══════════════════════════════════════════════════════════════════════


class TestLLMBenchmark:
    LLM_CONFIGS = LLM_CONFIGS

    def test_llm_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.LLM_CONFIGS, device)
        run_configs(configs, "llm", _execute_llm, benchmark_logger)


class TestEmbeddingBenchmark:
    EMBEDDING_CONFIGS = EMBEDDING_CONFIGS

    def test_embedding_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.EMBEDDING_CONFIGS, device)
        run_configs(configs, "embedding", _execute_embedding, benchmark_logger)


    """ class TestLargeEmbeddingBenchmark:
        Benchmark large embedding models (>3B params) separately.

        These models require 8-16GB+ RAM each and are excluded from the
        default benchmark to avoid OOM/swap crashes on laptops.
        Run with: pytest tests/back/api/test_rag_benchmark.py -k LargeEmbedding
        LARGE_EMBEDDING_CONFIGS = LARGE_EMBEDDING_CONFIGS

        def test_large_embedding_benchmark(self, benchmark_logger, device):
            configs = _apply_device(self.LARGE_EMBEDDING_CONFIGS, device)
            run_configs(configs, "embedding", _execute_embedding, benchmark_logger)
    """

class TestRetrieverBenchmark:
    SPARSE_CONFIGS = RETRIEVER_CONFIGS
    DENSE_CONFIGS = DENSE_RETRIEVER_CONFIGS
    COMPOSITE_CONFIGS = COMPOSITE_RETRIEVER_CONFIGS

    def test_sparse_retriever_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.SPARSE_CONFIGS, device)
        run_configs(configs, "retriever", _execute_sparse_retriever, benchmark_logger)

    def test_dense_retriever_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.DENSE_CONFIGS, device)
        run_configs(configs, "retriever", _execute_dense_retriever, benchmark_logger)

    def test_composite_retriever_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.COMPOSITE_CONFIGS, device)
        run_configs(configs, "retriever", _execute_composite_retriever, benchmark_logger)


class TestChunkerBenchmark:
    CHUNKER_CONFIGS = CHUNKER_CONFIGS

    def test_chunker_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.CHUNKER_CONFIGS, device)
        run_configs(configs, "chunker", _execute_chunker, benchmark_logger)


class TestPromptBenchmark:
    PROMPT_CONFIGS = PROMPT_CONFIGS

    def test_prompt_benchmark(self, benchmark_logger, device):
        configs = _apply_device(self.PROMPT_CONFIGS, device)
        run_configs(configs, "prompt", _execute_prompt, benchmark_logger)


# ═══════════════════════════════════════════════════════════════════════
#  Standalone entry point (run with: python benchmark_components.py)
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-m", "slow", *sys.argv[1:]]))
