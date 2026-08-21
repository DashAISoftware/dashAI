"""RAG helper endpoints (retriever presets)."""

from fastapi import APIRouter, Depends, Query
from kink import di

from DashAI.back.services.RAG.retriever_presets import (
    get_retriever_presets as resolve_retriever_presets,
)

router = APIRouter()


@router.get("/retriever-presets")
def retriever_presets(
    top_k: int = Query(default=10, ge=1),
    component_registry=Depends(lambda: di["component_registry"]),
):
    """Return resolved retriever preset recipes for the given top_k.

    Parameters
    ----------
    top_k : int
        Number of chunks to configure (>= 1). Defaults to 10.
    component_registry : ComponentRegistry
        Registry used to resolve each preset's schema defaults.

    Returns
    -------
    list[dict]
        One dict per preset: ``{key, description, component, params}``.
    """
    return resolve_retriever_presets(top_k, component_registry)
