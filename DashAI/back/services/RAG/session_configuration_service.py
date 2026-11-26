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

from typing import Any, Dict, List, Optional

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import GenerativeSession
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PARAM_CHUNKING_MODEL,
    RAG_PARAM_GENERATION_MODEL,
    RAG_PARAM_PROMPT,
    RAG_PARAM_QUERY_TRANSFORMATION,
    RAG_PARAM_RETRIEVER_MODEL,
)
from DashAI.back.models.RAG.retrievers.ref_utils import COMPONENT_KEY, PARAMS_KEY
from DashAI.back.services.RAG import chunking_presets, retriever_presets
from DashAI.back.services.RAG.prompt_service import PromptService
from DashAI.back.services.RAG.session_defaults_service import (
    RAG_CONTEXT_WINDOW,
    RAG_MAX_TOKENS,
)

#: Characters per token, for turning prompt text into a token estimate.
CHARS_PER_TOKEN = 4

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


class RAGSessionNotFoundError(ValueError):
    """Raised when the RAG session whose configuration is requested does not exist."""


def _reference_component(ref: Dict[str, Any]) -> str:
    """Return the component name of a reference, or ``""`` for an empty one.

    Only an empty reference (``{}``) describes as a custom configuration, so it
    has the empty name. Any non-empty reference must name its component with a
    string. One that does not is malformed, and it raises rather than being read
    as an empty component.

    Parameters
    ----------
    ref : Dict[str, Any]
        A ``{"component", "params"}`` reference, or an empty ``{}``.

    Returns
    -------
    str
        The component name, or ``""`` for an empty reference.

    Raises
    ------
    ValueError
        If the reference is not empty and its component is missing or not a
        string.
    """
    if not ref:
        return ""
    component = ref.get(COMPONENT_KEY)
    if not isinstance(component, str):
        raise ValueError(
            f"Component reference with keys {sorted(ref)} must name its "
            f"{COMPONENT_KEY!r} as a string."
        )
    return component


def _reference_params(ref: Dict[str, Any]) -> Dict[str, Any]:
    """Return the ``params`` object of a component reference.

    An empty reference names no component, so it has no parameters. A reference
    that names a component must carry a ``params`` object. One that does not is
    malformed, and it raises rather than being read as an empty configuration.

    Parameters
    ----------
    ref : Dict[str, Any]
        A ``{"component", "params"}`` reference, or an empty one.

    Returns
    -------
    Dict[str, Any]
        The parameters, or an empty dict for an empty reference.

    Raises
    ------
    ValueError
        If the reference names a component but its ``params`` is not an object.
    """
    if not ref:
        return {}
    params = ref.get(PARAMS_KEY)
    if not isinstance(params, dict):
        raise ValueError(
            f"Component reference {ref.get(COMPONENT_KEY)!r} has no params object."
        )
    return params


def _prompt_template(ref: Dict[str, Any]) -> str:
    """Return the template text of a prompt reference, or ``""`` for an empty one.

    An empty reference (``{}``) has no prompt, so it contributes no template
    text. A reference that names a component must carry its template as a
    string. One that does not is malformed, and it raises rather than being
    priced as an empty prompt.

    Parameters
    ----------
    ref : Dict[str, Any]
        A ``{"component", "params"}`` prompt reference, or an empty ``{}``.

    Returns
    -------
    str
        The template text, or ``""`` for an empty reference.

    Raises
    ------
    ValueError
        If the reference names a component but its ``template`` is missing or
        not a string.
    """
    if not ref:
        return ""
    template = _reference_params(ref).get("template")
    if not isinstance(template, str):
        raise ValueError(
            f"Prompt reference {_reference_component(ref)!r} has no string template."
        )
    return template


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
        RAGSessionNotFoundError
            If the session does not exist.
        ValueError
            If the stored configuration is malformed.
        """
        session = self._db.get(GenerativeSession, session_id)
        if session is None:
            raise RAGSessionNotFoundError(
                f"Generative session {session_id} does not exist."
            )

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
                chunking, retriever, prompt, generation
            ),
        }

    # ── Per-section descriptions ──────────────────────────────────────

    def _describe_chunking(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the chunking component, naming its preset when it has one."""
        section = self._describe_component(RAG_PARAM_CHUNKING_MODEL, ref)
        component = _reference_component(ref)
        params = _reference_params(ref)
        preset_key = chunking_presets.match_preset_key(
            component, params, self._registry
        )
        section["preset_key"] = preset_key
        section["preset_display_name"] = self._chunking_preset_name(preset_key)
        chunk_size = params.get("chunk_size")
        if isinstance(chunk_size, int):
            section["summary"] = self._chunk_size_summary(component, chunk_size)
        return section

    def _describe_retriever(self, ref: Dict[str, Any]) -> Dict[str, Any]:
        """Describe the retriever component, naming its preset when it has one."""
        section = self._describe_component(RAG_PARAM_RETRIEVER_MODEL, ref)
        component = _reference_component(ref)
        params = _reference_params(ref)
        preset_key = retriever_presets.match_preset_key(
            component, params, self._registry
        )
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
        component = _reference_component(ref)
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

        This stage is deliberately excluded from ``context_budget``: it only
        rewrites the user message before retrieval and contributes no chunks,
        no prompt template and no generation tokens, so it consumes none of the
        context window the budget accounts for.

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
        if not _reference_component(ref):
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
        component = _reference_component(ref)
        params = _reference_params(ref)
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
                    "is_component": isinstance(value, dict) and COMPONENT_KEY in value,
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
        params = _reference_params(chunking)
        chunk_size = params.get("chunk_size")
        if not isinstance(chunk_size, int):
            return 0
        if self._chunk_unit(_reference_component(chunking)) == "tokens":
            return chunk_size
        return chunking_presets.estimate_tokens(chunk_size)

    def _context_budget(
        self,
        chunking: Dict[str, Any],
        retriever: Dict[str, Any],
        prompt: Dict[str, Any],
        generation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute how much of the model's context window is already spoken for.

        The frontend used to do this arithmetic in two duplicated components, one
        of which was fed zeroes and so always reported "valid". Computing it here
        means the session view and the creation flow agree by construction.

        Chunks are counted with
        :func:`~DashAI.back.services.RAG.retriever_presets.effective_chunk_count`,
        which multiplies by the expansion window: an expanded unit carries the
        text of every chunk it covers, so retrieve-then-expand costs more context
        than its ``top_k`` alone suggests.
        """
        generation_params = _reference_params(generation)
        context_window = generation_params.get("context_window")
        if not isinstance(context_window, int):
            context_window = RAG_CONTEXT_WINDOW
        max_tokens = generation_params.get("max_tokens")
        if not isinstance(max_tokens, int):
            max_tokens = RAG_MAX_TOKENS

        chunk_count = retriever_presets.effective_chunk_count(
            _reference_component(retriever), _reference_params(retriever)
        )
        used_by_chunks = self._chunk_tokens(chunking) * chunk_count

        used_by_prompt = len(_prompt_template(prompt)) // CHARS_PER_TOKEN

        available = context_window - used_by_chunks - used_by_prompt - max_tokens
        return {
            "context_window": context_window,
            "max_tokens": max_tokens,
            "used_by_chunks": used_by_chunks,
            "used_by_prompt": used_by_prompt,
            "available": max(0, available),
            "is_valid": available > 0,
        }
