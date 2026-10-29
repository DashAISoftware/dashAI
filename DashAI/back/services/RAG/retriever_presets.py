"""Retriever preset recipes resolved from the component registry."""

from typing import Any, Dict, Final, List, Optional, Tuple

from DashAI.back.core.schema_fields.defaults import resolve_component_defaults
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.RAG_defaults import (
    DEFAULT_SEMANTIC_MODEL_NAME,
    DEFAULT_TOP_K,
    default_hybrid_retriever,
    default_keyword_retriever,
    default_semantic_retriever,
)
from DashAI.back.models.RAG.retrievers.retrieval_expansion import (
    ENABLE_FIELD,
    WINDOW_FIELD,
)

_SEMANTIC_MODEL_SHORT = DEFAULT_SEMANTIC_MODEL_NAME.rsplit("/", 1)[-1]

KEYWORD_PRESET_KEY = "keyword"
SEMANTIC_PRESET_KEY = "semantic"
HYBRID_PRESET_KEY = "hybrid"

#: Keys that never decide which preset a configuration belongs to. ``top_k`` is
#: a slider, and the retrieve-then-expand options are post-processing knobs, so
#: a legacy session (without them) and one that set them still match a preset.
_IGNORED_MATCH_KEYS: Final[Tuple[str, ...]] = ("top_k", ENABLE_FIELD, WINDOW_FIELD)

#: Preset a session gets when it does not choose one. Keyword retrieval is the
#: only paradigm that needs no model download, so it is the one default that can
#: never make session creation fail with a "must be downloaded first" conflict.
DEFAULT_PRESET_KEY = KEYWORD_PRESET_KEY

_KEYWORD_NAME = MultilingualString(
    en="Keyword",
    es="Palabras clave",
    pt="Palavra-chave",
    de="Stichwort",
    zh="关键词",
)
_SEMANTIC_NAME = MultilingualString(
    en="Semantic",
    es="Semántico",
    pt="Semântico",
    de="Semantisch",
    zh="语义",
)
_HYBRID_NAME = MultilingualString(
    en="Hybrid",
    es="Híbrido",
    pt="Híbrido",
    de="Hybrid",
    zh="混合",
)


def _keyword_preset(top_k: int, registry) -> Dict[str, Any]:
    """Build the keyword preset from the centralized BM25 default.

    Parameters
    ----------
    top_k : int
        Number of chunks the recipe selects.
    registry : ComponentRegistry
        Registry used to resolve any parameter the centralized recipe omits.

    Returns
    -------
    Dict[str, Any]
        The keyword preset recipe with its display metadata.
    """
    ref = default_keyword_retriever(top_k)
    params = {**resolve_component_defaults(ref["component"], registry), **ref["params"]}
    return {
        "key": KEYWORD_PRESET_KEY,
        "display_name": _KEYWORD_NAME,
        "description": "BM25",
        "component": ref["component"],
        "params": params,
    }


def _semantic_preset(top_k: int, registry) -> Dict[str, Any]:
    """Build the semantic preset from the centralized dense default.

    Parameters
    ----------
    top_k : int
        Number of chunks the recipe selects.
    registry : ComponentRegistry
        Registry used to resolve any parameter the centralized recipe omits.

    Returns
    -------
    Dict[str, Any]
        The semantic preset recipe with its display metadata.
    """
    ref = default_semantic_retriever(top_k)
    params = {**resolve_component_defaults(ref["component"], registry), **ref["params"]}
    return {
        "key": SEMANTIC_PRESET_KEY,
        "display_name": _SEMANTIC_NAME,
        "description": _SEMANTIC_MODEL_SHORT,
        "component": ref["component"],
        "params": params,
    }


