"""Validation for the optional RAG query transformation stage.

Single-responsibility service extracted from ``SessionValidationService``. It
owns the structural and class checks for the optional
``query_transformation`` parameter and resolves the stage's schema defaults.
Prompt-template validation is injected as a callable so this class never
reaches into ``PromptService`` internals.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List

from DashAI.back.core.schema_fields.defaults import resolve_component_defaults
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.prompts.transformation import (
    DefaultQueryDecompositionPrompt,
    DefaultQueryExpansionPrompt,
    DefaultQueryRewritingPrompt,
    QueryTransformationPrompt,
)
from DashAI.back.models.RAG.RAG_constants import RAG_PARAM_QUERY_TRANSFORMATION
from DashAI.back.models.RAG.RAG_defaults import merge_rag_llm_params
from DashAI.back.models.RAG.transformation import BaseQueryTransformation
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)
from DashAI.back.services.RAG.session_defaults_service import (
    transformation_llm_overrides,
)

log = logging.getLogger(__name__)

#: Nested transformation-parameter keys, hoisted to avoid magic strings.
_PROMPT_KEY = "prompt"
_LLM_MODEL_KEY = "llm_model"

#: Default transformation prompts whose ``template`` may be injected from
#: ``metadata["templates"]`` before schema validation, exactly like the default
#: generation prompts. Kept separate so the two families stay semantically
#: distinct even though they share the injection mechanism.
DEFAULT_TRANSFORMATION_PROMPT_NAMES = frozenset(
    {
        DefaultQueryRewritingPrompt.__name__,
        DefaultQueryExpansionPrompt.__name__,
        DefaultQueryDecompositionPrompt.__name__,
    }
)


class QueryTransformationValidationService:
    """Validates and defaults the optional query transformation stage.

    ``validate`` performs the full structural plus class check (prompt and
    ``llm_model`` subclass enforcement, plus template validation through the
    injected callable). ``apply_defaults`` resolves the transformer's and the
    nested LLM's omitted parameters from their schemas, with the shared RAG LLM
    overrides (10000 context window, 300 max tokens, 0.1 temperature) sitting
    between those schema placeholders and any caller-sent value.
    """

    def __init__(
        self,
        registry: ComponentRegistry,
        prompt_validator: Callable[[str, str], None],
    ):
        """Initialise the validator.

        Parameters
        ----------
        registry : ComponentRegistry
            Application component registry.
        prompt_validator : Callable[[str, str], None]
            ``PromptService.validate_prompt_template`` injected as a
            dependency; called as ``(component_name, template)`` and raises
            when the template is invalid.
        """
        self._registry = registry
        self._prompt_validator = prompt_validator

    def validate(self, normalized: Dict[str, Any]) -> None:
        """Validate the optional ``query_transformation`` stage structurally.

        Semantics
        ---------
        - Absent key → the stage stays absent (disabled).
        - Explicit ``None`` → the stage is disabled; ``None`` is preserved so a
          PUT can use it to turn an existing transformation off.
        - A dict ``{component, params}`` → the stage is enabled. The outer
          component must be a registered :class:`BaseQueryTransformation`, and
          its nested ``prompt`` / ``llm_model`` refs must be present and of the
          correct type. A caller-provided nested prompt template is validated
          here; default templates are injected later by the validation
          service's component-params pass.

        Parameters
        ----------
        normalized : Dict[str, Any]
            Normalised parameters dict, read-only here.

        Raises
        ------
        ValueError
            If the stage is present but malformed.
        """
        if RAG_PARAM_QUERY_TRANSFORMATION not in normalized:
            return
        ref = normalized[RAG_PARAM_QUERY_TRANSFORMATION]
        if ref is None:
            return
        if not isinstance(ref, dict):
            raise ValueError(
                f"'{RAG_PARAM_QUERY_TRANSFORMATION}' must be a dict or null, got "
                f"{type(ref).__name__}."
            )
        if "component" not in ref or not isinstance(ref["component"], str):
            raise ValueError(
                f"Missing or invalid 'component' in '{RAG_PARAM_QUERY_TRANSFORMATION}'."
            )
        if "params" not in ref or not isinstance(ref["params"], dict):
            raise ValueError(
                f"Missing or invalid 'params' in '{RAG_PARAM_QUERY_TRANSFORMATION}'."
            )

        component_name = ref["component"]
        component_class = self._resolve_subclass(
            component_name,
            BaseQueryTransformation,
            f"'{RAG_PARAM_QUERY_TRANSFORMATION}.component'",
        )

        params = ref["params"]
        prompt_ref = params.get("prompt")
        if not isinstance(prompt_ref, dict) or "component" not in prompt_ref:
            raise ValueError(
                f"'prompt' is required in '{RAG_PARAM_QUERY_TRANSFORMATION}' "
                "and must be a component reference."
            )
        prompt_name = prompt_ref["component"]
        if not isinstance(prompt_name, str):
            raise ValueError(
                f"'component' of '{RAG_PARAM_QUERY_TRANSFORMATION}.params.prompt' "
                f"must be a string, got {type(prompt_name).__name__}."
            )
        prompt_class = self._resolve_subclass(
            prompt_name,
            QueryTransformationPrompt,
            f"'{RAG_PARAM_QUERY_TRANSFORMATION}.params.prompt'",
        )
        prompt_base = getattr(
            component_class, "TRANSFORMATION_PROMPT_BASE", QueryTransformationPrompt
        )
        if not issubclass(prompt_class, prompt_base):
            raise ValueError(
                f"Transformer '{component_name}' requires a prompt of type "
                f"{prompt_base.__name__} family, got {prompt_class.__name__}."
            )

        prompt_params = prompt_ref.get("params")
        if prompt_params is not None and not isinstance(prompt_params, dict):
            raise ValueError(
                f"'params' of '{RAG_PARAM_QUERY_TRANSFORMATION}.params.prompt' "
                f"must be a dict, got {type(prompt_params).__name__}."
            )
        template = (
            prompt_params.get("template") if isinstance(prompt_params, dict) else None
        )
        self._validate_nested_template(prompt_name, template)

        llm_ref = params.get("llm_model")
        if not isinstance(llm_ref, dict) or "component" not in llm_ref:
            raise ValueError(
                f"'llm_model' is required in '{RAG_PARAM_QUERY_TRANSFORMATION}' "
                "and must be a component reference."
            )
        llm_name = llm_ref["component"]
        if not isinstance(llm_name, str):
            raise ValueError(
                f"'component' of '{RAG_PARAM_QUERY_TRANSFORMATION}.params.llm_model' "
                f"must be a string, got {type(llm_name).__name__}."
            )
        self._resolve_subclass(
            llm_name,
            TextToTextGenerationTaskModel,
            f"'{RAG_PARAM_QUERY_TRANSFORMATION}.params.llm_model'",
        )
        llm_params = llm_ref.get("params")
        if llm_params is not None and not isinstance(llm_params, dict):
            raise ValueError(
                f"'params' of '{RAG_PARAM_QUERY_TRANSFORMATION}.params.llm_model' "
                f"must be a dict, got {type(llm_params).__name__}."
            )
        log.debug(
            "Query transformation stage enabled with %s", component_class.__name__
        )

    def apply_defaults(self, normalized: Dict[str, Any]) -> None:
        """Fill the transformation stage's omitted params from its schema.

        Mirrors the generation-model defaults for the optional stage: the
        transformer's own schema placeholders (for example ``history_window``)
        plus the nested LLM's and prompt's placeholders are resolved
        server-side, sitting *under* whatever the caller sent. The resolved
        prompt template is later injected from its language-driven defaults by
        the component-params pass.

        The nested LLM receives the shared RAG overrides: ``context_window``
        10000, ``max_tokens`` 300 and ``temperature`` 0.1, instead of the model
        schema's 512/100/0.7 placeholders. A caller value equal to the schema
        placeholder is treated as "not customized" and replaced by the override
        (the shared frontend writes those placeholders when another LLM is
        selected); an explicit non-default value always wins.

        Parameters
        ----------
        normalized : Dict[str, Any]
            Normalised parameters dict, mutated in place only when the stage is
            present and not ``None``.
        """
        ref = normalized.get(RAG_PARAM_QUERY_TRANSFORMATION)
        if not isinstance(ref, dict):
            return
        name = ref.get("component")
        params = ref.get("params")
        if not name or not isinstance(params, dict):
            return

        merged = {**resolve_component_defaults(name, self._registry), **params}
        llm_ref = merged.get(_LLM_MODEL_KEY)
        if isinstance(llm_ref, dict):
            self._apply_llm_defaults(llm_ref)
        prompt_ref = merged.get(_PROMPT_KEY)
        if isinstance(prompt_ref, dict):
            self._apply_prompt_defaults(prompt_ref)
        ref["params"] = merged

    def _apply_llm_defaults(self, llm_ref: Dict[str, Any]) -> None:
        """Resolve the nested transformation LLM's params with the RAG overrides.

        Parameters
        ----------
        llm_ref : Dict[str, Any]
            The nested ``llm_model`` reference, mutated in place. A missing or
            malformed ``params`` container counts as empty, so the reference is
            normalized to the full schema defaults plus the overrides.
        """
        llm_name = llm_ref.get("component")
        llm_params = llm_ref.get("params")
        if not llm_name:
            return
        caller_params = llm_params if isinstance(llm_params, dict) else {}
        llm_ref["params"] = merge_rag_llm_params(
            resolve_component_defaults(llm_name, self._registry),
            caller_params,
            transformation_llm_overrides(),
        )

    def _apply_prompt_defaults(self, prompt_ref: Dict[str, Any]) -> None:
        """Resolve the nested prompt's placeholders under the caller values.

        Parameters
        ----------
        prompt_ref : Dict[str, Any]
            The nested ``prompt`` reference, mutated in place when its
            ``params`` is a dict. Left untouched otherwise.
        """
        prompt_name = prompt_ref.get("component")
        prompt_params = prompt_ref.get("params")
        if not prompt_name or not isinstance(prompt_params, dict):
            return
        prompt_ref["params"] = {
            **resolve_component_defaults(prompt_name, self._registry),
            **prompt_params,
        }

    def _validate_nested_template(self, prompt_name: str, template: Any) -> None:
        """Validate the nested transformation prompt's ``template`` value.

        Default transformation prompts may omit or blank their template: the
        language-driven template is injected later by the component-params pass
        (see ``SessionValidationService._validate_component_params``). Any
        other prompt must carry a non-blank string template with the required
        placeholders.

        Parameters
        ----------
        prompt_name : str
            Registered prompt component name.
        template : Any
            The raw ``template`` value sent for the prompt, or ``None`` when
            the key is absent.

        Raises
        ------
        ValueError
            If the template is not a string, or is blank/absent for a
            non-default prompt.
        """
        where = f"'{RAG_PARAM_QUERY_TRANSFORMATION}.params.prompt.params.template'"
        is_default = prompt_name in DEFAULT_TRANSFORMATION_PROMPT_NAMES
        is_blank = template is None or (
            isinstance(template, str) and not template.strip()
        )
        if is_blank:
            if is_default:
                return
            raise ValueError(
                f"{where} must not be blank; provide a template containing the "
                "required placeholders."
            )
        if not isinstance(template, str):
            raise ValueError(
                f"{where} must be a string, got {type(template).__name__}."
            )
        self._prompt_validator(prompt_name, template)

    def _resolve_subclass(self, name: str, base: type, where: str) -> type:
        """Resolve ``name`` in the registry and assert it derives from ``base``.

        Parameters
        ----------
        name : str
            Registered component name.
        base : type
            Required ancestor class.
        where : str
            Human-readable location used in the error message.

        Returns
        -------
        type
            The resolved component class.

        Raises
        ------
        ValueError
            If the component is unregistered or not a subclass of ``base``.
        """
        if name not in self._registry:
            raise ValueError(f"Component '{name}' at {where} is not registered.")
        klass = self._registry[name]["class"]
        if not issubclass(klass, base):
            raise ValueError(
                f"Component '{name}' at {where} must be a {base.__name__}."
            )
        return klass


__all__: List[str] = [
    "DEFAULT_TRANSFORMATION_PROMPT_NAMES",
    "QueryTransformationValidationService",
]
