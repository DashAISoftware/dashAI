"""Human-readable view of a RAG session's configuration.

A session stores raw component class names (``CharacterChunkModel``,
``ParallelRetriever``) and snake_case parameter keys. Rendering those directly
is what made the creation form and the session view speak two different
vocabularies. This service resolves the stored configuration into the same
friendly vocabulary the pickers use — display names, preset labels, parameter
labels and a precomputed context budget — so the frontend never has to keep a
translation table of its own.

Everything it returns is read-only and derived; nothing here mutates a session.
"""

import logging
from typing import Any, Dict, List, Optional

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import GenerativeSession
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.exceptions import RAGPipelineConfigError
from DashAI.back.models.RAG.RAG_constants import (
    COMPONENT_KEY,
    MAX_SUBQUERIES_KEY,
    PARAMS_KEY,
    QUERY_COUNT_KEYS,
    RAG_PARAM_CHUNKING_MODEL,
    RAG_PARAM_GENERATION_MODEL,
    RAG_PARAM_PROMPT,
    RAG_PARAM_QUERY_TRANSFORMATION,
    RAG_PARAM_RETRIEVER_MODEL,
    RERANKER_KEY,
)
from DashAI.back.services.RAG import chunking_presets, retriever_presets
from DashAI.back.services.RAG.prompt_service import PromptService
from DashAI.back.services.RAG.session_defaults_service import (
    RAG_CONTEXT_WINDOW,
    RAG_MAX_TOKENS,
)

log = logging.getLogger(__name__)

#: Characters per token, for turning prompt text into a token estimate.
CHARS_PER_TOKEN = 4

#: Queries the retrieval stage runs when no stage multiplies them.
SINGLE_QUERY = 1


