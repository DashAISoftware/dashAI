import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import exc, or_
from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGPipeline,
    RAGPrompt,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt
from DashAI.back.services.RAG.exceptions import (
    RAGDatabaseError,
    RAGPromptValidationError,
)
from DashAI.back.services.RAG.utils import (
    build_parameters_hash,
    normalize_params,
)

if TYPE_CHECKING:
    from DashAI.back.services.RAG.session_document_service import (
        SessionDocumentService,
    )

log = logging.getLogger(__name__)

_RAG_TASK_NAME = "RAGTask"


class PromptInUseError(ValueError):
    """Raised when deleting a prompt would leave sessions without it.

    Attributes
    ----------
    sessions : list of GenerativeSession
        The sessions that reference the prompt.
    """

    def __init__(self, sessions: List[GenerativeSession]) -> None:
        names = ", ".join(session.name for session in sessions)
        super().__init__(
            f"This prompt is used by these RAG sessions: {names}. "
            "Delete them with it to continue."
        )
        self.sessions = sessions


@dataclass
class PromptResponse:
    id: int
    class_name: str
    name: str | None
    parameters: dict[str, Any] | None
    created: datetime
    last_modified: datetime
    is_library: bool = False
    prompt_type: Optional[str] = None
    prompt_subtype: Optional[str] = None
    sessions: List[dict[str, Any]] = field(default_factory=list)


