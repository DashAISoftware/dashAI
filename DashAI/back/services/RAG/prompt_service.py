import copy
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
    RAGSessionPrompt,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.prompts.augmentation.augmentation_prompt import (
    AugmentationPrompt,
)
from DashAI.back.models.RAG.prompts.base_prompt import BasePrompt
from DashAI.back.models.RAG.prompts.evaluation.llm_filter_prompt import LLMFilterPrompt
from DashAI.back.models.RAG.prompts.evaluation.retrieval_sufficiency_prompt import (
    RetrievalSufficiencyPrompt,
)
from DashAI.back.models.RAG.prompts.generation.RAG_generation_prompt import (
    RAGGenerationPrompt,
)
from DashAI.back.models.RAG.prompts.transformation.transformation_prompt import (
    QueryTransformationPrompt,
)
from DashAI.back.services.RAG.exceptions import (
    RAGDatabaseError,
    RAGPromptValidationError,
)
from DashAI.back.services.RAG.utils import (
    build_prompt_hash,
    normalize_params,
)

if TYPE_CHECKING:
    from DashAI.back.services.RAG.session_document_service import (
        SessionDocumentService,
    )

log = logging.getLogger(__name__)

#: Values exposed in ``PromptResponse.origin``.
_ORIGIN_DEFAULT = "default"
_ORIGIN_LIBRARY = "library"
_ORIGIN_DRAFT = "draft"

#: Duplicate-content message shared by the create/update/fork guards.
_DUPLICATE_PROMPT_MESSAGE = (
    "A prompt with these parameters already exists for this class."
)

#: Slot path of the generation prompt. It lives at ``parameters["prompt"]`` and
#: not inside another component's parameters, so it has no container or key.
_GENERATION_SLOT_PATH = "generation"
#: Public alias for the generation slot path, used by callers that resolve the
#: pipeline's prompt binding directly.
GENERATION_SLOT_PATH = _GENERATION_SLOT_PATH
_DEFAULT_GENERATION_COMPONENT = "DefaultRAGGenerationPrompt"
_DEFAULT_GENERATION_LANGUAGE = "en"

_PROMPT_KEY = "prompt"
_PROMPT_ID_KEY = "prompt_id"
_COMPONENT_KEY = "component"
_PARAMS_KEY = "params"
_TEMPLATE_KEY = "template"
_TEMPLATES_KEY = "templates"
_LANGUAGE_KEY = "language"

#: Task name of the RAG generative task. Legacy sessions only declare it
#: through ``GenerativeSession.task_name``, so the dependency scan filters on
#: the stored value instead of importing the task class (which would create an
#: import cycle through the RAG models).
_RAG_TASK_NAME = "RAGTask"

#: Prompt base classes in the order used to infer a slot's expected base from
#: the default component declared by its schema placeholder.
_PROMPT_BASE_CLASSES: tuple[type, ...] = (
    RAGGenerationPrompt,
    RetrievalSufficiencyPrompt,
    LLMFilterPrompt,
    QueryTransformationPrompt,
    AugmentationPrompt,
    BasePrompt,
)


@dataclass
class PromptSlot:
    """A location in a RAG session configuration that holds a prompt.

    Attributes
    ----------
    slot_path : str
        Stable path naming the slot, for example ``generation``,
        ``query_transformation.prompt`` or
        ``retriever_model.children[0].prompt``.
    container : Any
        Dictionary that holds the prompt key. ``None`` for the generation
        slot, whose prompt lives at the top level.
    key : str or None
        Prompt key inside ``container``. ``None`` for the generation slot.
    expected_base : type
        Prompt base class a prompt bound to this slot must subclass.
    default_component : str or None
        Default prompt component declared by the schema placeholder, when any.
    """

    slot_path: str
    container: Any
    key: Optional[str]
    expected_base: type
    default_component: Optional[str]


class PromptConflictError(RAGPromptValidationError):
    """Raised when a prompt's content collides with an existing row.

    The API maps this to 409 Conflict. A plain validation error means the
    request is malformed; a conflict means the content already exists.
    """


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
    is_default: bool = False
    based_on_id: Optional[int] = None
    origin: str = _ORIGIN_LIBRARY
    prompt_type: Optional[str] = None
    prompt_subtype: Optional[str] = None
    sessions: List[dict[str, Any]] = field(default_factory=list)


def snapshot_bindings(db: Session, session_id: int) -> dict[str, dict[str, Any]]:
    """Return the resolved prompt-binding snapshot of a session.

    A history entry must capture the prompts that were active when it was
    written, not resolve them lazily from the session's current bindings: a
    later prompt edit would otherwise rewrite the past entry and disappear
    from the parameter-history diff.

    Parameters
    ----------
    db : Session
        Database session used to read the bindings.
    session_id : int
        Session whose bindings are captured.

    Returns
    -------
    dict
        Slot path to binding snapshot, ordered by slot path.

    Raises
    ------
    RAGPromptValidationError
        If a binding points at a prompt row that no longer exists.
    """
    result: dict[str, dict[str, Any]] = {}
    rows = (
        db.query(RAGSessionPrompt)
        .filter(RAGSessionPrompt.session_id == session_id)
        .order_by(RAGSessionPrompt.slot_path)
        .all()
    )
    for binding in rows:
        prompt = db.get(RAGPrompt, binding.prompt_id)
        if prompt is None:
            raise RAGPromptValidationError(
                f"Prompt {binding.prompt_id} bound to slot "
                f"{binding.slot_path} does not exist."
            )
        result[binding.slot_path] = PromptService._binding_payload(
            prompt, binding.language
        )
    return result