def _is_query_count(value: Any) -> bool:
    """Return whether ``value`` is a usable query or chunk count.

    Parameters
    ----------
    value : Any
        A candidate count. ``bool`` is rejected even though it is an ``int``
        subclass, because ``True`` is never a chunk count.

    Returns
    -------
    bool
        ``True`` for an ``int`` of at least one that is not a ``bool``.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _stage_params(transformation: Dict[str, Any]) -> Dict[str, Any]:
    """Return the ``params`` of a stored query transformation stage.

    Unlike the minimal reference of a retriever, a transformer stage always
    carries its ``params`` (a prompt and a model are required).

    Parameters
    ----------
    transformation : Dict[str, Any]
        The stored transformation reference.

    Returns
    -------
    Dict[str, Any]
        The stage's parameters.

    Raises
    ------
    RAGPipelineConfigError
        If ``params`` is missing or not a dict.
    """
    params = transformation.get(PARAMS_KEY)
    if not isinstance(params, dict):
        raise RAGPipelineConfigError(
            f"Stored query transformation '{transformation.get(COMPONENT_KEY)}' "
            "has no 'params' dict."
        )
    return params


def _reference_params(reference: Dict[str, Any], what: str) -> Dict[str, Any]:
    """Return a stored component reference's ``params``.

    A reference without ``params`` is the minimal ``{"component": name}`` the
    form stores for a component chosen by name alone, so it has no parameters.

    Parameters
    ----------
    reference : Dict[str, Any]
        A stored component reference.
    what : str
        What the reference is, for the error message.

    Returns
    -------
    Dict[str, Any]
        The parameters, empty for the minimal reference.

    Raises
    ------
    RAGPipelineConfigError
        If ``params`` is present and not a dict.
    """
    params = reference.get(PARAMS_KEY)
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise RAGPipelineConfigError(
            f"Stored 'params' of {what} is not a dict, got {type(params).__name__}."
        )
    return params


_SECTION_NAMES = {
    RAG_PARAM_CHUNKING_MODEL: MultilingualString(
        en="Chunking",
        es="Fragmentación",
        pt="Fragmentação",
        de="Chunking",
        zh="切分",
    ),
    RAG_PARAM_RETRIEVER_MODEL: MultilingualString(
        en="Retrieval",
        es="Recuperación",
        pt="Recuperação",
        de="Abruf",
        zh="检索",
    ),
    RAG_PARAM_PROMPT: MultilingualString(
        en="Prompt",
        es="Prompt",
        pt="Prompt",
        de="Prompt",
        zh="提示词",
    ),
    RAG_PARAM_GENERATION_MODEL: MultilingualString(
        en="Model",
        es="Modelo",
        pt="Modelo",
        de="Modell",
        zh="模型",
    ),
    RAG_PARAM_QUERY_TRANSFORMATION: MultilingualString(
        en="Query Transformation",
        es="Transformación de consultas",
        pt="Transformação de consultas",
        de="Abfragetransformation",
        zh="查询转换",
    ),
}


class SessionConfigurationService:
    """Resolves a stored RAG configuration into labels the UI can render."""

    def __init__(self, db, registry: ComponentRegistry):
        """Initialise the service.

        Parameters
        ----------
        db : Session
            SQLAlchemy session used to load the generative session.
        registry : ComponentRegistry
            Registry providing display names, descriptions and schemas.
        """
        self._db = db
        self._registry = registry

    # ── Public API ────────────────────────────────────────────────────

    def get_configuration(self, session_id: int) -> Dict[str, Any]:
        """Return the resolved configuration of a RAG session.

        Parameters
        ----------
        session_id : int
            The generative session to describe.

        Returns
        -------
        dict
            One entry per RAG component plus ``context_budget``. Multilingual
            values are returned as :class:`MultilingualString`; the caller
            localizes them.

        Raises
        ------
        ValueError
            If the session does not exist.
        """
        session = self._db.get(GenerativeSession, session_id)
        if session is None:
            raise ValueError(f"Generative session {session_id} does not exist.")

        parameters = PromptService(
            self._db, self._registry
        ).materialize_session_parameters(session.id, dict(session.parameters or {}))
        chunking = parameters.get(RAG_PARAM_CHUNKING_MODEL) or {}
        retriever = parameters.get(RAG_PARAM_RETRIEVER_MODEL) or {}
        prompt = parameters.get(RAG_PARAM_PROMPT) or {}
        generation = parameters.get(RAG_PARAM_GENERATION_MODEL) or {}
        transformation = parameters.get(RAG_PARAM_QUERY_TRANSFORMATION) or {}

        return {
            RAG_PARAM_CHUNKING_MODEL: self._describe_chunking(chunking),
            RAG_PARAM_RETRIEVER_MODEL: self._describe_retriever(retriever),
            RAG_PARAM_PROMPT: self._describe_prompt(prompt),
            RAG_PARAM_GENERATION_MODEL: self._describe_generation(generation),
            RAG_PARAM_QUERY_TRANSFORMATION: self._describe_transformation(
                transformation
            ),
            "context_budget": self._context_budget(
                chunking, retriever, prompt, generation, transformation
            ),
        }

    # ── Per-section descriptions ──────────────────────────────────────

    def _describe_chunking(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the chunking component, naming its preset when it has one."""
        section = self._describe_component(RAG_PARAM_CHUNKING_MODEL, ref)
        component = ref.get("component") or ""
        params = ref.get("params") or {}
        preset_key = chunking_presets.match_preset_key(component, params)
        section["preset_key"] = preset_key
        section["preset_display_name"] = self._chunking_preset_name(preset_key)
        chunk_size = params.get("chunk_size")
        if isinstance(chunk_size, int):
            section["summary"] = self._chunk_size_summary(component, chunk_size)
        return section

    def _describe_retriever(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the retriever component, naming its preset when it has one."""
        section = self._describe_component(RAG_PARAM_RETRIEVER_MODEL, ref)
        component = ref.get("component") or ""
        params = ref.get("params") or {}
        preset_key: Optional[str] = None
        try:
            preset_key = retriever_presets.match_preset_key(
                component, params, self._registry
            )
        except Exception:  # pragma: no cover - a stale preset must not 500
            log.exception("Retriever preset matching failed for %s", component)
        section["preset_key"] = preset_key
        section["preset_display_name"] = self._retriever_preset_name(preset_key)
        section["top_k"] = retriever_presets.effective_top_k(component, params)
        return section

    def _describe_prompt(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the prompt component."""
        return self._describe_component(RAG_PARAM_PROMPT, ref)

    def _describe_generation(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the generation model, including availability.

        Download and credential state come straight from the registry, so the
        session view can gate on the same facts the model picker does instead of
        guessing from the class name.
        """
        section = self._describe_component(RAG_PARAM_GENERATION_MODEL, ref)
        component = ref.get("component") or ""
        entry = self._registry_entry(component)
        if entry is None:
            section["requires_download"] = False
            section["downloaded"] = False
            section["credentials_satisfied"] = True
            section["required_credentials"] = []
            return section

        model_class = entry["class"]
        requires_download = bool(getattr(model_class, "REQUIRES_DOWNLOAD", False))
        section["requires_download"] = requires_download
        section["downloaded"] = (
            self._registry.refresh_download_status(component)
            if requires_download
            else True
        )
        section["credentials_satisfied"] = bool(
            entry.get("credentials_satisfied", True)
        )
        section["required_credentials"] = list(entry.get("required_credentials") or [])
        return section

    def _describe_transformation(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the optional query transformation stage.

        The stage is optional, so the section always exists: when the stored
        reference is absent, null or empty the section reports ``enabled`` as
        ``False`` and leaves every resolved field empty. When enabled the
        transformer is described through the shared component path, so an
        uninstalled transformer degrades to ``registered=False`` instead of
        failing the page.

        This stage consumes no prompt or generation tokens of its own, but it is
        not free: retrieval runs once per emitted query and merges the lists, so
        ``context_budget`` prices the stage through the number of queries it
        hands to retrieval and through its reranker's chunk count.

        Parameters
        ----------
        ref : Dict[str, Any]
            The stored ``{component, params}`` reference, or an empty mapping
            when the stage is disabled.

        Returns
        -------
        Dict[str, Any]
            The resolved section, with ``enabled`` telling whether the stage
            runs. Multilingual values are returned as
            :class:`MultilingualString`; the caller localizes them.
        """
        enabled = isinstance(ref, dict) and bool(ref.get("component"))
        if not enabled:
            return {
                "section_name": _SECTION_NAMES[RAG_PARAM_QUERY_TRANSFORMATION],
                "component": None,
                "display_name": None,
                "description": None,
                "registered": False,
                "params": [],
                "enabled": False,
            }

        section = self._describe_component(RAG_PARAM_QUERY_TRANSFORMATION, ref)
        section["enabled"] = True
        return section

    # ── Shared building blocks ────────────────────────────────────────

    def _registry_entry(self, component: str) -> Optional[Dict[str, Any]]:
        """Return a registry entry, or ``None`` when the component is unknown.

        A component can legitimately disappear — an uninstalled plugin, a
        renamed class — and an old session still references it. Reporting it as
        unknown keeps the endpoint useful instead of failing the whole page.
        """
        if not component or component not in self._registry:
            return None
        return self._registry[component]

    def _describe_component(self, key: str, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Build the common part of a section: names, description, parameters."""
        component = ref.get("component") or ""
        params = ref.get("params") or {}
        entry = self._registry_entry(component)

        if entry is None:
            return {
                "section_name": _SECTION_NAMES[key],
                "component": component,
                # Falling back to the raw name is the one place a class name may
                # surface, and only when nothing better exists.
                "display_name": component or None,
                "description": None,
                "registered": False,
                "params": self._describe_params(None, params),
            }

        return {
            "section_name": _SECTION_NAMES[key],
            "component": component,
            "display_name": entry.get("display_name") or component,
            "description": entry.get("description"),
            "registered": True,
            "params": self._describe_params(entry.get("schema"), params),
        }

    def _describe_params(
        self, schema: Optional[Dict[str, Any]], params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Pair each stored parameter with its label and description.

        Labels come from the schema ``title`` that ``schema_field``'s ``alias``
        feeds, so the UI never has to prettify a snake_case key itself.
        """
        properties = (schema or {}).get("properties") or {}
        described = []
        for name, value in params.items():
            prop = properties.get(name) or {}
            described.append(
                {
                    "name": name,
                    "label": prop.get("title") or name,
                    "description": prop.get("description"),
                    "value": value,
                    "is_component": isinstance(value, dict) and "component" in value,
                }
            )
        return described

    def _chunking_preset_name(self, key: Optional[str]) -> Optional[MultilingualString]:
        """Return the display name of a chunking preset key."""
        if key is None:
            return None
        for preset in chunking_presets.get_chunking_presets(self._registry):
            if preset["key"] == key:
                return preset["display_name"]
        return None

    def _retriever_preset_name(
        self, key: Optional[str]
    ) -> Optional[MultilingualString]:
        """Return the display name of a retriever preset key."""
        if key is None:
            return None
        for preset in retriever_presets.get_retriever_presets(10, self._registry):
            if preset["key"] == key:
                return preset["display_name"]
        return None

    def _chunk_size_summary(
        self, component: str, chunk_size: int
    ) -> MultilingualString:
        """Summarise a chunk size in the unit the chunker actually counts in."""
        if self._chunk_unit(component) == "tokens":
            return MultilingualString(
                en=f"{chunk_size} tokens",
                es=f"{chunk_size} tokens",
                pt=f"{chunk_size} tokens",
                de=f"{chunk_size} Tokens",
                zh=f"{chunk_size} 标记",
            )
        tokens = chunking_presets.estimate_tokens(chunk_size)
        return MultilingualString(
            en=f"{chunk_size} characters ≈ {tokens} tokens",
            es=f"{chunk_size} caracteres ≈ {tokens} tokens",
            pt=f"{chunk_size} caracteres ≈ {tokens} tokens",
            de=f"{chunk_size} Zeichen ≈ {tokens} Tokens",
            zh=f"{chunk_size} 字符 ≈ {tokens} 标记",
        )

    def _chunk_unit(self, component: str) -> str:
        """Return whether a chunker counts characters or tokens."""
        entry = self._registry_entry(component)
        if entry is None:
            return "characters"
        return getattr(entry["class"], "CHUNK_UNIT", "characters")

    # ── Context budget ────────────────────────────────────────────────

    def _chunk_tokens(self, chunking: Dict[str, Any]) -> int:
        """Return the token cost of a single retrieved chunk."""
        params = chunking.get("params") or {}
        chunk_size = params.get("chunk_size")
        if not isinstance(chunk_size, int):
            return 0
        if self._chunk_unit(chunking.get("component") or "") == "tokens":
            return chunk_size
        return chunking_presets.estimate_tokens(chunk_size)

    def _retrieval_chunk_count(
        self,
        retriever: Dict[str, Any],
        transformation: Optional[Dict[str, Any]],
    ) -> int:
        """Return how many chunks the retrieval stage puts in the prompt.

        Retrieval runs once per query the transformation stage emits and merges
        the lists, so a multi-query stage costs its queries times the retriever's
        own chunk count. The merged pool is then trimmed to the reranker's chunk
        count when one is configured, and that trimmed pool is what
        the generation prompt receives.

        Parameters
        ----------
        retriever : Dict[str, Any]
            The stored retriever reference.
        transformation : Dict[str, Any] | None
            The stored transformation reference, or ``None``/empty when the
            stage is disabled.

        Returns
        -------
        int
            The number of chunks the prompt can hold, expansion and reranker cap
            included.
        """
        retriever_params = _reference_params(retriever, "the retriever")
        retrieved = retriever_presets.effective_chunk_count(
            retriever[COMPONENT_KEY], retriever_params
        )
        queries = self._query_count(transformation)
        if queries <= SINGLE_QUERY:
            # A single query merges nothing and the reranker only runs on a
            # merged pool, so the retriever's own chunks reach the prompt.
            return retrieved
        merged = retrieved * queries
        cap = self._pool_cap(transformation)
        if cap is None:
            return merged
        # The reranker keeps ``cap`` units of the pool, and every unit is as
        # wide as the retriever's own expansion window makes it: the reranker
        # never expands anything itself.
        capped = cap * retriever_presets.max_expansion_factor(retriever_params)
        if self._is_uncapped_decomposition(transformation):
            # The model decides how many queries an uncapped decomposition
            # emits, so the merged estimate is only a floor: the reranker's cap
            # is the one bound the pool is certain to respect.
            return capped
        return min(merged, capped)

    @staticmethod
    def _is_uncapped_decomposition(transformation: Optional[Dict[str, Any]]) -> bool:
        """Report whether the stage explicitly lifts its sub-query cap.

        Parameters
        ----------
        transformation : Dict[str, Any] | None
            The stored transformation reference.

        Returns
        -------
        bool
            ``True`` when ``max_subqueries`` is stored as an explicit ``None``.
            An omitted cap is not counted here: the budget prices it at the
            declared count (see :meth:`_query_count`).
        """
        if not transformation:
            return False
        params = _stage_params(transformation)
        return MAX_SUBQUERIES_KEY in params and params[MAX_SUBQUERIES_KEY] is None

    def _query_count(self, transformation: Optional[Dict[str, Any]]) -> int:
        """Return how many queries the transformation stage hands to retrieval.

        A stage that declares no query count — a rewriter — retrieves once. An
        explicit count is used as stored. A count the stored stage omits, or an
        explicitly uncapped decomposition (``max_subqueries: null``), is priced
        at the count the transformer's schema declares, since the model decides
        the real number: the runtime does not cap such a stage at that count,
        so the price is an estimate, not a bound (an uncapped decomposition
        with a reranker is bounded by the reranker instead, see
        :meth:`_retrieval_chunk_count`).

        Parameters
        ----------
        transformation : Dict[str, Any] | None
            The stored transformation reference.

        Returns
        -------
        int
            The number of queries retrieval runs for one user message.

        Raises
        ------
        RAGPipelineConfigError
            If the stage's ``params`` is not a dict, or a stored count is neither
            a positive integer nor ``None``.
        """
        if not transformation:
            return SINGLE_QUERY
        params = _stage_params(transformation)
        component = transformation[COMPONENT_KEY]
        for key in QUERY_COUNT_KEYS:
            if key in params and params[key] is not None:
                if not _is_query_count(params[key]):
                    raise RAGPipelineConfigError(
                        f"Stored '{key}' of '{component}' must be a positive "
                        f"integer or null, got {params[key]!r}."
                    )
                return params[key]
            declared = self._declared_query_count(component, key)
            if declared is not None:
                return declared
        return SINGLE_QUERY

    def _declared_query_count(self, component: str, key: str) -> Optional[int]:
        """Return the count a transformer's schema declares for ``key``.

        Parameters
        ----------
        component : str
            Registered transformer class name.
        key : str
            The query-count parameter to read, for example ``"n_queries"``.

        Returns
        -------
        Optional[int]
            The schema placeholder (or its pydantic default when the placeholder
            is absent), or ``None`` when the transformer is unknown or does not
            declare a usable count for ``key``.
        """
        entry = self._registry_entry(component)
        if entry is None:
            return None
        field = getattr(entry["class"].SCHEMA, "model_fields", {}).get(key)
        if field is None:
            return None
        placeholder = (field.json_schema_extra or {}).get("placeholder")
        if _is_query_count(placeholder):
            return placeholder
        if _is_query_count(field.default):
            return field.default
        return None

    def _pool_cap(self, transformation: Optional[Dict[str, Any]]) -> Optional[int]:
        """Return how many chunks the stage's reranker lets through to the prompt.

        The reranker is a retriever, so its output is bounded like one: its own
        ``top_k`` units (see :func:`retriever_presets.effective_top_k`). It
        orders units that already exist, so its own expansion window never
        widens them; the width of the kept units is the retriever stage's.

        Parameters
        ----------
        transformation : Dict[str, Any] | None
            The stored transformation reference.

        Returns
        -------
        int | None
            The number of units the merged pool is trimmed to, or ``None`` when
            no reranker is configured and the whole pool reaches the prompt.

        Raises
        ------
        RAGPipelineConfigError
            If a stored reranker is not a component reference.
        """
        if not transformation:
            return None
        reranker = _stage_params(transformation).get(RERANKER_KEY)
        if reranker is None:
            return None
        if not isinstance(reranker, dict) or not reranker.get(COMPONENT_KEY):
            raise RAGPipelineConfigError(
                "Stored reranker of the query transformation is not a component "
                "reference."
            )
        return retriever_presets.effective_top_k(
            reranker[COMPONENT_KEY], _reference_params(reranker, "the reranker")
        )

    def _context_budget(
        self,
        chunking: Dict[str, Any],
        retriever: Dict[str, Any],
        prompt: Dict[str, Any],
        generation: Dict[str, Any],
        transformation: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute how much of the model's context window is already spoken for.

        The frontend used to do this arithmetic in two duplicated components, one
        of which was fed zeroes and so always reported "valid". Computing it here
        means the session view and the creation flow agree by construction.

        Chunks are counted with
        :func:`~DashAI.back.services.RAG.retriever_presets.effective_chunk_count`,
        which multiplies by the expansion window: an expanded unit carries the
        text of every chunk it covers, so retrieve-then-expand costs more context
        than its ``top_k`` alone suggests. The query transformation stage is
        priced the same way — see :meth:`_retrieval_chunk_count` — so a
        multi-query pool is never reported as a single query's worth of chunks.

        Parameters
        ----------
        chunking, retriever, prompt, generation : Dict[str, Any]
            The stored component references the budget is derived from.
        transformation : Dict[str, Any] | None
            The stored query transformation reference, or ``None`` when the
            stage is disabled.

        Returns
        -------
        Dict[str, Any]
            The window, the tokens already committed and what is left, plus
            whether the configuration fits.
        """
        generation_params = generation.get("params") or {}
        context_window = generation_params.get("context_window")
        if not isinstance(context_window, int):
            context_window = RAG_CONTEXT_WINDOW
        max_tokens = generation_params.get("max_tokens")
        if not isinstance(max_tokens, int):
            max_tokens = RAG_MAX_TOKENS

        chunk_count = self._retrieval_chunk_count(retriever, transformation)
        used_by_chunks = self._chunk_tokens(chunking) * chunk_count

        template = (prompt.get("params") or {}).get("template") or ""
        used_by_prompt = len(template) // CHARS_PER_TOKEN

        available = context_window - used_by_chunks - used_by_prompt - max_tokens
        return {
            "context_window": context_window,
            "max_tokens": max_tokens,
            "used_by_chunks": used_by_chunks,
            "used_by_prompt": used_by_prompt,
            "available": max(0, available),
            "is_valid": available > 0,
        }