class PromptService:
    """Service layer for RAG prompt CRUD, validation, and session-scoped copies."""

    def __init__(self, db: Session, registry: ComponentRegistry):
        self.db = db
        self._registry = registry

    def create(
        self, class_name: str, name: str, parameters: dict[str, Any]
    ) -> PromptResponse:
        """Create a RAGPrompt record.

        Validates templates via ``validate_prompt_template()``, inserts the
        DB record, and returns the serialized prompt response. When the same
        parameters already exist as an internal pipeline row, that row is
        promoted to a library row instead of failing with a duplicate error.

        Args:
            class_name: Registered prompt component name.
            name: Human-readable name for the prompt.
            parameters: Prompt configuration including ``template`` or
                ``templates``.

        Returns:
            The newly created prompt response.

        Raises:
            RAGPromptValidationError: If validation fails.
            RAGDatabaseError: If a database error occurs.
        """
        if class_name not in self._registry:
            raise RAGPromptValidationError(
                f"Component {class_name} is not registered in the registry."
            )
        prompt_class = self._registry[class_name]["class"]
        if not issubclass(prompt_class, BasePrompt):
            raise RAGPromptValidationError(
                f"Component {class_name} is not a valid Prompt subclass."
            )

        if "templates" in parameters:
            for _lang, tmpl in parameters["templates"].items():
                self.validate_prompt_template(class_name, tmpl)
        elif "template" in parameters:
            self.validate_prompt_template(class_name, parameters["template"])
        else:
            raise RAGPromptValidationError(
                "Prompt parameters must include 'template' or 'templates'."
            )

        parameters = normalize_params(parameters)
        params_hash = build_parameters_hash(parameters)

        try:
            prompt = RAGPrompt(
                class_name=class_name,
                name=name,
                parameters=parameters,
                parameters_hash=params_hash,
                is_library=True,
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            return self._serialize_prompt(prompt)
        except exc.IntegrityError as e:
            self.db.rollback()
            # A session may already have materialized this exact template as
            # an internal ``get_or_create`` row. Promoting that row is what
            # lets the user save a prompt they have already used, instead of
            # returning a 409 for a row the library does not even show.
            existing = self._find_by_hash(parameters)
            if (
                existing is not None
                and existing.class_name == class_name
                and existing.class_name not in self._builtin_prompt_class_names()
                and not existing.is_library
            ):
                existing.is_library = True
                existing.name = name
                self.db.commit()
                self.db.refresh(existing)
                return self._serialize_prompt(existing)
            log.exception(e)
            raise RAGDatabaseError("Error creating prompt in database.") from e
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error creating prompt in database.") from e

    def get_or_create(
        self, class_name: str, name: str, parameters: dict[str, Any]
    ) -> PromptResponse:
        """Lookup-or-create a RAGPrompt record.

        Searches for an existing prompt with the same class name and
        parameters and reuses it when found; otherwise inserts a new record.
        Unlike :meth:`create`, this does not enforce template presence so
        repeated pipeline builds can share a single prompt record.

        The lookup checks both the raw parameters and the sorted variant
        because rows created via :meth:`create` may store keys in a
        non-deterministic order (the UNIQUE constraint compares the
        serialized JSON text). Inserts always use the sorted variant so
        subsequent lookups are deterministic.

        Args:
            class_name: Registered prompt component name.
            name: Human-readable name for the prompt.
            parameters: Prompt configuration including ``template`` or
                ``templates``.

        Returns:
            The existing or newly created prompt response.

        Raises:
            RAGDatabaseError: If a database error occurs.
        """
        normalized = normalize_params(parameters)

        existing = self._find_by_hash(parameters)
        if existing is None and normalized != parameters:
            existing = self._find_by_hash(normalized)

        if existing is not None:
            return self._serialize_prompt(existing)

        params_hash = build_parameters_hash(normalized)
        try:
            prompt = RAGPrompt(
                class_name=class_name,
                name=name,
                parameters=normalized,
                parameters_hash=params_hash,
                is_library=False,
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            return self._serialize_prompt(prompt)
        except exc.IntegrityError:
            self.db.rollback()
            existing = self._find_by_hash(parameters)
            if existing is None and normalized != parameters:
                existing = self._find_by_hash(normalized)
            if existing is not None:
                return self._serialize_prompt(existing)
            raise
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error creating prompt in database.") from e

    def _find_by_hash(self, params: dict[str, Any]) -> RAGPrompt | None:
        """Look up a prompt by its normalized parameters hash.

        Args:
            params: Parameters to compute hash from.

        Returns:
            Matching ``RAGPrompt`` or ``None``.

        Raises:
            RAGDatabaseError: On database error.
        """
        try:
            h = build_parameters_hash(params)
            return self.db.query(RAGPrompt).filter_by(parameters_hash=h).first()
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error looking up prompt by hash.") from e

    def _default_prompt_specs(
        self,
    ) -> tuple[tuple[str, str, dict[str, Any]], ...]:
        """Return every built-in prompt registered in the component registry.

        Generation, augmentation, query-transformation and evaluation prompts
        all declare their language templates in ``metadata["templates"]`` and
        are named ``Default*`` (or tagged ``variant="default"``). Discovering
        them here keeps the library from silently showing only generation
        prompts when a new prompt family is registered.
        """
        specs = []
        for component in self._registry.get_components_by_types(select="Prompt"):
            component_name = component.get("name")
            prompt_class = component.get("class")
            if (
                not component_name
                or prompt_class is None
                or not issubclass(prompt_class, BasePrompt)
            ):
                continue
            metadata = getattr(prompt_class, "metadata", None) or {}
            templates = metadata.get("templates")
            if not isinstance(templates, dict) or not templates:
                continue
            is_default = metadata.get(
                "variant"
            ) == "default" or component_name.startswith("Default")
            if not is_default:
                continue
            display_name = metadata.get("name") or component.get(
                "display_name", component_name
            )
            if isinstance(display_name, dict):
                display_name = display_name.get("en") or component_name
            specs.append(
                (
                    component_name,
                    str(display_name),
                    {"templates": templates, "language": "en"},
                )
            )
        return tuple(specs)

    def _builtin_prompt_class_names(self) -> set[str]:
        """Return the class names of every built-in prompt."""
        return {name for name, _, _ in self._default_prompt_specs()}

    def _ensure_default_prompts(self) -> None:
        """Create any missing built-in prompt rows.

        The library shows built-ins even when the table already contains
        user-created prompts, so seeding cannot depend on the table being
        completely empty.
        """
        specs = self._default_prompt_specs()
        default_names = [name for name, _, _ in specs]
        existing = {
            row[0]
            for row in self.db.query(RAGPrompt.class_name)
            .filter(RAGPrompt.class_name.in_(default_names))
            .all()
        }
        for class_name, name, parameters in specs:
            if class_name in existing:
                continue
            self.db.add(
                RAGPrompt(
                    class_name=class_name,
                    name=name,
                    parameters=parameters,
                    parameters_hash=build_parameters_hash(parameters),
                    is_library=False,
                )
            )
        try:
            self.db.commit()
        except exc.IntegrityError:
            # Another request seeded the same rows between the query and the
            # insert; the rows exist now, which is all this method promises.
            self.db.rollback()

    def get_all(self) -> list[PromptResponse]:
        """Get all prompts.

        Seeds every built-in prompt registered in the component registry
        when its row is missing.

        Returns:
            A list of serialized prompt responses.

        Raises:
            RAGDatabaseError: If a database error occurs.
        """
        try:
            self._ensure_default_prompts()
            prompts = self.db.query(RAGPrompt).all()
            return [self._serialize_prompt(p) for p in prompts]

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise RAGDatabaseError("Error listing prompts in database.") from e

    def get_library(self) -> list[PromptResponse]:
        """List the prompts the library page shows.

        Includes the user-created library rows (``is_library=True``) and the
        built-in defaults. Internal ``get_or_create`` rows stay hidden:
        deleting one of those would break a session that never chose it.

        Returns
        -------
        list of PromptResponse
            Library and built-in prompts ordered by id, each with the sessions
            using it. ``is_library`` tells the UI which ones can be deleted.
        """
        try:
            self._ensure_default_prompts()
            default_names = [name for name, _, _ in self._default_prompt_specs()]
            prompts = (
                self.db.query(RAGPrompt)
                .filter(
                    or_(
                        RAGPrompt.is_library.is_(True),
                        RAGPrompt.class_name.in_(default_names),
                    )
                )
                .order_by(RAGPrompt.id)
                .all()
            )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise RAGDatabaseError("Error listing prompts in database.") from e
        result = []
        for prompt in prompts:
            sessions = self._sessions_for(prompt)
            result.append(
                self._serialize_prompt(prompt, sessions=self._session_payload(sessions))
            )
        return result

    def sessions_using(self, prompt_id: int) -> List[GenerativeSession]:
        """Return the sessions that depend on a prompt.

        Two kinds of dependency count: a ``rag_pipeline`` row pointing at the
        prompt (the pipeline was already built), and a session whose stored
        ``parameters.prompt`` still has the same component and parameters (the
        template was copied but the pipeline has not been built yet).

        Parameters
        ----------
        prompt_id : int
            Primary key of the prompt.

        Returns
        -------
        list of GenerativeSession
            Unique sessions ordered by id.

        Raises
        ------
        LookupError
            If the prompt does not exist.
        """
        prompt = self.db.get(RAGPrompt, prompt_id)
        if prompt is None:
            raise LookupError(f"Prompt with ID {prompt_id} does not exist.")
        return self._sessions_for(prompt)

    def delete(
        self,
        prompt_id: int,
        *,
        cascade_sessions: bool = False,
        session_service: Optional["SessionDocumentService"] = None,
    ) -> None:
        """Delete a prompt created from the library.

        Parameters
        ----------
        prompt_id : int
            Primary key of the prompt.
        cascade_sessions : bool
            Delete the sessions that depend on the prompt as well.
        session_service : SessionDocumentService, optional
            Required when ``cascade_sessions`` is true and sessions exist.

        Raises
        ------
        LookupError
            If the prompt does not exist.
        RAGPromptValidationError
            If the prompt is internal or built-in and must not be deleted.
        PromptInUseError
            If sessions use the prompt and ``cascade_sessions`` is false.
        RAGDatabaseError
            On a database error.
        """
        try:
            prompt = self.db.get(RAGPrompt, prompt_id)
            if prompt is None:
                raise LookupError(f"Prompt with ID {prompt_id} does not exist.")
            if (
                not prompt.is_library
                or prompt.class_name in self._builtin_prompt_class_names()
            ):
                raise RAGPromptValidationError(
                    "Only prompts created from the prompt library can be deleted."
                )

            sessions = self._sessions_for(prompt)
            if sessions and not cascade_sessions:
                raise PromptInUseError(sessions)
            if sessions:
                if session_service is None:
                    raise RAGPromptValidationError(
                        "Deleting a prompt in use requires the session service."
                    )
                for session in sessions:
                    session_service.delete_session(session.id, commit=False)
                self.db.flush()

            # SQLite does not enforce the prompt FK cascade. Clear whatever a
            # concurrent pipeline build could have written before the delete.
            self.db.query(RAGPipeline).filter(
                RAGPipeline.prompt_id == prompt_id
            ).delete(synchronize_session=False)
            self.db.delete(prompt)
            self.db.commit()
        except (LookupError, PromptInUseError, RAGPromptValidationError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error deleting prompt from database.") from e

    def _sessions_for(self, prompt: RAGPrompt) -> List[GenerativeSession]:
        """Return the unique sessions that use ``prompt``.

        Parameters
        ----------
        prompt : RAGPrompt
            The prompt whose users are collected.

        Returns
        -------
        list of GenerativeSession
            Ordered by id.
        """
        found: dict[int, GenerativeSession] = {}
        pipeline_sessions = (
            self.db.query(GenerativeSession)
            .join(RAGPipeline, RAGPipeline.session_id == GenerativeSession.id)
            .filter(RAGPipeline.prompt_id == prompt.id)
            .all()
        )
        for session in pipeline_sessions:
            found[session.id] = session

        target_signature = self._prompt_signature({"params": prompt.parameters or {}})
        for session in (
            self.db.query(GenerativeSession)
            .filter(GenerativeSession.task_name == _RAG_TASK_NAME)
            .all()
        ):
            parameters = session.parameters or {}
            if parameters.get("prompt_id") == prompt.id:
                found[session.id] = session
                continue
            # Generation prompts live under ``parameters.prompt``, but
            # transformation and retriever prompts are nested deeper inside
            # their own component parameters. Walk the whole configuration so
            # every prompt family reports its dependants.
            if self._references_prompt(parameters, prompt.class_name, target_signature):
                found[session.id] = session
        return [found[key] for key in sorted(found)]

    @classmethod
    def _references_prompt(
        cls,
        value: Any,
        class_name: str,
        target_signature: tuple[str, Any] | None,
    ) -> bool:
        """Whether a nested session configuration references a prompt.

        Parameters
        ----------
        value : Any
            A session parameter value, possibly a nested dict or list.
        class_name : str
            Prompt component to look for.
        target_signature : tuple or None
            Template identity to compare, as returned by ``_prompt_signature``.

        Returns
        -------
        bool
            ``True`` when the reference matches the prompt.
        """
        if target_signature is None:
            return False
        if isinstance(value, dict):
            if (
                value.get("component") == class_name
                and cls._prompt_signature(value) == target_signature
            ):
                return True
            return any(
                cls._references_prompt(item, class_name, target_signature)
                for item in value.values()
            )
        if isinstance(value, list):
            return any(
                cls._references_prompt(item, class_name, target_signature)
                for item in value
            )
        return False

    @staticmethod
    def _prompt_signature(reference: Any) -> tuple[str, Any] | None:
        """Return the template identity of a prompt reference.

        Parameters
        ----------
        reference : Any
            A ``{"component", "params"}`` reference, or a wrapped prompt.

        Returns
        -------
        tuple or None
            ``("template", text)`` for a single template,
            ``("templates", ((lang, text), ...))`` for a language map, or
            ``None`` when the reference has no usable template.
        """
        if not isinstance(reference, dict):
            return None
        params = reference.get("params") or {}
        if not isinstance(params, dict):
            return None
        template = params.get("template")
        if isinstance(template, str):
            return ("template", template)
        templates = params.get("templates")
        if isinstance(templates, dict) and templates:
            language = params.get("language")
            if language in templates:
                return ("template", templates[language])
            return (
                "templates",
                tuple(
                    sorted((str(key), str(value)) for key, value in templates.items())
                ),
            )
        return None

    @staticmethod
    def _session_payload(
        sessions: List[GenerativeSession],
    ) -> List[dict[str, Any]]:
        """Serialize sessions for a prompt response."""
        return [{"id": session.id, "name": session.name} for session in sessions]

    def validate_template(self, class_name: str, template: str) -> None:
        """Validate a template against the prompt class's required placeholders.

        Parameters
        ----------
        class_name : str
            Registered prompt component name.
        template : str
            The template string to validate.

        Raises
        ------
        ValueError
            If the component is not registered, is not a Prompt subclass,
            or the template is missing required placeholders.
        """
        self.validate_prompt_template(class_name, template)

    def resolve_prompt_id_to_component(self, prompt_id: int) -> dict[str, Any]:
        """Resolve a prompt_id to a component configuration dict.

        Args:
            prompt_id: Primary key of the prompt.

        Returns:
            ``{"component": class_name, "params": {"template": ...}}``, plus
            ``language`` when the stored row carries one, suitable for
            pipeline configuration.

        Raises:
            RAGPromptValidationError: If the prompt does not exist or has no
                usable template.
            RAGDatabaseError: If a database error occurs.
        """
        try:
            prompt = self.db.get(RAGPrompt, prompt_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise RAGDatabaseError("Error retrieving prompt from database.") from e

        if prompt is None:
            raise RAGPromptValidationError(
                f"Prompt with ID {prompt_id} does not exist."
            )

        params = prompt.parameters or {}
        template = params.get("template")
        if not template:
            if "templates" not in params:
                raise RAGPromptValidationError(
                    f"Prompt {prompt_id} has no 'template' or 'templates'"
                )
            language = params.get("language", "en")
            templates = params["templates"]
            template = templates.get(language)
            if not template:
                template = next(iter(templates.values()), None)
        if not template:
            raise RAGPromptValidationError(f"Prompt {prompt_id} has no usable template")

        resolved = {"template": template}
        language = params.get("language")
        if language is not None:
            resolved["language"] = language

        return {
            "component": prompt.class_name,
            "params": resolved,
        }

    def validate_component_ref(self, prompt_ref: dict[str, Any]) -> None:
        """Validate a prompt component reference.

        Validates that:
        - The prompt reference contains a registered ``component`` name.
        - If a ``template`` is provided, it contains all required placeholders.
        - If no template is provided, the component has a built-in default.

        Parameters
        ----------
        prompt_ref : dict
            ``{"component": "...", "params": {"template": "...", ...}}``

        Raises
        ------
        RAGPromptValidationError
            If validation fails.
        """
        if "component" not in prompt_ref:
            raise RAGPromptValidationError("Prompt config must contain 'component'.")

        component = prompt_ref.get("component", "")
        params = prompt_ref.get("params", {})
        template = params.get("template", "")
        if not template and "templates" in params:
            template = next(iter(params["templates"].values()), "")
        # If no explicit template, the component has a built-in default.
        # Only validate if the caller provided a template to override.
        if template:
            self.validate_prompt_template(component, template)

    def validate_prompt_exists(self, prompt_id: int) -> None:
        """Validate that a prompt ID exists in the database.

        Parameters
        ----------
        prompt_id : int

        Raises
        ------
        RAGPromptValidationError
            If the prompt does not exist.
        """
        prompt = self.db.get(RAGPrompt, prompt_id)
        if prompt is None:
            raise RAGPromptValidationError(
                f"Prompt with ID {prompt_id} does not exist."
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def validate_prompt_template(self, class_name: str, template: str) -> None:
        """Check class is registered, is a Prompt subclass, and template validates.

        Args:
            class_name: Registered prompt component name.
            template: The template string to validate.

        Raises:
            RAGPromptValidationError: On any validation failure.
        """
        if class_name not in self._registry:
            raise RAGPromptValidationError(
                f"Component {class_name} is not registered in the registry."
            )

        prompt_component = self._registry[class_name]
        prompt_class = prompt_component["class"]

        if not issubclass(prompt_class, BasePrompt):
            raise RAGPromptValidationError(
                f"Component {class_name} is not a valid Prompt subclass."
            )

        if not prompt_class.validate_template(template):
            raise RAGPromptValidationError(
                f"Invalid template for prompt {class_name}. "
                f"Required tokens are: {prompt_class.get_required_placeholders()}"
            )

    def _serialize_prompt(
        self,
        prompt: RAGPrompt,
        sessions: Optional[List[dict[str, Any]]] = None,
    ) -> PromptResponse:
        """Convert a RAGPrompt DB model to a PromptResponse."""
        try:
            component = self._registry[prompt.class_name]
        except KeyError:
            component = {}
        prompt_class = component.get("class")
        metadata = getattr(prompt_class, "metadata", None) or {}
        return PromptResponse(
            id=prompt.id,
            class_name=prompt.class_name,
            name=prompt.name,
            parameters=prompt.parameters,
            created=prompt.created,
            last_modified=prompt.last_modified,
            is_library=bool(prompt.is_library),
            prompt_type=metadata.get("type"),
            prompt_subtype=metadata.get("technique"),
            sessions=sessions or [],
        )