class PromptService:
    """Service layer for RAG prompt CRUD, validation, and session-scoped copies."""

    def __init__(self, db: Session, registry: ComponentRegistry):
        self.db = db
        self._registry = registry

    def create(
        self, class_name: str, name: str, parameters: dict[str, Any]
    ) -> PromptResponse:
        """Create a library prompt, or promote a matching draft.

        Validates the prompt class and templates, then inserts a library row.
        When ``get_or_create`` already materialized the same content as a
        draft, that draft is promoted to a library row instead of inserting a
        duplicate.

        Args:
            class_name: Registered prompt component name.
            name: Human-readable name for the prompt.
            parameters: Prompt configuration including ``template`` or
                ``templates``.

        Returns:
            The created or promoted prompt response.

        Raises:
            RAGPromptValidationError: If validation fails, the class is a
                built-in default, or the content already belongs to another
                library/default row.
            RAGDatabaseError: If a database error occurs.
        """
        if self._is_default_component(class_name):
            # Built-in defaults are seeded from the registry and are immutable.
            # A library row with a default class would claim the canonical
            # content hash and make the built-in catalog unreachable.
            raise RAGPromptValidationError(
                f"{class_name} is a built-in default prompt; fork it instead "
                "of creating a library prompt with that class."
            )
        self._validate_prompt_parameters(class_name, parameters)

        parameters = normalize_params(parameters)
        params_hash = build_prompt_hash(class_name, parameters)

        existing = self._find_by_hash(class_name, parameters)
        if existing is not None:
            return self._promote_or_reject(existing, name)

        try:
            prompt = RAGPrompt(
                class_name=class_name,
                name=name,
                parameters=parameters,
                parameters_hash=params_hash,
                is_library=True,
                is_default=False,
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            return self._serialize_prompt(prompt)
        except exc.IntegrityError as e:
            self.db.rollback()
            # A concurrent insert won the race after the lookup. Re-query and
            # apply the same promotion rule.
            existing = self._find_by_hash(class_name, parameters)
            if existing is not None:
                return self._promote_or_reject(existing, name)
            log.exception(e)
            raise RAGDatabaseError("Error creating prompt in database.") from e
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error creating prompt in database.") from e

    def _promote_or_reject(self, prompt: RAGPrompt, name: str) -> PromptResponse:
        """Promote a draft row to the library, or reject duplicate content.

        Args:
            prompt: Existing row whose content matches the request.
            name: Name to store when the row is promoted.

        Returns:
            The promoted prompt response, or the existing library row.

        Raises:
            RAGPromptValidationError: If the row is a default or already a
                library row.
            PromptConflictError: If the draft is bound to a session, which
                would mutate that session by promoting its private prompt.
        """
        if prompt.is_default or prompt.is_library:
            raise PromptConflictError(_DUPLICATE_PROMPT_MESSAGE)
        if self._prompt_is_bound(prompt.id):
            # Promoting a bound draft would expose session-private content and
            # flip the row under the owning session. Make the caller fork or
            # save to the library under a new row instead.
            raise PromptConflictError(
                "A prompt with these parameters belongs to a RAG session and "
                "cannot be promoted to the library. Save a copy instead."
            )
        prompt.is_library = True
        prompt.name = name
        self.db.commit()
        self.db.refresh(prompt)
        return self._serialize_prompt(prompt)

    def get_or_create(
        self, class_name: str, name: str, parameters: dict[str, Any]
    ) -> PromptResponse:
        """Lookup-or-create an internal RAGPrompt record.

        Searches for an existing prompt with the same class name and
        parameters and reuses it when found; otherwise inserts a draft row
        (``is_library=False``, ``is_default=False``). Unlike :meth:`create`,
        this does not enforce template presence so repeated pipeline builds
        can share a single prompt record.

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

        existing = self._find_by_hash(class_name, normalized)
        if existing is not None:
            return self._serialize_prompt(existing)

        params_hash = build_prompt_hash(class_name, normalized)
        try:
            prompt = RAGPrompt(
                class_name=class_name,
                name=name,
                parameters=normalized,
                parameters_hash=params_hash,
                is_library=False,
                is_default=False,
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            return self._serialize_prompt(prompt)
        except exc.IntegrityError:
            self.db.rollback()
            existing = self._find_by_hash(class_name, normalized)
            if existing is not None:
                return self._serialize_prompt(existing)
            raise
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error creating prompt in database.") from e

    def _find_by_hash(
        self, class_name: str, params: dict[str, Any]
    ) -> RAGPrompt | None:
        """Look up a prompt by its class-aware normalized parameters hash.

        Args:
            class_name: Registered prompt component name.
            params: Parameters to compute the hash from.

        Returns:
            Matching ``RAGPrompt`` or ``None``.

        Raises:
            RAGDatabaseError: On database error.
        """
        try:
            h = build_prompt_hash(class_name, params)
            return self.db.query(RAGPrompt).filter_by(parameters_hash=h).first()
        except exc.SQLAlchemyError as e:
            # This is a read. Rolling back here would discard the caller's
            # pending work (seeding runs inside SAVEPOINTs and must not be
            # aborted by a lookup).
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
                    # Deep-copy the class-level mapping: a seeded row is a
                    # database object the application may mutate (demote,
                    # promote, edit), and sharing the module dict would let that
                    # mutation reach every other prompt built from the
                    # component metadata.
                    {"templates": copy.deepcopy(templates), "language": "en"},
                )
            )
        return tuple(specs)

    def _ensure_default_prompts(self, *, commit: bool = True) -> None:
        """Create any missing built-in prompt rows.

        The library shows built-ins even when the table already contains
        user-created prompts, so seeding cannot depend on the table being
        completely empty. Each spec is handled in its own SAVEPOINT:

        * an existing canonical default row is left alone;
        * a non-canonical ``is_default`` row for the class (for example one
          migrated with a legacy ``{"template": ...}`` body) is demoted to a
          draft so a single canonical row owns the class;
        * otherwise the canonical row is created, reusing a draft/library row
          that already holds the same content.

        Parameters
        ----------
        commit : bool
            Commit the seeded rows. When false, flush only and leave the
            transaction to the caller.
        """
        seeded = False
        for class_name, name, parameters in self._default_prompt_specs():
            canonical_hash = build_prompt_hash(class_name, parameters)
            try:
                with self.db.begin_nested():
                    if self._demote_non_canonical_defaults(class_name, canonical_hash):
                        seeded = True
                    canonical = self._find_by_hash(class_name, parameters)
                    if canonical is not None:
                        if canonical.is_default:
                            continue
                        # A draft or library row already owns the canonical
                        # content. Promote it instead of colliding on the
                        # globally unique parameters hash.
                        canonical.is_default = True
                        canonical.is_library = False
                        if canonical.name is None:
                            canonical.name = name
                        seeded = True
                        continue
                    self.db.add(
                        RAGPrompt(
                            class_name=class_name,
                            name=name,
                            parameters=parameters,
                            parameters_hash=canonical_hash,
                            is_library=False,
                            is_default=True,
                        )
                    )
                    seeded = True
            except exc.IntegrityError:
                # Another request seeded this row between the lookup and the
                # insert. The SAVEPOINT already rolled that row back; the
                # caller's transaction and the other specs stay usable.
                log.warning(
                    "Could not seed default prompt %s; it may have been "
                    "inserted concurrently.",
                    class_name,
                )
                continue
        if commit and seeded:
            self.db.commit()
        else:
            self.db.flush()

    def _demote_non_canonical_defaults(
        self, class_name: str, canonical_hash: str
    ) -> bool:
        """Demote every default row of ``class_name`` that is not canonical.

        Legacy databases may hold ``is_default`` rows whose parameters only
        carry a ``template`` (or a different templates map). Keeping them
        flagged as defaults would let two rows compete for one class and make
        reads depend on insertion order. The rows are kept as drafts so any
        session bound to them keeps its text.

        Parameters
        ----------
        class_name : str
            Registered default prompt component.
        canonical_hash : str
            Hash of the registry-owned canonical parameters.

        Returns
        -------
        bool
            Whether at least one row was demoted.
        """
        rows = (
            self.db.query(RAGPrompt)
            .filter(
                RAGPrompt.class_name == class_name,
                RAGPrompt.is_default.is_(True),
            )
            .all()
        )
        demoted = False
        for row in rows:
            if row.parameters_hash == canonical_hash:
                continue
            row.is_default = False
            demoted = True
        return demoted

    def get_all(self) -> list[PromptResponse]:
        """Get every prompt a user may select.

        Internal drafts are excluded: they are session-local content-addressed
        rows, so exposing them would let a client hand another session's private
        edit to a pipeline. Built-in defaults and user library rows are listed.

        Returns:
            A list of serialized prompt responses, each reporting the RAG
            sessions that use it.

        Raises:
            RAGDatabaseError: If a database error occurs.
        """
        try:
            self._ensure_default_prompts()
            prompts = (
                self.db.query(RAGPrompt)
                .filter(
                    or_(
                        RAGPrompt.is_library.is_(True),
                        RAGPrompt.is_default.is_(True),
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

    def get(self, prompt_id: int) -> PromptResponse:
        """Return one prompt by its primary key.

        Parameters
        ----------
        prompt_id : int
            Primary key of the prompt.

        Returns
        -------
        PromptResponse
            The serialized prompt, reporting the RAG sessions that use it.

        Raises
        ------
        LookupError
            If the prompt does not exist.
        RAGDatabaseError
            On a database error.
        """
        try:
            prompt = self.db.get(RAGPrompt, prompt_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise RAGDatabaseError("Error retrieving prompt from database.") from e
        if prompt is None:
            raise LookupError(f"Prompt with ID {prompt_id} does not exist.")
        sessions = self._sessions_for(prompt)
        return self._serialize_prompt(prompt, sessions=self._session_payload(sessions))

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
            prompts = (
                self.db.query(RAGPrompt)
                .filter(
                    or_(
                        RAGPrompt.is_library.is_(True),
                        RAGPrompt.is_default.is_(True),
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
        """Return the sessions bound to a prompt.

        A session depends on a prompt when any of its
        ``rag_session_prompt`` slots points at it. A prompt can be bound to
        several slots of the same session, so the result is de-duplicated.

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
        detach: bool = False,
        session_service: Optional["SessionDocumentService"] = None,
    ) -> None:
        """Delete a prompt created from the library.

        Parameters
        ----------
        prompt_id : int
            Primary key of the prompt.
        cascade_sessions : bool
            Delete the sessions that depend on the prompt as well.
        detach : bool
            Keep the sessions: copy the prompt content into an internal draft
            row and repoint every binding to it before deleting the library
            row. Mutually exclusive with ``cascade_sessions``.
        session_service : SessionDocumentService, optional
            Required when ``cascade_sessions`` is true and sessions exist.

        Raises
        ------
        LookupError
            If the prompt does not exist.
        RAGPromptValidationError
            If the prompt is internal or built-in and must not be deleted, or
            both ``detach`` and ``cascade_sessions`` were requested.
        PromptInUseError
            If sessions use the prompt and neither option was requested.
        RAGDatabaseError
            On a database error.
        """
        if detach and cascade_sessions:
            raise RAGPromptValidationError(
                "Choose either detach or cascade_sessions, not both."
            )
        try:
            prompt = self.db.get(RAGPrompt, prompt_id)
            if prompt is None:
                raise LookupError(f"Prompt with ID {prompt_id} does not exist.")
            if prompt.is_default:
                raise RAGPromptValidationError(
                    "Built-in default prompts cannot be deleted."
                )
            if not prompt.is_library:
                raise RAGPromptValidationError(
                    "Only prompts created from the prompt library can be deleted."
                )

            sessions = self._sessions_for(prompt)
            if sessions and not (cascade_sessions or detach):
                raise PromptInUseError(sessions)
            if cascade_sessions and sessions:
                if session_service is None:
                    raise RAGPromptValidationError(
                        "Deleting a prompt in use requires the session service."
                    )
                session_ids = [session.id for session in sessions]
                for session in sessions:
                    session_service.delete_session(session.id, commit=False)
                # SQLite does not enforce the ``rag_session_prompt`` FK
                # cascade, so drop the links explicitly with their sessions.
                self.db.query(RAGSessionPrompt).filter(
                    RAGSessionPrompt.session_id.in_(session_ids)
                ).delete(synchronize_session=False)
                self.db.flush()

            has_pipelines = (
                self.db.query(RAGPipeline.id)
                .filter(RAGPipeline.prompt_id == prompt_id)
                .first()
                is not None
            )
            if detach and (sessions or has_pipelines):
                # The draft can only take the content hash once the library row
                # releases it, so delete first and insert the draft afterwards.
                # A pipeline without a session binding still needs the draft:
                # it is that session's build history.
                self._detach_bindings_for_delete(prompt)
                self.db.commit()
                return

            # SQLite does not enforce the prompt FK. Drop any leftover binding
            # pointing at this row: a binding whose session join is empty (an
            # orphan) is invisible to ``_sessions_for`` but would still violate
            # the FK on a database that enforces it.
            self.db.query(RAGSessionPrompt).filter(
                RAGSessionPrompt.prompt_id == prompt_id
            ).delete(synchronize_session=False)
            # Detach every pipeline that still points at the prompt instead of
            # deleting it: the pipeline row is a session's build history and
            # must survive the prompt.
            self.db.query(RAGPipeline).filter(
                RAGPipeline.prompt_id == prompt_id
            ).update(
                {RAGPipeline.prompt_id: None},
                synchronize_session=False,
            )
            self.db.query(RAGPrompt).filter(RAGPrompt.based_on_id == prompt_id).update(
                {RAGPrompt.based_on_id: None},
                synchronize_session=False,
            )
            self.db.delete(prompt)
            self.db.commit()
        except (LookupError, PromptInUseError, RAGPromptValidationError):
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error deleting prompt from database.") from e

    def _detach_bindings_for_delete(self, prompt: RAGPrompt) -> None:
        """Replace a library prompt with an equivalent draft in every binding.

        The source row is deleted first so the draft can own the content hash,
        which is globally unique. Bindings keep their ``slot_path`` and
        ``language``, and pipeline snapshots are repointed at the draft so a
        session keeps the exact prompt it was built with. The caller commits.

        Parameters
        ----------
        prompt : RAGPrompt
            Library prompt about to be deleted.
        """
        bindings = (
            self.db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.prompt_id == prompt.id)
            .all()
        )
        targets: list[tuple[int, str, Optional[str]]] = []
        for binding in bindings:
            targets.append((binding.session_id, binding.slot_path, binding.language))
        class_name = prompt.class_name
        parameters = normalize_params(prompt.parameters or {})

        pipeline_ids = [
            row[0]
            for row in self.db.query(RAGPipeline.id)
            .filter(RAGPipeline.prompt_id == prompt.id)
            .all()
        ]
        self.db.query(RAGPrompt).filter(RAGPrompt.based_on_id == prompt.id).update(
            {RAGPrompt.based_on_id: None},
            synchronize_session=False,
        )
        # Delete through the ORM so the identity map forgets the old rows
        # before the replacements with the same (session_id, slot_path) key
        # are inserted below.
        for binding in bindings:
            self.db.delete(binding)
        self.db.flush()
        self.db.delete(prompt)
        self.db.flush()

        draft = self._find_by_hash(class_name, parameters)
        if draft is None:
            draft = RAGPrompt(
                class_name=class_name,
                name=None,
                parameters=parameters,
                parameters_hash=build_prompt_hash(class_name, parameters),
                is_library=False,
                is_default=False,
                based_on_id=None,
            )
            self.db.add(draft)
            self.db.flush()

        if pipeline_ids:
            # The detached draft holds the very content the pipelines were
            # built from, so point them at it instead of losing the snapshot.
            self.db.query(RAGPipeline).filter(RAGPipeline.id.in_(pipeline_ids)).update(
                {RAGPipeline.prompt_id: draft.id},
                synchronize_session=False,
            )

        for session_id, slot_path, language in targets:
            self.db.add(
                RAGSessionPrompt(
                    session_id=session_id,
                    slot_path=slot_path,
                    prompt_id=draft.id,
                    language=language,
                )
            )
        self.db.flush()

    def update_library_prompt(
        self,
        prompt_id: int,
        name: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> PromptResponse:
        """Edit a user-owned library prompt in place.

        Default prompts and internal drafts are immutable: defaults must be
        forked, and drafts are promoted by :meth:`create`. The content hash is
        recomputed after an edit and must not collide with another row.

        Parameters
        ----------
        prompt_id : int
            Primary key of the prompt.
        name : str, optional
            New display name. ``None`` keeps the stored name.
        parameters : dict, optional
            New parameters. ``None`` keeps the stored parameters.

        Returns
        -------
        PromptResponse
            The updated prompt.

        Raises
        ------
        LookupError
            If the prompt does not exist.
        RAGPromptValidationError
            If the prompt is a default, is not a library row, the templates
            are invalid, or the new content collides with another row.
        RAGDatabaseError
            On a database error.
        """
        try:
            prompt = self.db.get(RAGPrompt, prompt_id)
            if prompt is None:
                raise LookupError(f"Prompt with ID {prompt_id} does not exist.")
            if prompt.is_default:
                raise RAGPromptValidationError(
                    "Built-in default prompts cannot be edited; fork them instead."
                )
            if not prompt.is_library:
                raise RAGPromptValidationError(
                    "Only prompts created from the prompt library can be edited."
                )

            if parameters is not None:
                self._validate_prompt_parameters(prompt.class_name, parameters)
                new_parameters = normalize_params(parameters)
                # Check the collision before mutating the row: ``_find_by_hash``
                # autoflushes pending changes, and writing the conflicting hash
                # first would surface as an IntegrityError instead of a
                # validation error.
                collision = self._find_by_hash(prompt.class_name, new_parameters)
                if collision is not None and collision.id != prompt.id:
                    raise PromptConflictError(_DUPLICATE_PROMPT_MESSAGE)
                prompt.parameters = new_parameters
                prompt.parameters_hash = build_prompt_hash(
                    prompt.class_name, new_parameters
                )

            if name is not None:
                prompt.name = name

            self.db.commit()
            self.db.refresh(prompt)
            return self._serialize_prompt(prompt)
        except (LookupError, RAGPromptValidationError):
            self.db.rollback()
            raise
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error updating prompt in database.") from e

    def fork_prompt(
        self,
        prompt_id: int,
        name: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> PromptResponse:
        """Create a user-owned copy of a prompt.

        Forking a default switches it to its ``CUSTOM_CLASS`` counterpart and
        seeds the copy with the default's active template; forking a library
        prompt keeps its class. The fork is idempotent when the requested name
        matches: an existing draft is promoted, and an existing library row is
        returned. Requesting a different name for content that already belongs
        to a library row raises ``PromptConflictError`` instead of silently
        ignoring the name.

        Parameters
        ----------
        prompt_id : int
            Primary key of the source prompt.
        name : str
            Name to store on the fork.
        parameters : dict, optional
            Parameters for the fork. ``None`` reuses the source's template.

        Returns
        -------
        PromptResponse
            The new, promoted, or existing library prompt.

        Raises
        ------
        LookupError
            If the source prompt does not exist.
        RAGPromptValidationError
            If the source default has no custom counterpart, the parameters
            are invalid, the target content is a default, or the target
            content already belongs to a library prompt under another name.
        PromptConflictError
            If the source is an internal draft, which belongs to whichever
            session created it.
        RAGDatabaseError
            On a database error.
        """
        try:
            source = self.db.get(RAGPrompt, prompt_id)
            if source is None:
                raise LookupError(f"Prompt with ID {prompt_id} does not exist.")
            if (
                not source.is_default
                and not source.is_library
                and not self._is_default_component(source.class_name)
            ):
                # An internal draft is a session's private, content-addressed
                # edit. Forking it would publish it and mutate the session that
                # owns it.
                raise PromptConflictError(
                    f"Prompt {prompt_id} is an internal draft and cannot be "
                    "forked. Save it to the library instead."
                )

            target_class = self._fork_class_name(source)
            target_params = self._fork_parameters(source, parameters)
            self._validate_prompt_parameters(target_class, target_params)
            target_params = normalize_params(target_params)
            target_hash = build_prompt_hash(target_class, target_params)

            existing = self._find_by_hash(target_class, target_params)
            if existing is not None:
                return self._resolve_fork_target(existing, source, name)

            prompt = RAGPrompt(
                class_name=target_class,
                name=name,
                parameters=target_params,
                parameters_hash=target_hash,
                is_library=True,
                is_default=False,
                # Only a default has a distinct fork source. Forking a library
                # row keeps the same class and content, so the row found above
                # is the source itself and must not point at itself.
                based_on_id=source.id if source.is_default else None,
            )
            self.db.add(prompt)
            self.db.commit()
            self.db.refresh(prompt)
            return self._serialize_prompt(prompt)
        except (LookupError, RAGPromptValidationError):
            self.db.rollback()
            raise
        except exc.IntegrityError as e:
            self.db.rollback()
            existing = self._find_by_hash(target_class, target_params)
            if existing is not None:
                return self._resolve_fork_target(existing, source, name)
            log.exception(e)
            raise RAGDatabaseError("Error forking prompt in database.") from e
        except exc.SQLAlchemyError as e:
            self.db.rollback()
            log.exception(e)
            raise RAGDatabaseError("Error forking prompt in database.") from e

    def _resolve_fork_target(
        self, existing: RAGPrompt, source: RAGPrompt, name: str
    ) -> PromptResponse:
        """Promote or return a row that already holds the fork's content.

        Parameters
        ----------
        existing : RAGPrompt
            Row whose content matches the fork.
        source : RAGPrompt
            Prompt being forked, recorded as lineage on a promoted draft.
        name : str
            Name to store when the row is promoted.

        Returns
        -------
        PromptResponse
            The promoted or existing library prompt.

        Raises
        ------
        RAGPromptValidationError
            If the row is a default prompt, or it is a library row already
            stored under a different name.
        """
        if existing.is_default:
            raise PromptConflictError(
                "A default prompt already owns this content and cannot be "
                "used as a fork target."
            )
        if existing.is_library:
            if existing.name and existing.name != name:
                # Returning the row silently would drop the requested name.
                # Say so instead, and let the client PATCH the library prompt
                # if it really wants to rename it.
                raise PromptConflictError(
                    f"A library prompt named '{existing.name}' already owns "
                    "this content."
                )
            return self._serialize_prompt(existing)
        existing.is_library = True
        existing.name = name
        if existing.based_on_id is None and existing.id != source.id:
            existing.based_on_id = source.id
        self.db.commit()
        self.db.refresh(existing)
        return self._serialize_prompt(existing)

    def _fork_class_name(self, source: RAGPrompt) -> str:
        """Return the prompt class a fork of ``source`` must use.

        Parameters
        ----------
        source : RAGPrompt
            Prompt being forked.

        Returns
        -------
        str
            The source class for ordinary library prompts, or the default's
            ``CUSTOM_CLASS`` counterpart for default prompts and for legacy
            ``Default*`` rows that were demoted to drafts.

        Raises
        ------
        RAGPromptValidationError
            If a default prompt has no registered custom counterpart.
        """
        if not source.is_default and not self._is_default_component(source.class_name):
            return source.class_name
        try:
            source_class = self._registry[source.class_name]["class"]
        except KeyError as e:
            raise RAGPromptValidationError(
                f"Default prompt {source.class_name} is not registered."
            ) from e
        custom_class = getattr(source_class, "CUSTOM_CLASS", None)
        if not custom_class:
            raise RAGPromptValidationError(
                f"Default prompt {source.class_name} has no custom counterpart."
            )
        return custom_class

    def _fork_parameters(
        self, source: RAGPrompt, parameters: Optional[dict[str, Any]]
    ) -> dict[str, Any]:
        """Return the parameters a fork of ``source`` must store.

        Parameters
        ----------
        source : RAGPrompt
            Prompt being forked.
        parameters : dict, optional
            Caller-provided override, used verbatim when present.

        Returns
        -------
        dict
            The caller's parameters, the source parameters for a library
            prompt, or the source template wrapped for a default's custom
            counterpart.

        Raises
        ------
        RAGPromptValidationError
            If a default prompt has no usable template.
        """
        if parameters is not None:
            return dict(parameters)
        source_params = source.parameters or {}
        if not self._is_default_component(source.class_name):
            return dict(source_params)
        template = self._active_template(source_params)
        if not template:
            # A legacy ``Default*`` row may only store a language selector. The
            # canonical text still lives in the component metadata, so fork it
            # rather than failing the request.
            template, _ = self._registered_default_template(
                source.class_name, source_params.get(_LANGUAGE_KEY)
            )
        if not template:
            raise RAGPromptValidationError(
                f"Default prompt {source.class_name} has no usable template."
            )
        return {"template": template}

    def _sessions_for(self, prompt: RAGPrompt) -> List[GenerativeSession]:
        """Return the unique sessions bound to ``prompt``.

        A session depends on the prompt when any ``rag_session_prompt`` slot
        points at it, either through a binding row or, for sessions created
        before prompts moved into their own table, through a ``prompt_id``
        stored inside ``parameters``. Missing the legacy reference would let a
        prompt be deleted while a session still needs it, and the session would
        then be unreadable.

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
        bound = (
            self.db.query(GenerativeSession)
            .join(
                RAGSessionPrompt,
                RAGSessionPrompt.session_id == GenerativeSession.id,
            )
            .filter(RAGSessionPrompt.prompt_id == prompt.id)
            .distinct()
            .order_by(GenerativeSession.id)
            .all()
        )
        for session in bound:
            found[session.id] = session

        # Legacy rows keep their prompt reference in the configuration blob.
        # The value is JSON, so the comparison has to happen in Python: SQL
        # cannot portably inspect it and a LIKE would match ``prompt_id: 12``
        # for prompt 1.
        candidates = (
            self.db.query(GenerativeSession)
            .filter(GenerativeSession.task_name == _RAG_TASK_NAME)
            .order_by(GenerativeSession.id)
            .all()
        )
        for session in candidates:
            if session.id in found:
                continue
            if self._references_prompt_id(session.parameters, prompt.id):
                found[session.id] = session

        return [found[key] for key in sorted(found)]

    @classmethod
    def _references_prompt_id(cls, value: Any, prompt_id: int) -> bool:
        """Whether a stored parameter value references ``prompt_id``.

        Parameters
        ----------
        value : Any
            Stored parameter value, or any nested container of it.
        prompt_id : int
            Prompt id to look for.

        Returns
        -------
        bool
            ``True`` when a ``prompt_id`` key holds that id. Booleans are
            ignored: ``True == 1`` would otherwise match prompt 1.
        """
        if isinstance(value, dict):
            for key, item in value.items():
                if (
                    key == _PROMPT_ID_KEY
                    and isinstance(item, int)
                    and not isinstance(item, bool)
                    and item == prompt_id
                ):
                    return True
                if cls._references_prompt_id(item, prompt_id):
                    return True
            return False
        if isinstance(value, list):
            return any(cls._references_prompt_id(item, prompt_id) for item in value)
        return False

    def _prompt_is_bound(self, prompt_id: int) -> bool:
        """Whether any session or pipeline snapshot still points at a prompt.

        Parameters
        ----------
        prompt_id : int
            Primary key of the prompt.

        Returns
        -------
        bool
            ``True`` when a ``rag_session_prompt`` or ``rag_pipeline`` row
            references the prompt.
        """
        binding = (
            self.db.query(RAGSessionPrompt.session_id)
            .filter(RAGSessionPrompt.prompt_id == prompt_id)
            .first()
        )
        if binding is not None:
            return True
        pipeline = (
            self.db.query(RAGPipeline.id)
            .filter(RAGPipeline.prompt_id == prompt_id)
            .first()
        )
        return pipeline is not None

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

        A row whose class is a registered default but whose parameters carry no
        usable text (a legacy ``{"language": "en"}`` body, or a draft migrated
        from one) falls back to the class's ``metadata["templates"]``, selecting
        the binding language and defaulting to ``en``. This keeps legacy rows
        readable instead of failing every session that references them.

        Args:
            prompt_id: Primary key of the prompt.

        Returns:
            ``{"component": class_name, "params": {"template": ...}}``, plus
            ``language`` when the stored row carries one or the fallback
            selected one, suitable for pipeline configuration.

        Raises:
            RAGPromptValidationError: If the prompt does not exist, the id is
                not an integer, or the prompt has no usable template.
            RAGDatabaseError: If a database error occurs.
        """
        prompt_id = self.require_prompt_id(prompt_id)
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
        template = params.get(_TEMPLATE_KEY)
        language = params.get(_LANGUAGE_KEY)
        if not template:
            templates = params.get(_TEMPLATES_KEY)
            if isinstance(templates, dict) and templates:
                selected = language if language in templates else None
                if selected is None:
                    selected = "en" if "en" in templates else next(iter(templates))
                template = templates.get(selected)
                language = selected
        if not template and self._is_default_component(prompt.class_name):
            # Legacy default rows and drafts migrated from them may only carry
            # a language selector. The canonical text is code-owned, so read it
            # from the registered component metadata.
            template, selected = self._registered_default_template(
                prompt.class_name, language
            )
            if template:
                language = selected
        if not template:
            if _TEMPLATES_KEY not in params and _TEMPLATE_KEY not in params:
                raise RAGPromptValidationError(
                    f"Prompt {prompt_id} has no 'template' or 'templates'"
                )
            raise RAGPromptValidationError(f"Prompt {prompt_id} has no usable template")

        resolved = {_TEMPLATE_KEY: template}
        if language is not None:
            resolved[_LANGUAGE_KEY] = language

        return {
            _COMPONENT_KEY: prompt.class_name,
            _PARAMS_KEY: resolved,
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
            Primary key of the prompt. A boolean, float, string or container
            is rejected: ``True`` and ``1.0`` would silently address prompt 1.

        Raises
        ------
        RAGPromptValidationError
            If the prompt does not exist or the id is not a plain integer.
        """
        prompt_id = self.require_prompt_id(prompt_id)
        prompt = self.db.get(RAGPrompt, prompt_id)
        if prompt is None:
            raise RAGPromptValidationError(
                f"Prompt with ID {prompt_id} does not exist."
            )

    @staticmethod
    def require_prompt_id(prompt_id: Any) -> int:
        """Return ``prompt_id`` when it is a non-boolean integer.

        Parameters
        ----------
        prompt_id : Any
            Caller-provided prompt identifier.

        Returns
        -------
        int
            The same id, guaranteed to be an ``int``.

        Raises
        ------
        RAGPromptValidationError
            If the value is missing, a boolean, a float, a string or a
            container.
        """
        if isinstance(prompt_id, bool) or not isinstance(prompt_id, int):
            raise RAGPromptValidationError(
                f"'prompt_id' must be an integer, got {type(prompt_id).__name__}."
            )
        return prompt_id

    # ------------------------------------------------------------------
    # Session prompt slots and bindings
    # ------------------------------------------------------------------

    def discover_prompt_slots(self, parameters: dict[str, Any]) -> List[PromptSlot]:
        """Find every prompt location declared by a session configuration.

        The generation prompt is always first: it lives at
        ``parameters["prompt"]`` and has no component container. Every other
        slot is discovered by walking the component references in
        ``parameters`` and reading each component's schema for properties whose
        placeholder is itself a prompt component reference.

        Parameters
        ----------
        parameters : dict
            A RAG session configuration. Prompt references may still be
            present; they are treated as slots and never walked into.

        Returns
        -------
        list of PromptSlot
            Generation first, then the remaining slots sorted by path.
        """
        generation = PromptSlot(
            slot_path=_GENERATION_SLOT_PATH,
            container=None,
            key=None,
            expected_base=RAGGenerationPrompt,
            default_component=None,
        )
        slots: list[PromptSlot] = [generation]
        if isinstance(parameters, dict):
            for key, value in parameters.items():
                if key in (_PROMPT_KEY, _PROMPT_ID_KEY):
                    continue
                if not self._is_component_ref(value):
                    continue
                if self._is_prompt_component(value.get(_COMPONENT_KEY)):
                    continue
                self._discover_slots_in_reference(value, key, slots)
        return [generation, *sorted(slots[1:], key=lambda slot: slot.slot_path)]

    def split_prompts(
        self, parameters: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        """Extract every prompt reference from a session configuration.

        The returned parameters keep the component structure but contain no
        prompt keys; each extracted reference is keyed by its slot path. No
        database row is created or modified.

        Parameters
        ----------
        parameters : dict
            A RAG session configuration that may carry prompt references.

        Returns
        -------
        tuple
            ``(clean_parameters, prompt_inputs)`` where ``prompt_inputs`` maps
            slot paths to their ``{"component", "params"}`` (or
            ``{"prompt_id"}``) references. An explicit ``prompt_id`` is folded
            into the generation slot's input so the ownership guard on the
            draft path still sees it.
        """
        cleaned = copy.deepcopy(parameters) if isinstance(parameters, dict) else {}
        prompt_inputs: dict[str, dict[str, Any]] = {}

        generation = cleaned.pop(_PROMPT_KEY, None)
        prompt_id = cleaned.pop(_PROMPT_ID_KEY, None)
        if isinstance(generation, dict) and generation:
            if prompt_id is not None and _PROMPT_ID_KEY not in generation:
                # Keep the id next to the resolved reference: the binding sync
                # must be able to tell an explicit selection from a
                # content-addressed edit.
                generation = {**generation, _PROMPT_ID_KEY: prompt_id}
            prompt_inputs[_GENERATION_SLOT_PATH] = generation
        elif prompt_id is not None:
            prompt_inputs[_GENERATION_SLOT_PATH] = {_PROMPT_ID_KEY: prompt_id}

        for slot in self.discover_prompt_slots(cleaned):
            if slot.slot_path == _GENERATION_SLOT_PATH:
                continue
            if slot.container is None or slot.key is None:
                continue
            if slot.key in slot.container:
                prompt_inputs[slot.slot_path] = slot.container.pop(slot.key)

        return cleaned, prompt_inputs

    def materialize_prompt_input(
        self,
        slot: PromptSlot,
        prompt_input: dict[str, Any],
        *,
        language: Optional[str] = None,
        current_prompt_id: Optional[int] = None,
    ) -> tuple[RAGPrompt, Optional[str]]:
        """Resolve a prompt input to a stored prompt row.

        The input may reference an existing row (``prompt_id``), describe a
        component configuration, or both. A ``prompt_id`` whose accompanying
        parameters differ from the stored row is treated as a session-local
        edit: the target class is the default's custom counterpart (or the
        row's own class) and the result is an immutable draft row. Default and
        library rows are never mutated here.

        Parameters
        ----------
        slot : PromptSlot
            Slot the input is being bound to.
        prompt_input : dict
            Prompt reference, optionally carrying a ``language`` selection.
        language : str, optional
            Binding language for a default prompt. Overrides the input's own
            ``language`` when both are present.
        current_prompt_id : int, optional
            Prompt currently bound to the slot. A draft row is only selectable
            when it is this row, so a session can re-save its own draft but
            cannot adopt another session's.

        Returns
        -------
        tuple
            The prompt row and the binding language (``None`` for non-default
            rows).

        Raises
        ------
        RAGPromptValidationError
            If the input is malformed, the referenced ``prompt_id`` is missing
            or not an integer, the class is not valid for the slot, or the
            referenced row is a non-selectable draft.
        """
        if not isinstance(prompt_input, dict):
            raise RAGPromptValidationError("Prompt input must be a dict.")

        requested_language = language
        if requested_language is None and isinstance(
            prompt_input.get(_LANGUAGE_KEY), str
        ):
            requested_language = prompt_input[_LANGUAGE_KEY]

        if prompt_input.get(_PROMPT_ID_KEY) is not None:
            return self._materialize_prompt_by_id(
                slot,
                prompt_input,
                requested_language,
                current_prompt_id=current_prompt_id,
            )

        component = prompt_input.get(_COMPONENT_KEY)
        params = prompt_input.get(_PARAMS_KEY) or {}
        if not component:
            raise RAGPromptValidationError(
                "A prompt input must include 'prompt_id' or 'component'."
            )
        if not isinstance(params, dict):
            raise RAGPromptValidationError("Prompt parameters must be a dict.")
        # A default prompt may carry a blank template so its language text can
        # be injected later; any other type is a malformed payload rather than
        # a language selection, so it is rejected here for every caller.
        self.validate_prompt_params_shape(
            params, allow_missing=True, allow_blank_template=True
        )
        return self._materialize_prompt_by_component(
            slot, str(component), params, requested_language
        )

    def sync_session_bindings(
        self,
        session_id: int,
        parameters: dict[str, Any],
        prompt_inputs: dict[str, dict[str, Any]],
        *,
        generation_default: Optional[dict[str, Any]] = None,
    ) -> dict[str, dict[str, Any]]:
        """Bring a session's prompt bindings in line with its configuration.

        Every discovered slot either receives the supplied input, keeps its
        existing binding, or falls back to its default prompt. Bindings for
        slots that no longer exist are removed. Rows are flushed, not
        committed: the caller owns the transaction.

        Parameters
        ----------
        session_id : int
            Session whose bindings are updated.
        parameters : dict
            Prompt-free session configuration used to discover slots.
        prompt_inputs : dict
            Slot path to prompt input mapping, as produced by
            :meth:`split_prompts`.
        generation_default : dict, optional
            Default reference for the generation slot when none was supplied.
            Falls back to ``DefaultRAGGenerationPrompt`` with ``en``.

        Returns
        -------
        dict
            Snapshot of every bound slot, suitable for parameter history.

        Raises
        ------
        RAGPromptValidationError
            If an input names a slot the configuration does not declare, or a
            prompt cannot be resolved for its slot.
        """
        slots = self.discover_prompt_slots(parameters)
        unknown = sorted(set(prompt_inputs) - {slot.slot_path for slot in slots})
        if unknown:
            # A caller-supplied ``prompts`` map is keyed by slot path. An
            # unknown path would be dropped silently, so the client would think
            # its prompt had been saved.
            raise RAGPromptValidationError(
                "Unknown prompt slot(s): " + ", ".join(unknown) + "."
            )
        self._ensure_default_prompts(commit=False)

        existing = self._bindings_by_slot(session_id)
        active_paths: set[str] = set()
        snapshot: dict[str, dict[str, Any]] = {}

        for slot in slots:
            active_paths.add(slot.slot_path)
            binding = existing.get(slot.slot_path)
            prompt_input = prompt_inputs.get(slot.slot_path)

            if prompt_input is not None:
                row, language = self.materialize_prompt_input(
                    slot,
                    prompt_input,
                    current_prompt_id=(
                        binding.prompt_id if binding is not None else None
                    ),
                )
            elif binding is not None:
                row = self.db.get(RAGPrompt, binding.prompt_id)
                if row is None:
                    raise RAGPromptValidationError(
                        f"Prompt {binding.prompt_id} bound to slot "
                        f"{slot.slot_path} does not exist."
                    )
                # The registry may have changed since the binding was stored.
                # Never keep a row that is no longer a valid prompt for the
                # slot just because it was valid when it was first bound.
                row_class = self._prompt_class(row.class_name)
                if row_class is None or not issubclass(row_class, slot.expected_base):
                    raise RAGPromptValidationError(
                        f"Prompt {binding.prompt_id} bound to slot "
                        f"{slot.slot_path} is not valid for that slot."
                    )
                language = binding.language
            else:
                row, language = self._default_binding_for_slot(slot, generation_default)

            if binding is None:
                binding = RAGSessionPrompt(
                    session_id=session_id,
                    slot_path=slot.slot_path,
                    prompt_id=row.id,
                    language=language,
                )
                self.db.add(binding)
                existing[slot.slot_path] = binding
            else:
                binding.prompt_id = row.id
                binding.language = language

            snapshot[slot.slot_path] = self._binding_payload(row, language)

        for slot_path, binding in existing.items():
            if slot_path not in active_paths:
                self.db.delete(binding)

        self.db.flush()
        return snapshot

    @staticmethod
    def slot_top_level_key(slot_path: str) -> str:
        """Return the session parameter key a slot path lives under.

        Parameters
        ----------
        slot_path : str
            Stable slot path, for example ``query_transformation.prompt``.

        Returns
        -------
        str
            ``prompt`` for the generation slot, otherwise the first path
            segment (``query_transformation``, ``retriever_model``, ...).
        """
        if slot_path == _GENERATION_SLOT_PATH:
            return _PROMPT_KEY
        return slot_path.split(".", 1)[0]

    def apply_prompt_map(
        self, parameters: dict[str, Any], prompts: dict[str, Any]
    ) -> dict[str, Any]:
        """Place a ``prompts`` map inside a session configuration copy.

        The session API accepts prompts either embedded in ``parameters`` or as
        a separate slot-path map. The map has to be folded into the
        configuration *before* validation: a required nested slot (the query
        transformation prompt, for instance) is otherwise rejected before the
        map is ever consulted. Nothing is persisted.

        Parameters
        ----------
        parameters : dict
            Session configuration the map applies to.
        prompts : dict
            Slot path to prompt input (``{"component", "params"}`` or
            ``{"prompt_id"}``).

        Returns
        -------
        dict
            A copy of ``parameters`` with every mapped reference in place.

        Raises
        ------
        RAGPromptValidationError
            If a slot path is unknown, an input is malformed, the prompt class
            is not valid for the slot, or the referenced prompt is unusable.
        """
        target = copy.deepcopy(parameters) if isinstance(parameters, dict) else {}
        slots = {slot.slot_path: slot for slot in self.discover_prompt_slots(target)}
        unknown = sorted(set(prompts) - set(slots))
        if unknown:
            raise RAGPromptValidationError(
                "Unknown prompt slot(s): " + ", ".join(unknown) + "."
            )
        for slot_path, prompt_input in prompts.items():
            slot = slots[slot_path]
            reference = self._resolve_prompt_map_reference(slot, prompt_input)
            if slot_path == _GENERATION_SLOT_PATH:
                target[_PROMPT_KEY] = reference
            elif slot.container is not None and slot.key is not None:
                slot.container[slot.key] = reference
            else:
                raise RAGPromptValidationError(
                    f"Prompt slot {slot_path} cannot be configured."
                )
        return target

    def _resolve_prompt_map_reference(
        self, slot: PromptSlot, prompt_input: Any
    ) -> dict[str, Any]:
        """Validate one ``prompts`` map entry and resolve it to a reference.

        Parameters
        ----------
        slot : PromptSlot
            Slot the entry targets.
        prompt_input : Any
            ``{"prompt_id"}``, ``{"component", "params"}`` or a mix of both.

        Returns
        -------
        dict
            ``{"component", "params"}`` reference safe to place at the slot.

        Raises
        ------
        RAGPromptValidationError
            If the entry is malformed, its prompt class is not valid for the
            slot, or its template is invalid for that class.
        """
        if not isinstance(prompt_input, dict):
            raise RAGPromptValidationError(
                f"Prompt input for slot {slot.slot_path} must be a dict."
            )

        prompt_id = prompt_input.get(_PROMPT_ID_KEY)
        params = prompt_input.get(_PARAMS_KEY)
        if prompt_id is not None:
            reference = self.resolve_prompt_id_to_component(prompt_id)
            if params is not None:
                if not isinstance(params, dict):
                    raise RAGPromptValidationError("Prompt parameters must be a dict.")
                self.validate_prompt_params_shape(
                    params, allow_missing=True, allow_blank_template=False
                )
                reference = {
                    _COMPONENT_KEY: reference[_COMPONENT_KEY],
                    _PARAMS_KEY: {**reference[_PARAMS_KEY], **params},
                }
        else:
            component = prompt_input.get(_COMPONENT_KEY)
            if not isinstance(component, str) or not component:
                raise RAGPromptValidationError(
                    "A prompt input must include 'prompt_id' or 'component'."
                )
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise RAGPromptValidationError("Prompt parameters must be a dict.")
            self.validate_prompt_params_shape(
                params, allow_missing=True, allow_blank_template=False
            )
            reference = {_COMPONENT_KEY: component, _PARAMS_KEY: dict(params)}

        component = reference[_COMPONENT_KEY]
        self._validate_component_class(component, slot.expected_base)

        reference_params = reference[_PARAMS_KEY]
        templates = reference_params.get(_TEMPLATES_KEY)
        if isinstance(templates, dict) and templates:
            for template in templates.values():
                self.validate_prompt_template(component, template)
        template = reference_params.get(_TEMPLATE_KEY)
        if isinstance(template, str) and template.strip():
            self.validate_prompt_template(component, template)
        return reference

    def preview_session_bindings(
        self,
        session_id: int,
        parameters: dict[str, Any],
        prompt_inputs: dict[str, dict[str, Any]],
        *,
        generation_default: Optional[dict[str, Any]] = None,
    ) -> dict[str, dict[str, Any]]:
        """Return the bindings :meth:`sync_session_bindings` would produce.

        The bindings are computed inside a SAVEPOINT that is always rolled
        back, so the session keeps its current bindings. Callers use this to
        detect a no-op save before writing a history row.

        Parameters
        ----------
        session_id : int
            Session whose bindings are previewed.
        parameters : dict
            Prompt-free session configuration.
        prompt_inputs : dict
            Slot path to prompt input mapping.
        generation_default : dict, optional
            Default reference for the generation slot.

        Returns
        -------
        dict
            Slot path to binding snapshot, as the sync would store it.

        Raises
        ------
        RAGPromptValidationError
            If the sync itself would reject the configuration.
        """
        savepoint = self.db.begin_nested()
        try:
            return self.sync_session_bindings(
                session_id,
                parameters,
                prompt_inputs,
                generation_default=generation_default,
            )
        finally:
            savepoint.rollback()

    def prompt_id_for_slot(self, session_id: int, slot_path: str) -> Optional[int]:
        """Return the prompt id bound to one session slot.


        Parameters
        ----------
        session_id : int
            Session whose binding is read.
        slot_path : str
            Stable slot path, for example ``generation``.

        Returns
        -------
        int or None
            The bound prompt id, or ``None`` when the slot has no binding.
        """
        binding = (
            self.db.query(RAGSessionPrompt)
            .filter(
                RAGSessionPrompt.session_id == session_id,
                RAGSessionPrompt.slot_path == slot_path,
            )
            .first()
        )
        return binding.prompt_id if binding is not None else None

    def materialize_session_parameters(
        self, session_id: int, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a session configuration with its prompts populated.

        New sessions store prompt-free parameters and resolve prompts from
        ``rag_session_prompt``. Legacy sessions still carry their prompt
        references inside ``parameters``; those references are split in memory
        and injected as overrides so their content survives a read without
        rewriting the row. Nothing is committed.

        Parameters
        ----------
        session_id : int
            Session whose bindings are read.
        parameters : dict
            Stored session parameters, prompt-free or legacy.

        Returns
        -------
        dict
            A copy of ``parameters`` with every prompt slot populated.
        """
        stored = dict(parameters or {})
        clean, prompt_inputs = self.split_prompts(stored)
        if prompt_inputs:
            return self.inject_prompt_slots(session_id, clean, overrides=prompt_inputs)
        return self.inject_prompt_slots(session_id, stored)

    def materialize_history_parameters(
        self,
        parameters: dict[str, Any],
        prompt_bindings: Optional[dict[str, Any]],
        *,
        session_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Return a history entry's configuration with its own prompts injected.

        History entries written after the prompt redesign store prompt-free
        parameters plus a ``prompt_bindings`` snapshot. Each entry must be
        materialized from that snapshot, not from the session's current
        bindings, otherwise a prompt-only edit would not show up in the diff.
        Legacy entries that still carry their prompts inside ``parameters``
        are rendered from those; entries with neither are returned unchanged so
        the history never borrows a later prompt state.

        Parameters
        ----------
        parameters : dict
            Stored history parameters, prompt-free or legacy.
        prompt_bindings : dict or None
            Slot path to binding snapshot mapping captured with the entry.
        session_id : int, optional
            Session the entry belongs to. Only used to resolve legacy entries
            that still carry their prompts inside ``parameters``.

        Returns
        -------
        dict
            A copy of ``parameters`` with the snapshot's prompts injected.
        """
        if prompt_bindings:
            return self._inject_history_bindings(parameters, prompt_bindings)
        clean, prompt_inputs = self.split_prompts(parameters or {})
        if prompt_inputs and session_id is not None:
            return self.inject_prompt_slots(session_id, clean, overrides=prompt_inputs)
        return copy.deepcopy(parameters) if isinstance(parameters, dict) else {}

    def _inject_history_bindings(
        self, parameters: dict[str, Any], prompt_bindings: dict[str, Any]
    ) -> dict[str, Any]:
        """Inject a history entry's captured prompt snapshots into its params.

        Parameters
        ----------
        parameters : dict
            Prompt-free history parameters.
        prompt_bindings : dict
            Slot path to binding snapshot mapping.

        Returns
        -------
        dict
            A copy of ``parameters`` with every snapshot's prompt injected.
        """
        injected = copy.deepcopy(parameters) if isinstance(parameters, dict) else {}
        slots = {slot.slot_path: slot for slot in self.discover_prompt_slots(injected)}
        for slot_path, snapshot in prompt_bindings.items():
            slot = slots.get(slot_path)
            if slot is None:
                continue
            resolved = self._resolve_history_snapshot(snapshot)
            if slot_path == _GENERATION_SLOT_PATH:
                injected[_PROMPT_KEY] = resolved
            elif slot.container is not None and slot.key is not None:
                slot.container[slot.key] = resolved
        return injected

    @staticmethod
    def _resolve_history_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        """Resolve a history binding snapshot to a component reference.

        Default prompts store one template per language, so the snapshot's
        binding language selects the text. Library and draft prompts store
        their content directly.

        Parameters
        ----------
        snapshot : dict
            One entry of a ``prompt_bindings`` snapshot.

        Returns
        -------
        dict
            ``{"component", "params"}`` reference built from the snapshot.
        """
        class_name = snapshot.get("class_name")
        params = copy.deepcopy(snapshot.get("parameters") or {})
        if snapshot.get("is_default"):
            templates = params.get(_TEMPLATES_KEY)
            if isinstance(templates, dict) and templates:
                selected = snapshot.get(_LANGUAGE_KEY) or params.get(_LANGUAGE_KEY)
                if selected not in templates:
                    selected = params.get(_LANGUAGE_KEY)
                if selected not in templates:
                    selected = next(iter(templates), None)
                params = {_TEMPLATE_KEY: templates.get(selected)}
                if selected is not None:
                    params[_LANGUAGE_KEY] = selected
        return {_COMPONENT_KEY: class_name, _PARAMS_KEY: params}

    def inject_prompt_slots(
        self,
        session_id: int,
        parameters: dict[str, Any],
        *,
        bindings: Optional[dict[str, int]] = None,
        overrides: Optional[dict[str, dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Resolve a session's bindings into a prompt-populated configuration.

        The input parameters are deep-copied and every discovered slot is
        replaced by the resolved ``{"component", "params"}`` reference.
        Default prompts are resolved to the binding's language template.
        Nothing is persisted.

        Parameters
        ----------
        session_id : int
            Session whose bindings are read.
        parameters : dict
            Prompt-free configuration that already carries every container the
            discovered slots live under.
        bindings : dict, optional
            Slot path to prompt id override. Missing slots fall back to the
            stored binding and then to the slot's default.
        overrides : dict, optional
            Slot path to prompt input (``{"component", "params"}`` or
            ``{"prompt_id"}``) override. It wins over ``bindings``, the stored
            binding and the slot's default. Legacy sessions use this to
            re-inject prompts that still live inside their parameters.

        Returns
        -------
        dict
            A copy of ``parameters`` with every prompt slot populated.

        Raises
        ------
        RAGPromptValidationError
            If a binding is missing and no default exists, or a bound prompt is
            unusable.
        """
        injected = copy.deepcopy(parameters) if isinstance(parameters, dict) else {}
        id_overrides = bindings or {}
        input_overrides = overrides or {}
        stored = self._bindings_by_slot(session_id)

        for slot in self.discover_prompt_slots(injected):
            language: Optional[str] = None
            if slot.slot_path in input_overrides:
                resolved = self._resolve_override_input(
                    slot, input_overrides[slot.slot_path]
                )
            else:
                if slot.slot_path in id_overrides:
                    row = self.db.get(RAGPrompt, id_overrides[slot.slot_path])
                    if row is None:
                        raise RAGPromptValidationError(
                            f"Prompt {id_overrides[slot.slot_path]} does not exist."
                        )
                    if row.is_default:
                        language = (row.parameters or {}).get(_LANGUAGE_KEY)
                elif slot.slot_path in stored:
                    binding = stored[slot.slot_path]
                    row = self.db.get(RAGPrompt, binding.prompt_id)
                    if row is None:
                        raise RAGPromptValidationError(
                            f"Prompt {binding.prompt_id} bound to slot "
                            f"{slot.slot_path} does not exist."
                        )
                    language = binding.language
                else:
                    row, language = self._default_binding_for_slot(slot, None)

                resolved = self._resolve_prompt_row(row, language)

            if slot.slot_path == _GENERATION_SLOT_PATH:
                injected[_PROMPT_KEY] = resolved
            elif slot.container is not None and slot.key is not None:
                slot.container[slot.key] = resolved
            else:
                raise RAGPromptValidationError(
                    f"Prompt slot {slot.slot_path} cannot be injected."
                )

        return injected

    def _resolve_override_input(
        self, slot: PromptSlot, prompt_input: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve an in-memory prompt input for injection.

        Component-shaped inputs are returned verbatim so a legacy session
        round-trips byte-for-byte without touching the database. Inputs that
        only carry a ``prompt_id`` are resolved through the stored row.

        Parameters
        ----------
        slot : PromptSlot
            Slot the input belongs to.
        prompt_input : dict
            Prompt reference from a legacy session.

        Returns
        -------
        dict
            Resolved ``{"component", "params"}`` reference.

        Raises
        ------
        RAGPromptValidationError
            If the input is malformed or the referenced row is unusable.
        """
        if not isinstance(prompt_input, dict):
            raise RAGPromptValidationError("Prompt input must be a dict.")

        component = prompt_input.get(_COMPONENT_KEY)
        params = prompt_input.get(_PARAMS_KEY)
        if component and isinstance(params, dict):
            return copy.deepcopy(prompt_input)

        row, language = self.materialize_prompt_input(slot, prompt_input)
        return self._resolve_prompt_row(row, language)

    def list_bindings(self, session_id: int) -> dict[str, dict[str, Any]]:
        """Return the resolved snapshot of every binding of a session.

        Rows are read fresh, so edits to a library prompt are visible to every
        session bound to it. Ordering follows the slot path.

        Parameters
        ----------
        session_id : int
            Session whose bindings are listed.

        Returns
        -------
        dict
            Slot path to binding snapshot.
        """
        return snapshot_bindings(self.db, session_id)

    def snapshot_bindings(self, session_id: int) -> dict[str, dict[str, Any]]:
        """Alias of :meth:`list_bindings` for history writers.

        Parameters
        ----------
        session_id : int
            Session whose bindings are captured.

        Returns
        -------
        dict
            Slot path to binding snapshot.
        """
        return snapshot_bindings(self.db, session_id)

    def _bindings_by_slot(self, session_id: int) -> dict[str, RAGSessionPrompt]:
        """Return the binding row of every slot of a session.

        Parameters
        ----------
        session_id : int
            Session whose bindings are read.

        Returns
        -------
        dict
            Slot path to ``RAGSessionPrompt`` row.
        """
        result: dict[str, RAGSessionPrompt] = {}
        bindings = (
            self.db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.session_id == session_id)
            .all()
        )
        for binding in bindings:
            result[binding.slot_path] = binding
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _discover_slots_in_reference(
        self, reference: dict[str, Any], path: str, slots: list[PromptSlot]
    ) -> None:
        """Append the prompt slots declared by one component reference.

        Parameters
        ----------
        reference : dict
            ``{"component", "params"}`` reference being walked.
        path : str
            Slot path prefix of the reference.
        slots : list of PromptSlot
            Accumulator receiving the discovered slots.
        """
        component = reference.get(_COMPONENT_KEY)
        params = reference.get(_PARAMS_KEY)
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return

        slots.extend(self._component_prompt_slots(component, params, path))

        for key, value in params.items():
            child_path = f"{path}.{key}"
            if self._is_component_ref(value):
                if self._is_prompt_component(value.get(_COMPONENT_KEY)):
                    continue
                self._discover_slots_in_reference(value, child_path, slots)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if not self._is_component_ref(item):
                        continue
                    if self._is_prompt_component(item.get(_COMPONENT_KEY)):
                        continue
                    self._discover_slots_in_reference(
                        item, f"{child_path}[{index}]", slots
                    )

    def _component_prompt_slots(
        self, component: str, container: dict[str, Any], path: str
    ) -> list[PromptSlot]:
        """Return the prompt slots a component schema declares.

        A property becomes a slot when its placeholder is a prompt component
        reference. The placeholder's class supplies the slot's expected base
        prompt class.

        Parameters
        ----------
        component : str
            Registered component name.
        container : dict
            Component parameters dictionary that holds the prompt keys.
        path : str
            Slot path prefix of the component.

        Returns
        -------
        list of PromptSlot
            Slots declared by the component schema.
        """
        entry = self._component_entry(component)
        if entry is None:
            return []
        schema = entry.get("schema") or {}
        properties = schema.get("properties") or {}
        if not isinstance(properties, dict):
            return []

        slots: list[PromptSlot] = []
        for key, prop in properties.items():
            if not isinstance(prop, dict):
                continue
            placeholder = prop.get("placeholder")
            if not isinstance(placeholder, dict):
                continue
            default_component = placeholder.get(_COMPONENT_KEY)
            if not default_component:
                continue
            default_entry = self._component_entry(default_component)
            if default_entry is None:
                continue
            default_class = default_entry.get("class")
            if not isinstance(default_class, type) or not issubclass(
                default_class, BasePrompt
            ):
                continue
            slots.append(
                PromptSlot(
                    slot_path=f"{path}.{key}",
                    container=container,
                    key=key,
                    expected_base=self._expected_base_for(default_class),
                    default_component=default_component,
                )
            )
        return slots

    @staticmethod
    def _expected_base_for(prompt_class: type) -> type:
        """Return the first known base prompt class of ``prompt_class``."""
        for base in _PROMPT_BASE_CLASSES:
            if issubclass(prompt_class, base):
                return base
        return BasePrompt

    @staticmethod
    def _is_component_ref(value: Any) -> bool:
        """Whether ``value`` is a ``{"component", "params"}`` reference."""
        return (
            isinstance(value, dict) and _COMPONENT_KEY in value and _PARAMS_KEY in value
        )

    def _component_entry(self, component: Any) -> Optional[dict[str, Any]]:
        """Return the registry entry for a component name, if any."""
        if not isinstance(component, str) or not component:
            return None
        try:
            return self._registry[component]
        except (KeyError, TypeError):
            return None

    def _prompt_class(self, class_name: Any) -> Optional[type]:
        """Return the prompt class registered under ``class_name``."""
        entry = self._component_entry(class_name)
        if entry is None:
            return None
        prompt_class = entry.get("class")
        if not isinstance(prompt_class, type) or not issubclass(
            prompt_class, BasePrompt
        ):
            return None
        return prompt_class

    def _is_prompt_component(self, component: Any) -> bool:
        """Whether a component name resolves to a prompt class."""
        return self._prompt_class(component) is not None

    def _is_default_component(self, component: str) -> bool:
        """Whether a component is a code-owned default prompt."""
        entry = self._component_entry(component)
        if entry is None:
            return False
        prompt_class = entry.get("class")
        metadata = getattr(prompt_class, "metadata", None) or {}
        return metadata.get("variant") == "default" or component.startswith("Default")

    def _registered_default_template(
        self, class_name: Any, language: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """Return the canonical template registered for a default prompt class.

        Legacy rows may have lost the templates map (a language-only body, or a
        draft migrated from one). The code-owned ``metadata["templates"]`` is
        still authoritative for them.

        Parameters
        ----------
        class_name : Any
            Registered component name of the prompt class.
        language : str, optional
            Preferred language. Falls back to ``en`` and then to the first
            language the class declares.

        Returns
        -------
        tuple
            ``(template, language)``. Both are ``None`` when the class is not a
            registered default or declares no templates.
        """
        if not isinstance(class_name, str) or not class_name:
            return None, None
        prompt_class = self._prompt_class(class_name)
        if prompt_class is None:
            return None, None
        metadata = getattr(prompt_class, "metadata", None) or {}
        templates = metadata.get(_TEMPLATES_KEY)
        if not isinstance(templates, dict) or not templates:
            return None, None
        selected = language if language in templates else None
        if selected is None:
            selected = "en" if "en" in templates else next(iter(templates))
        template = templates.get(selected)
        if not isinstance(template, str) or not template:
            return None, None
        return template, selected

    @staticmethod
    def _has_usable_template(params: Any) -> bool:
        """Whether parameters carry text that can actually render.

        A legacy ``Default*`` input may carry ``{"language": "en", "template":
        ""}``: the keys are present but there is no text. Treating that as an
        edit would fork the default into an empty draft, so it counts as "no
        template" and binds the live default instead.

        Parameters
        ----------
        params : Any
            Prompt parameters to inspect.

        Returns
        -------
        bool
            ``True`` when a non-empty template string or templates map exists.
        """
        if not isinstance(params, dict):
            return False
        template = params.get(_TEMPLATE_KEY)
        if isinstance(template, str) and template.strip():
            return True
        templates = params.get(_TEMPLATES_KEY)
        return isinstance(templates, dict) and any(
            isinstance(value, str) and value.strip() for value in templates.values()
        )

    @classmethod
    def _template_matches_default(
        cls,
        default_row: RAGPrompt,
        params: dict[str, Any],
        language: Optional[str],
    ) -> bool:
        """Whether explicit parameters only restate a default's active text.

        The API resolves a default's ``template`` from its language when a
        session is validated, so a plain "use the English default" arrives as
        an explicit template equal to the row's own text. Such an input is not
        an edit and must keep the live default binding.

        Parameters
        ----------
        default_row : RAGPrompt
            Row flagged as a built-in default.
        params : dict
            Prompt parameters carrying an explicit ``template`` or
            ``templates`` map.
        language : str, optional
            Language selected for the binding.

        Returns
        -------
        bool
            ``True`` when the explicit text is the default's own text.
        """
        stored = default_row.parameters or {}
        stored_templates = stored.get(_TEMPLATES_KEY)
        if not isinstance(stored_templates, dict) or not stored_templates:
            return False

        explicit_templates = params.get(_TEMPLATES_KEY)
        if isinstance(explicit_templates, dict):
            return not cls._parameters_differ(explicit_templates, stored_templates)

        template = params.get(_TEMPLATE_KEY)
        if not isinstance(template, str):
            return False
        selected = language or stored.get(_LANGUAGE_KEY)
        if selected not in stored_templates:
            selected = stored.get(_LANGUAGE_KEY)
        if selected not in stored_templates:
            selected = next(iter(stored_templates), None)
        return selected is not None and stored_templates.get(selected) == template

    @staticmethod
    def _edit_parameters(params: dict[str, Any]) -> dict[str, Any]:
        """Return the content parameters an edit of a default should store.

        A default also carries a ``language`` selector, which is not part of
        the custom counterpart's content. Keeping only the template text keeps
        the draft identical to a normal custom prompt.
        """
        if _TEMPLATE_KEY in params:
            return {_TEMPLATE_KEY: params[_TEMPLATE_KEY]}
        if _TEMPLATES_KEY in params:
            return {_TEMPLATES_KEY: dict(params[_TEMPLATES_KEY])}
        return {}

    @staticmethod
    def _is_language_selection(params: Any) -> bool:
        """Whether parameters only select a language on a default prompt."""
        return isinstance(params, dict) and set(params) <= {_LANGUAGE_KEY}

    @staticmethod
    def _parameters_differ(
        params: dict[str, Any], stored: Optional[dict[str, Any]]
    ) -> bool:
        """Compare normalized parameter payloads."""
        return normalize_params(params or {}) != normalize_params(stored or {})

    @staticmethod
    def _binding_language(prompt: RAGPrompt, language: Optional[str]) -> Optional[str]:
        """Return the language a binding should store for ``prompt``."""
        if prompt.is_default:
            return language or (prompt.parameters or {}).get(_LANGUAGE_KEY)
        return language

    def _materialize_prompt_by_id(
        self,
        slot: PromptSlot,
        prompt_input: dict[str, Any],
        language: Optional[str],
        *,
        current_prompt_id: Optional[int] = None,
    ) -> tuple[RAGPrompt, Optional[str]]:
        """Resolve a prompt input that carries a ``prompt_id``."""
        prompt_id = self.require_prompt_id(prompt_input[_PROMPT_ID_KEY])
        row = self.db.get(RAGPrompt, prompt_id)
        if row is None:
            raise RAGPromptValidationError(
                f"Prompt with ID {prompt_id} does not exist."
            )

        row_class = self._prompt_class(row.class_name)
        if row_class is None or not issubclass(row_class, slot.expected_base):
            raise RAGPromptValidationError(
                f"Prompt {prompt_id} is not valid for slot {slot.slot_path}."
            )

        params = prompt_input.get(_PARAMS_KEY)
        has_params = isinstance(params, dict)
        is_draft = not row.is_default and not row.is_library
        # Drafts are content-addressed and session-local. Only the session that
        # already holds this draft may re-save it: otherwise session B could
        # adopt session A's private edit by guessing its id.
        if is_draft and row.id != current_prompt_id:
            raise RAGPromptValidationError(
                "Draft prompts cannot be selected directly; choose a "
                "library or default prompt."
            )

        if row.is_default and (not has_params or self._is_language_selection(params)):
            selected = language
            if selected is None and isinstance(params, dict):
                selected = params.get(_LANGUAGE_KEY)
            return row, self._binding_language(row, selected)

        if (
            has_params
            and self._has_usable_template(params)
            and self._template_matches_default(row, params, language)
        ):
            return row, self._binding_language(row, language)

        if has_params and self._parameters_differ(params, row.parameters):
            # Normalize the edit the same way the component path does: a
            # default edit stores only the template text, without the
            # language selector, so both paths produce one hash for the same
            # content.
            target_class = (
                self._fork_class_name(row) if row.is_default else row.class_name
            )
            draft_params = (
                self._edit_parameters(params)
                if row.is_default
                else normalize_params(params)
            )
            self._validate_prompt_parameters(target_class, draft_params)
            draft = self._get_or_create_content_row(
                target_class,
                draft_params,
                based_on_id=row.id if row.is_default else None,
            )
            return draft, None

        return row, self._binding_language(row, language)

    def _materialize_prompt_by_component(
        self,
        slot: PromptSlot,
        component: str,
        params: dict[str, Any],
        language: Optional[str],
    ) -> tuple[RAGPrompt, Optional[str]]:
        """Resolve a prompt input that carries a component configuration.

        A default component without an explicit template binds live to its
        default row, preserving the selected language. An explicit template is
        a session-local edit: the default's ``CUSTOM_CLASS`` counterpart is
        used and the resulting content-addressed draft records lineage through
        ``based_on_id``. A template that matches the default's active text is
        not an edit and keeps the live default binding. A non-default component
        is content-addressed, so equal content reuses one draft.

        Parameters
        ----------
        slot : PromptSlot
            Slot the input is being bound to. Its ``expected_base`` decides
            which prompt classes are legal.
        component : str
            Registered prompt component name of the input.
        params : dict
            Component parameters. For a default, an explicit ``template`` or
            ``templates`` map marks a session-local edit.
        language : str, optional
            Binding language selected for the input.

        Returns
        -------
        tuple
            The prompt row and the binding language (``None`` for non-default
            rows).

        Raises
        ------
        RAGPromptValidationError
            If the component is unregistered, is not valid for the slot, or its
            parameters are invalid.
        """
        self._validate_component_class(component, slot.expected_base)

        if self._is_default_component(component):
            selected = language
            if selected is None:
                selected = params.get(_LANGUAGE_KEY)
            if not self._has_usable_template(params):
                return self._default_row_for_component(component, language=selected)

            default_row, default_language = self._default_row_for_component(
                component, language=selected
            )
            if self._template_matches_default(default_row, params, selected):
                return default_row, default_language

            target_class = self._fork_class_name(default_row)
            draft_params = self._edit_parameters(params)
            self._validate_prompt_parameters(target_class, draft_params)
            draft = self._get_or_create_content_row(
                target_class,
                draft_params,
                based_on_id=default_row.id,
            )
            return draft, None

        self._validate_prompt_parameters(component, params)
        draft = self._get_or_create_content_row(component, params)
        return draft, None

    def _validate_component_class(self, component: str, expected_base: type) -> None:
        """Validate a component name and its base class for a slot."""
        prompt_class = self._prompt_class(component)
        if prompt_class is None:
            raise RAGPromptValidationError(
                f"Component {component} is not a valid Prompt subclass."
            )
        if not issubclass(prompt_class, expected_base):
            raise RAGPromptValidationError(
                f"Component {component} cannot be used for this prompt slot."
            )

    def _default_row_for_component(
        self,
        component: Optional[str],
        *,
        language: Optional[str] = None,
    ) -> tuple[RAGPrompt, Optional[str]]:
        """Return the default prompt row for a component.

        Parameters
        ----------
        component : str, optional
            Registered default prompt component.
        language : str, optional
            Binding language to store.

        Raises
        ------
        RAGPromptValidationError
            If no component is given or the default row is missing.
        """
        if not component:
            raise RAGPromptValidationError(
                "No default prompt component is available for this slot."
            )

        row = (
            self.db.query(RAGPrompt)
            .filter(
                RAGPrompt.class_name == component,
                RAGPrompt.is_default.is_(True),
            )
            # Legacy databases can hold more than one default row per class.
            # Ordering by id keeps the seeded canonical row deterministic;
            # ``_ensure_default_prompts`` demotes the non-canonical ones.
            .order_by(RAGPrompt.id)
            .first()
        )
        if row is None:
            # Read paths can run before the library has ever been opened, so a
            # missing built-in row is seeded here rather than reported.
            self._ensure_default_prompts(commit=False)
            row = (
                self.db.query(RAGPrompt)
                .filter(
                    RAGPrompt.class_name == component,
                    RAGPrompt.is_default.is_(True),
                )
                .order_by(RAGPrompt.id)
                .first()
            )
        if row is None:
            raise RAGPromptValidationError(
                f"Default prompt {component} is not registered or missing."
            )
        return row, self._binding_language(row, language)

    def _get_or_create_content_row(
        self,
        class_name: str,
        parameters: dict[str, Any],
        *,
        based_on_id: Optional[int] = None,
    ) -> RAGPrompt:
        """Find or create the internal draft row for some prompt content.

        The row is content-addressed by its class-aware hash, so equal content
        reuses one draft. ``based_on_id`` records lineage when the content was
        produced by editing a default prompt.

        Parameters
        ----------
        class_name : str
            Registered prompt component name. Entry content keeps whatever
            class the caller resolved, which may be a legacy ``Default*`` class
            for a migrated row.
        parameters : dict
            Prompt parameters. Normalized before hashing.
        based_on_id : int, optional
            Default prompt the content was edited from, when any. Only written
            onto a draft that has no lineage yet.

        Returns
        -------
        RAGPrompt
            The existing or newly inserted draft row.

        Raises
        ------
        RAGDatabaseError
            If the insert fails for a reason other than a concurrent duplicate.
        """
        normalized = normalize_params(parameters)
        existing = self._find_by_hash(class_name, normalized)
        if existing is not None:
            if (
                based_on_id is not None
                and not existing.is_default
                and not existing.is_library
                and existing.based_on_id is None
            ):
                existing.based_on_id = based_on_id
            return existing

        prompt = RAGPrompt(
            class_name=class_name,
            name=None,
            parameters=normalized,
            parameters_hash=build_prompt_hash(class_name, normalized),
            is_library=False,
            is_default=False,
            based_on_id=based_on_id,
        )
        try:
            with self.db.begin_nested():
                self.db.add(prompt)
        except exc.IntegrityError as error:
            # The SAVEPOINT rolled back only this insert; the caller's
            # transaction (and any earlier draft it created) is still alive.
            # Another request may have inserted the same content first.
            existing = self._find_by_hash(class_name, normalized)
            if existing is not None:
                return existing
            raise RAGDatabaseError("Error creating prompt draft.") from error
        return prompt

    def _default_binding_for_slot(
        self, slot: PromptSlot, generation_default: Optional[dict[str, Any]]
    ) -> tuple[RAGPrompt, Optional[str]]:
        """Return the prompt a slot should fall back to when unbound.

        The generation slot honours the caller's default reference (a component
        ref, a ``prompt_id``, or the built-in ``DefaultRAGGenerationPrompt``
        with ``en``). Every other slot uses the default component its own
        schema placeholder declares.

        Parameters
        ----------
        slot : PromptSlot
            Slot to bind.
        generation_default : dict, optional
            Default reference supplied for the generation slot, when any.

        Returns
        -------
        tuple
            The prompt row and the language the binding should store.

        Raises
        ------
        RAGPromptValidationError
            If the slot has no default prompt, or the supplied default
            reference is invalid or cannot be resolved.
        """
        if slot.slot_path == _GENERATION_SLOT_PATH:
            reference = generation_default or {
                _COMPONENT_KEY: _DEFAULT_GENERATION_COMPONENT,
                _PARAMS_KEY: {_LANGUAGE_KEY: _DEFAULT_GENERATION_LANGUAGE},
            }
            if _PROMPT_ID_KEY in reference:
                return self.materialize_prompt_input(slot, reference)

            component = reference.get(_COMPONENT_KEY)
            params = reference.get(_PARAMS_KEY) or {}
            if (
                component
                and self._is_default_component(component)
                and not self._has_usable_template(params)
            ):
                language = params.get(_LANGUAGE_KEY) or _DEFAULT_GENERATION_LANGUAGE
                return self._default_row_for_component(component, language=language)
            return self.materialize_prompt_input(slot, reference)

        if slot.default_component:
            return self._default_row_for_component(slot.default_component)
        raise RAGPromptValidationError(
            f"Prompt slot {slot.slot_path} has no default prompt."
        )

    def _resolve_prompt_row(
        self, prompt: RAGPrompt, language: Optional[str]
    ) -> dict[str, Any]:
        """Resolve a prompt row to a component reference for injection.

        Default rows are materialized with the binding's language template;
        library and draft rows use their stored template. A row whose class is
        a registered default but whose stored body carries no usable text (a
        legacy ``{"language": ...}`` row, or a draft migrated from one) reads
        the canonical text from the component's ``metadata["templates"]``.

        Args:
            prompt: Prompt row bound to the slot.
            language: Binding language, used to pick a default's template.

        Returns:
            ``{"component": class_name, "params": {"template": ...}}`` suitable
            for injecting into a session configuration.

        Raises:
            RAGPromptValidationError: If the row has no usable text and its
                class is not a registered default with a template catalog.
        """
        if not prompt.is_default:
            return self.resolve_prompt_id_to_component(prompt.id)

        parameters = prompt.parameters or {}
        templates = parameters.get(_TEMPLATES_KEY)
        if isinstance(templates, dict) and templates:
            selected = language or parameters.get(_LANGUAGE_KEY)
            if selected not in templates:
                selected = parameters.get(_LANGUAGE_KEY)
            if selected not in templates:
                selected = next(iter(templates), None)
            template = templates.get(selected) if selected is not None else None
            if template:
                resolved: dict[str, Any] = {_TEMPLATE_KEY: template}
                if selected is not None:
                    resolved[_LANGUAGE_KEY] = selected
                return {_COMPONENT_KEY: prompt.class_name, _PARAMS_KEY: resolved}

        # Legacy default rows may predate the templates map and only store the
        # text that was active when they were written. Returning it keeps old
        # sessions readable instead of failing on load.
        legacy_template = parameters.get(_TEMPLATE_KEY)
        if isinstance(legacy_template, str) and legacy_template:
            resolved = {_TEMPLATE_KEY: legacy_template}
            legacy_language = parameters.get(_LANGUAGE_KEY)
            if legacy_language is not None:
                resolved[_LANGUAGE_KEY] = legacy_language
            return {_COMPONENT_KEY: prompt.class_name, _PARAMS_KEY: resolved}

        if self._is_default_component(prompt.class_name):
            # The row lost its body (a language-only legacy default), but the
            # canonical text still exists in the code-owned metadata.
            template, selected = self._registered_default_template(
                prompt.class_name, language or parameters.get(_LANGUAGE_KEY)
            )
            if template:
                resolved = {_TEMPLATE_KEY: template}
                if selected is not None:
                    resolved[_LANGUAGE_KEY] = selected
                return {_COMPONENT_KEY: prompt.class_name, _PARAMS_KEY: resolved}

        raise RAGPromptValidationError(
            f"Default prompt {prompt.class_name} has no language templates."
        )

    @staticmethod
    def _binding_payload(prompt: RAGPrompt, language: Optional[str]) -> dict[str, Any]:
        """Serialize a binding's prompt row for history snapshots."""
        return {
            "prompt_id": prompt.id,
            "class_name": prompt.class_name,
            "name": prompt.name,
            "parameters": copy.deepcopy(prompt.parameters or {}),
            "is_default": bool(prompt.is_default),
            "is_library": bool(prompt.is_library),
            "language": language,
        }

    def _validate_prompt_parameters(
        self, class_name: str, parameters: dict[str, Any]
    ) -> None:
        """Validate that parameters carry templates valid for ``class_name``.

        Args:
            class_name: Registered prompt component name.
            parameters: Prompt configuration to validate.

        Raises:
            RAGPromptValidationError: If no template is present, the payload
                mixes ``template`` and ``templates``, a value is not a
                non-empty string, or a template is invalid for the prompt
                class.
        """
        self.validate_prompt_params_shape(
            parameters, allow_missing=False, allow_blank_template=False
        )
        templates = parameters.get(_TEMPLATES_KEY)
        if isinstance(templates, dict):
            for template in templates.values():
                self.validate_prompt_template(class_name, template)
            return
        self.validate_prompt_template(class_name, parameters[_TEMPLATE_KEY])

    def validate_prompt_params_shape(
        self,
        parameters: Any,
        *,
        allow_missing: bool = True,
        allow_blank_template: bool = True,
    ) -> None:
        """Type-check the ``template``/``templates`` part of prompt parameters.

        A prompt payload may carry a single ``template`` string or a
        ``templates`` map keyed by language. Mixing both is ambiguous, and a
        value of the wrong type would otherwise be coerced by the component
        schema (``123`` becomes ``"123"``) or silently ignored.

        Parameters
        ----------
        parameters : Any
            Prompt parameters to check.
        allow_missing : bool
            When ``True``, omitting both keys is accepted: a prompt input may
            only select a stored prompt or a default language.
        allow_blank_template : bool
            When ``True``, a ``None``/blank ``template`` is accepted. Default
            prompts use this because their language template is injected
            before schema validation.

        Raises
        ------
        RAGPromptValidationError
            If the payload is malformed.
        """
        if parameters is None:
            parameters = {}
        if not isinstance(parameters, dict):
            raise RAGPromptValidationError("Prompt parameters must be a dict.")

        has_template = _TEMPLATE_KEY in parameters
        has_templates = _TEMPLATES_KEY in parameters
        if has_template and has_templates:
            raise RAGPromptValidationError(
                "Prompt parameters must not include both 'template' and 'templates'."
            )
        if has_template:
            template = parameters[_TEMPLATE_KEY]
            if template is None:
                if allow_blank_template:
                    return
                raise RAGPromptValidationError("'template' must be a non-empty string.")
            if not isinstance(template, str):
                raise RAGPromptValidationError(
                    f"'template' must be a string, got {type(template).__name__}."
                )
            if not template.strip() and not allow_blank_template:
                raise RAGPromptValidationError("'template' must be a non-empty string.")
            return
        if has_templates:
            self._validate_templates_map(parameters[_TEMPLATES_KEY])
            return
        if not allow_missing:
            raise RAGPromptValidationError(
                "Prompt parameters must include 'template' or 'templates'."
            )

    @staticmethod
    def _validate_templates_map(templates: Any) -> None:
        """Check that a ``templates`` value maps languages to prompt text.

        Parameters
        ----------
        templates : Any
            Candidate ``templates`` value.

        Raises
        ------
        RAGPromptValidationError
            If the value is not a non-empty mapping of language keys to
            non-empty strings.
        """
        if not isinstance(templates, dict) or not templates:
            raise RAGPromptValidationError(
                "'templates' must be a non-empty object mapping languages to templates."
            )
        for language, template in templates.items():
            if not isinstance(language, str) or not language.strip():
                raise RAGPromptValidationError(
                    "'templates' keys must be non-empty language codes."
                )
            if not isinstance(template, str) or not template.strip():
                raise RAGPromptValidationError(
                    f"'templates' entry '{language}' must be a non-empty string."
                )

    @staticmethod
    def _active_template(parameters: dict[str, Any]) -> Optional[str]:
        """Return the template a multi-language prompt currently uses.

        Args:
            parameters: Prompt parameters.

        Returns:
            The single template, the template for the selected language, the
            first available language template, or ``None``.
        """
        template = parameters.get("template")
        if isinstance(template, str):
            return template
        templates = parameters.get("templates")
        if isinstance(templates, dict) and templates:
            language = parameters.get("language")
            if language in templates:
                return templates[language]
            return next(iter(templates.values()))
        return None

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
        if prompt.is_default:
            origin = _ORIGIN_DEFAULT
        elif prompt.is_library:
            origin = _ORIGIN_LIBRARY
        else:
            origin = _ORIGIN_DRAFT
        return PromptResponse(
            id=prompt.id,
            class_name=prompt.class_name,
            name=prompt.name,
            parameters=prompt.parameters,
            created=prompt.created,
            last_modified=prompt.last_modified,
            is_library=bool(prompt.is_library),
            is_default=bool(prompt.is_default),
            based_on_id=prompt.based_on_id,
            origin=origin,
            prompt_type=metadata.get("type"),
            prompt_subtype=metadata.get("technique"),
            sessions=sessions or [],
        )