def _hybrid_preset(top_k: int, registry) -> Dict[str, Any]:
    """Build the hybrid preset from the centralized parallel default.

    Parameters
    ----------
    top_k : int
        Total number of chunks the recipe returns. The hybrid factory splits it
        between the keyword and semantic children.
    registry : ComponentRegistry
        Registry used to resolve any parameter the centralized recipe omits.

    Returns
    -------
    Dict[str, Any]
        The hybrid preset recipe with its display metadata.
    """
    ref = default_hybrid_retriever(top_k)
    params = {**resolve_component_defaults(ref["component"], registry), **ref["params"]}
    return {
        "key": HYBRID_PRESET_KEY,
        "display_name": _HYBRID_NAME,
        "description": f"BM25 + {_SEMANTIC_MODEL_SHORT}",
        "component": ref["component"],
        "params": params,
    }


def get_retriever_presets(top_k: int, registry) -> List[Dict[str, Any]]:
    """Return the three retriever preset recipes with ``top_k`` applied.

    Parameters
    ----------
    top_k : int
        Number of chunks each recipe selects (or the total for the hybrid).
    registry : ComponentRegistry
        Registry used to resolve each component's schema defaults.

    Returns
    -------
    List[Dict[str, Any]]
        Keyword, semantic and hybrid recipes, in that order.
    """
    return [
        _keyword_preset(top_k, registry),
        _semantic_preset(top_k, registry),
        _hybrid_preset(top_k, registry),
    ]


