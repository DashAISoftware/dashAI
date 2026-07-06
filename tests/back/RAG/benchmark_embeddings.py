"""Script simple para testear modelos de embedding uno por uno.
Corre sin pytest desde la raíz del repo:
    python tests/back/api/test_embedding_models.py [cpu|cuda]
"""
import gc
import importlib
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding import (
    ST_MODELS,
)

EMBEDDING_MAP = {
    "SentenceTransformerEmbedding": ("sentence_transformer_embedding", "SentenceTransformerEmbedding"),
    "BERTEmbedding": ("bert_embedding", "BERTEmbedding"),
    "DistilBERTEmbedding": ("distilbert_embedding", "DistilBERTEmbedding"),
    "RoBERTaEmbedding": ("roberta_embedding", "RoBERTaEmbedding"),
    "E5Embedding": ("e5_embedding", "E5Embedding"),
    "GemmaEmbedding": ("gemma_embedding", "GemmaEmbedding"),
    "InstructorEmbedding": ("instructor_embedding", "InstructorEmbedding"),
    "LaBSEmbedding": ("labse_embedding", "LaBSEmbedding"),
    "FastTextEmbedding": ("fasttext_embedding", "FastTextEmbedding"),
}

BASE = "DashAI.back.models.RAG.embeddings.dense"

TRACE_FILE = "benchmark_trace.txt"
if os.path.exists(TRACE_FILE):
    os.remove(TRACE_FILE)


def trace(msg):
    with open(TRACE_FILE, "a") as f:
        f.write(msg + "\n")
        f.flush()
        os.fsync(f.fileno())
    print(msg, flush=True)


def test_model(cfg):
    class_name = cfg["component_class"]
    model_name = cfg["model_name"]
    params = dict(cfg["params"])

    module_path, cls_name = EMBEDDING_MAP[class_name]
    module = importlib.import_module(f"{BASE}.{module_path}")
    EmbeddingClass = getattr(module, cls_name)

    if "model_name" not in params:
        params["model_name"] = model_name

    trace(f"\n=== {class_name}[{cfg['config_name']}] — {model_name} ===")
    trace("  Instantiating...")
    emb = EmbeddingClass(**params)
    trace("  Loading model...")
    emb.load()
    trace("  Encoding...")
    t0 = time.perf_counter()
    vec = emb.encode("Hello world, this is a test sentence for embedding.")
    elapsed = time.perf_counter() - t0

    assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
    assert vec.ndim == 1, f"Expected 1-D, got {vec.ndim}D"
    assert vec.shape[0] > 0, f"Expected positive dimension, got {vec.shape[0]}"
    assert np.isfinite(vec).all(), "Embedding contains non-finite values"

    trace(f"  OK ({elapsed:.2f}s) dim={vec.shape[0]}")
    del emb
    return True


def main():
    device = sys.argv[1] if len(sys.argv) > 1 else "cpu"
    trace(f"Device: {device}")
    trace(f"{'='*60}")

    # SentenceTransformer models (exclude >8B)
    large_st = {"microsoft/harrier-oss-v1-27b", "Qwen/Qwen3-Embedding-8B"}
    st_base = {"device": device, "normalize": True, "overflow_strategy": "truncate"}

    configs = []
    for model_name in sorted(ST_MODELS):
        if model_name in large_st:
            trace(f"  SKIP {model_name} (large model)")
            continue
        label = model_name.rstrip("/").split("/")[-1]
        configs.append({
            "component_class": "SentenceTransformerEmbedding",
            "model_name": model_name,
            "config_name": label,
            "params": dict(st_base),
        })

    # Additional models
    configs += [
        {"component_class": "BERTEmbedding", "model_name": "google-bert/bert-base-uncased", "config_name": "base", "params": {"device": device, "pooling_strategy": "mean", "overflow_strategy": "truncate"}},
        {"component_class": "BERTEmbedding", "model_name": "google-bert/bert-large-uncased", "config_name": "large", "params": {"device": device, "pooling_strategy": "mean", "overflow_strategy": "truncate"}},
        {"component_class": "DistilBERTEmbedding", "model_name": "distilbert/distilbert-base-uncased", "config_name": "base", "params": {"device": device, "pooling_strategy": "mean", "overflow_strategy": "truncate"}},
        {"component_class": "RoBERTaEmbedding", "model_name": "FacebookAI/roberta-base", "config_name": "base", "params": {"device": device, "pooling_strategy": "mean", "overflow_strategy": "truncate"}},
        {"component_class": "RoBERTaEmbedding", "model_name": "FacebookAI/xlm-roberta-base", "config_name": "xlm_base", "params": {"device": device, "pooling_strategy": "mean", "overflow_strategy": "truncate"}},
        {"component_class": "E5Embedding", "model_name": "intfloat/e5-small-v2", "config_name": "small", "params": {"device": device, "overflow_strategy": "truncate"}},
        {"component_class": "GemmaEmbedding", "model_name": "google/embeddinggemma-300m", "config_name": "default", "params": {"device": device, "overflow_strategy": "truncate", "task_type": "search_result"}},
        {"component_class": "InstructorEmbedding", "model_name": "hkunlp/instructor-base", "config_name": "base", "params": {"device": device, "instruction": "Represent the document for retrieval:"}},
        {"component_class": "LaBSEmbedding", "model_name": "sentence-transformers/LaBSE", "config_name": "default", "params": {"device": device, "overflow_strategy": "truncate"}},
        {"component_class": "FastTextEmbedding", "model_name": "facebook/fasttext-en-vectors", "config_name": "english", "params": {"pooling_strategy": "mean"}},
        {"component_class": "FastTextEmbedding", "model_name": "facebook/fasttext-es-vectors", "config_name": "spanish", "params": {"pooling_strategy": "mean"}},
    ]

    passed = 0
    failed = 0
    for cfg in configs:
        try:
            test_model(cfg)
            passed += 1
        except Exception as e:
            trace(f"  FAILED: {e}")
            failed += 1

        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    trace(f"\n{'='*60}")
    trace(f"Done: {passed} passed, {failed} failed")
    trace(f"Results in: {TRACE_FILE}")


if __name__ == "__main__":
    main()
