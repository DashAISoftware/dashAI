"""Retriever preset recipes resolved from the component registry."""

from typing import Any, Dict, List

_SEMANTIC_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_SEMANTIC_MODEL_SHORT = "paraphrase-multilingual-MiniLM-L12-v2"


def _resolve_defaults(component_name: str, registry) -> Dict[str, Any]:
    """Resolve a component's schema placeholders into a params dict.

    Recursively resolves nested component placeholders of the form
    ``{"component": ..., "params": {}}`` into ``{"component": ..., "params": {...}}``.
    Unregistered components resolve to an empty dict so a stale placeholder
    cannot crash the endpoint.
    """
    if component_name not in registry:
        return {}
    schema = registry[component_name]["schema"]
    params: Dict[str, Any] = {}
    for key, prop in schema.get("properties", {}).items():
        placeholder = prop.get("placeholder")
        if isinstance(placeholder, dict) and "component" in placeholder:
            params[key] = {
                "component": placeholder["component"],
                "params": {
                    **_resolve_defaults(placeholder["component"], registry),
                    **placeholder.get("params", {}),
                },
            }
        else:
            params[key] = placeholder
    return params


def _keyword_preset(top_k: int, registry) -> Dict[str, Any]:
    params = _resolve_defaults("BM25Retriever", registry)
    params["top_k"] = top_k
    return {
        "key": "keyword",
        "description": "BM25",
        "component": "BM25Retriever",
        "params": params,
    }


def _semantic_preset(top_k: int, registry) -> Dict[str, Any]:
    params = _resolve_defaults("DenseEmbeddingRetriever", registry)
    params["embedding_model"]["params"]["model_name"] = _SEMANTIC_MODEL_NAME
    params["top_k"] = top_k
    return {
        "key": "semantic",
        "description": _SEMANTIC_MODEL_SHORT,
        "component": "DenseEmbeddingRetriever",
        "params": params,
    }


def _hybrid_preset(top_k: int, registry) -> Dict[str, Any]:
    keyword_k = (top_k + 1) // 2  # ceil(top_k / 2)
    semantic_k = top_k // 2  # floor(top_k / 2)

    keyword_params = _resolve_defaults("BM25Retriever", registry)
    keyword_params["top_k"] = keyword_k

    semantic_params = _resolve_defaults("DenseEmbeddingRetriever", registry)
    semantic_params["embedding_model"]["params"]["model_name"] = _SEMANTIC_MODEL_NAME
    semantic_params["top_k"] = semantic_k

    return {
        "key": "hybrid",
        "description": f"BM25 + {_SEMANTIC_MODEL_SHORT}",
        "component": "ParallelRetriever",
        "params": {
            "merge_strategy": "round_robin",
            "children": [
                {"component": "BM25Retriever", "params": keyword_params},
                {"component": "DenseEmbeddingRetriever", "params": semantic_params},
            ],
        },
    }


def get_retriever_presets(top_k: int, registry) -> List[Dict[str, Any]]:
    """Return the three retriever preset recipes with ``top_k`` applied."""
    return [
        _keyword_preset(top_k, registry),
        _semantic_preset(top_k, registry),
        _hybrid_preset(top_k, registry),
    ]