def get_default_retriever(registry, top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
    """Return the ``{component, params}`` ref for the default preset.

    Parameters
    ----------
    registry : ComponentRegistry
        Registry used to resolve each component's schema defaults.
    top_k : int, optional
        Number of chunks the default recipe selects. Defaults to
        :data:`DashAI.back.models.RAG.RAG_defaults.DEFAULT_TOP_K`.

    Returns
    -------
    Dict[str, Any]
        The default retriever configuration.
    """
    recipe = next(
        preset
        for preset in get_retriever_presets(top_k, registry)
        if preset["key"] == DEFAULT_PRESET_KEY
    )
    return {"component": recipe["component"], "params": recipe["params"]}


def _strip_match_ignored_keys(value: Any) -> Any:
    """Drop the keys that never decide a preset match, at every level.

    A preset keeps its shape when the user only moves the Top-K slider or
    toggles retrieve-then-expand, so matching a stored config against a recipe
    has to ignore those keys at every level (composite presets split ``top_k``
    across their children, and expansion options may sit on the parent, on a
    child, or on neither in a legacy session).
    """
    if isinstance(value, dict):
        stripped: Dict[str, Any] = {}
        for key, item in value.items():
            if key in _IGNORED_MATCH_KEYS:
                continue
            stripped[key] = _strip_match_ignored_keys(item)
        return stripped
    if isinstance(value, list):
        stripped_list: List[Any] = []
        for item in value:
            stripped_list.append(_strip_match_ignored_keys(item))
        return stripped_list
    return value


def match_preset_key(component: str, params: Dict[str, Any], registry) -> Optional[str]:
    """Return the preset key a retriever config corresponds to, if any.

    ``top_k`` and the retrieve-then-expand options are ignored at every level,
    so a session created before those options existed still matches its preset,
    and so does the same recipe with them set to any value.

    Parameters
    ----------
    component : str
        Retriever class name.
    params : dict
        Retriever parameters.
    registry : ComponentRegistry
        Registry used to resolve each candidate recipe.

    Returns
    -------
    str | None
        The matching preset key, or ``None`` for a custom configuration.
    """
    stripped = _strip_match_ignored_keys(params)
    for preset in get_retriever_presets(DEFAULT_TOP_K, registry):
        if preset["component"] != component:
            continue
        if _strip_match_ignored_keys(preset["params"]) == stripped:
            return preset["key"]
    return None


def effective_top_k(component: str, params: Dict[str, Any]) -> int:
    """Return how many chunks a retriever config actually returns.

    A composite retriever's own ``top_k`` (when it has one) bounds the result;
    otherwise the children's values add up.
    """
    if "top_k" in params and isinstance(params["top_k"], int):
        return params["top_k"]
    if "max_chunks" in params and isinstance(params["max_chunks"], int):
        return params["max_chunks"]
    children = params.get("children")
    if isinstance(children, list) and children:
        return sum(
            effective_top_k(child.get("component", ""), child.get("params", {}) or {})
            for child in children
            if isinstance(child, dict)
        )
    return 0


def _expansion_factor(params: Dict[str, Any]) -> int:
    """Return the multiplier retrieve-then-expand adds to a chunk count.

    Parameters
    ----------
    params : Dict[str, Any]
        Retriever parameters of one configuration level.

    Returns
    -------
    int
        The window size when expansion is enabled with a real ``int`` window
        above one, otherwise ``1``.
    """
    if params.get(ENABLE_FIELD) is not True:
        return 1
    window = params.get(WINDOW_FIELD)
    if isinstance(window, bool) or not isinstance(window, int):
        return 1
    return window if window > 1 else 1


def _max_expansion_factor(params: Dict[str, Any]) -> int:
    """Return the largest expansion factor over a retriever and its children.

    A parent that caps its own output still returns units produced deeper in the
    tree, so its cap has to be priced with the widest window below it. A
    cross-encoder selecting five units out of an expanded child's output carries
    that child's window per unit, not one chunk: estimating five chunks there
    would under-count the budget by the child's window.

    Parameters
    ----------
    params : Dict[str, Any]
        Retriever parameters of one configuration level.

    Returns
    -------
    int
        The maximum ``_expansion_factor`` over this node and its descendants.
    """
    factor = _expansion_factor(params)
    children = params.get("children")
    if not isinstance(children, list):
        return factor
    for child in children:
        if not isinstance(child, dict):
            continue
        child_factor = _max_expansion_factor(child.get("params", {}) or {})
        if child_factor > factor:
            factor = child_factor
    return factor


def _own_chunk_cap(params: Dict[str, Any]) -> Optional[int]:
    """Return the cap a retriever declares for its own output, if any.

    ``top_k`` caps the chunks a reranker or composite returns and ``max_chunks``
    caps an LLM-evaluated pool. A node declaring neither is bounded by its
    children instead.

    Parameters
    ----------
    params : Dict[str, Any]
        Retriever parameters of one configuration level.

    Returns
    -------
    int | None
        The declared cap, or ``None`` when the node has none.
    """
    for key in ("top_k", "max_chunks"):
        if key not in params:
            continue
        value = params[key]
        if isinstance(value, int):
            return value
    return None


def effective_chunk_count(component: str, params: Dict[str, Any]) -> int:
    """Return how many chunks a retriever config actually puts in the prompt.

    A retriever's own ``top_k`` (or an LLM-evaluated retriever's ``max_chunks``)
    caps how many units it returns, but each unit may itself be an expanded
    window produced below it, so a capped parent is priced with the widest
    window in its subtree. A composite without a cap adds up its children's
    expansion-aware counts and applies only its own factor, because each child
    already accounted for its own window (applying the subtree maximum again
    would double-count). A plain leaf costs its expansion-adjusted ``top_k``.

    Parameters
    ----------
    component : str
        Retriever class name.
    params : Dict[str, Any]
        Retriever parameters, possibly holding ``children`` refs.

    Returns
    -------
    int
        The context cost of this retriever in chunks, expansion included.
    """
    cap = _own_chunk_cap(params)
    if cap is not None:
        return cap * _max_expansion_factor(params)
    children = params.get("children")
    if isinstance(children, list) and children:
        base = 0
        for child in children:
            if not isinstance(child, dict):
                continue
            base += effective_chunk_count(
                child.get("component", ""), child.get("params", {}) or {}
            )
        return base * _expansion_factor(params)
    return effective_top_k(component, params) * _expansion_factor(params)
