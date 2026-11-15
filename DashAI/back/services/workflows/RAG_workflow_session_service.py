import copy
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional, Tuple

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    GenerativeSessionParameterHistory,
)
from DashAI.back.models.RAG.exceptions import (
    RAGDatabaseError,
    RAGPromptValidationError,
    RAGWorkflowError,
)
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PARAM_DOCUMENTS,
    RAG_PARAM_GENERATION_MODEL,
)
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.index_job_service import cancel_live_index_job
from DashAI.back.services.RAG.prompt_service import (
    PromptConflictError,
    PromptService,
)
from DashAI.back.services.RAG.session_document_service import (
    SessionDocumentService,
)
from DashAI.back.services.RAG.session_validation_service import (
    SessionValidationService,
)
from DashAI.back.services.workflows.base import (
    WorkflowConflictError,
    WorkflowSessionError,
    WorkflowSessionService,
    WorkflowStorageError,
)

NO_DOCUMENTS_MESSAGE = (
    "Add at least one document to this session before sending a message."
)


class RAGWorkflowSessionService(WorkflowSessionService):
    """Session lifecycle of the RAG workflow.

    The session model is the generation LLM its ``generation_model``
    parameter names, and ``RAGJob`` runs each turn. Creation fills the RAG
    defaults and updates are validated strictly, component by component,
    cleaning up the indexes they invalidate. Prompts live in their own table:
    the session row stores prompt free parameters and each prompt slot is
    bound to a stored prompt. A turn needs at least one document, and
    deletion stops the index and removes every RAG row the session owned.
    """

    JOB = "RAGJob"

    _prompt_service: Optional[PromptService] = None

    @property
    def prompts(self) -> PromptService:
        """Prompt service bound to this request.

        Returns
        -------
        PromptService
            The service, created on first use.
        """
        if self._prompt_service is None:
            self._prompt_service = PromptService(self.db, self.component_registry)
        return self._prompt_service

    @staticmethod
    @contextmanager
    def _write_errors() -> Iterator[None]:
        """Translate RAG errors raised while writing a session.

        Raises
        ------
        WorkflowConflictError
            When a prompt collides with a stored one.
        WorkflowStorageError
            When the RAG rows cannot be read or written.
        WorkflowSessionError
            When the request is otherwise invalid.
        """
        try:
            yield
        except PromptConflictError as error:
            raise WorkflowConflictError(str(error)) from error
        except RAGDatabaseError as error:
            raise WorkflowStorageError(str(error)) from error
        except WorkflowSessionError:
            raise
        except (RAGWorkflowError, ValueError, LookupError) as error:
            raise WorkflowSessionError(str(error)) from error

    @staticmethod
    @contextmanager
    def _read_errors() -> Iterator[None]:
        """Translate an unusable stored prompt into a state conflict.

        Raises
        ------
        WorkflowConflictError
            When a stored prompt cannot be resolved.
        """
        try:
            yield
        except RAGPromptValidationError as error:
            raise WorkflowConflictError(str(error)) from error

    def _prompt_inputs(
        self,
        parameters: Optional[Dict[str, Any]],
        prompts: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Collect the prompt inputs of a request.

        Parameters
        ----------
        parameters : Optional[Dict[str, Any]]
            Parameters that may embed prompts.
        prompts : Optional[Dict[str, Any]]
            Explicit slot path to prompt input map; it wins over embedded
            prompts.

        Returns
        -------
        Dict[str, Any]
            Prompt inputs keyed by slot path.
        """
        _, inputs = self.prompts.split_prompts(dict(parameters or {}))
        if isinstance(prompts, dict):
            inputs.update(prompts)
        return inputs

    def model_name_from(self, parameters: Optional[Dict[str, Any]]) -> Optional[str]:
        """Return the generation LLM the parameters name.

        Parameters
        ----------
        parameters : Optional[Dict[str, Any]]
            Session parameters.

        Returns
        -------
        Optional[str]
            The component of ``generation_model``, or ``None`` when it is
            missing or malformed.
        """
        if not isinstance(parameters, dict):
            return None
        reference = parameters.get(RAG_PARAM_GENERATION_MODEL)
        if not isinstance(reference, dict):
            return None
        component = reference.get("component")
        return component if isinstance(component, str) and component else None

    def check_parameters(self, model_class: type, parameters: Dict[str, Any]) -> None:
        """Accept parameters already validated component by component.

        ``prepare_parameters`` and ``validate_update`` check every component
        reference against its own schema, so the LLM's schema, which covers
        only ``generation_model``, has nothing to add.

        Parameters
        ----------
        model_class : type
            Class of the generation LLM.
        parameters : Dict[str, Any]
            The parameters to store.
        """

    def _validator(self) -> SessionValidationService:
        """Build the RAG validation service for this request.

        Returns
        -------
        SessionValidationService
            Validator bound to this request's database and registry.
        """
        return SessionValidationService(self.db, self.component_registry)

    def prepare_parameters(
        self,
        parameters: Dict[str, Any],
        language: Optional[str] = None,
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate a new RAG session and fill the components left out.

        A prompt sent only through ``prompts`` is placed at its slot first, so
        a required nested slot can be configured from scratch.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Parameters sent by the client.
        language : Optional[str]
            Client language, used for the default prompt templates.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        Dict[str, Any]
            The normalized parameters, prompts included.

        Raises
        ------
        WorkflowSessionError
            When the parameters are invalid.
        WorkflowConflictError
            When a prompt collides with a stored one.
        """
        with self._write_errors():
            if isinstance(prompts, dict):
                parameters = self.prompts.apply_prompt_map(parameters, prompts)
            return self._validator().prepare_RAG_params(parameters, language)

    def stored_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Return the parameters without their prompts.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Parameters that may embed prompts.

        Returns
        -------
        Dict[str, Any]
            The prompt free parameters.
        """
        with self._write_errors():
            clean, _ = self.prompts.split_prompts(dict(parameters))
        return clean

    def bind_new_session(
        self,
        session: GenerativeSession,
        parameters: Dict[str, Any],
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Bind every prompt slot of a new session to a stored prompt.

        Parameters
        ----------
        session : GenerativeSession
            The new session, flushed but not committed.
        parameters : Dict[str, Any]
            Complete parameters, prompts included.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map; it wins over embedded prompts.

        Returns
        -------
        Optional[Dict[str, Any]]
            The bindings snapshot.
        """
        with self._write_errors():
            return self.prompts.sync_session_bindings(
                session.id,
                self.stored_parameters(parameters),
                self._prompt_inputs(parameters, prompts),
                generation_default=parameters.get("prompt"),
            )

    def client_parameters(
        self, session: GenerativeSession, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Inject the bound prompts into prompt free parameters.

        Materializing before the commit makes a prompt that cannot be rendered
        fail the request instead of the next read.

        Parameters
        ----------
        session : GenerativeSession
            The session.
        parameters : Dict[str, Any]
            Prompt free parameters.

        Returns
        -------
        Dict[str, Any]
            The parameters with their prompts.
        """
        with self._write_errors():
            return self.prompts.inject_prompt_slots(session.id, parameters)

    def read_parameters(
        self, session: GenerativeSession
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Return the session parameters with prompts, and its bindings.

        Prompts come from storage, or from the parameters of a legacy session.

        Parameters
        ----------
        session : GenerativeSession
            The stored session.

        Returns
        -------
        Tuple[Dict[str, Any], Optional[Dict[str, Any]]]
            The materialized parameters and the resolved bindings.

        Raises
        ------
        WorkflowConflictError
            When a stored prompt cannot be resolved.
        """
        with self._read_errors():
            parameters = self.prompts.materialize_session_parameters(
                session.id, dict(session.parameters or {})
            )
            return parameters, self.prompts.list_bindings(session.id)

    def snapshot_prompts(self, session: GenerativeSession) -> Optional[Dict[str, Any]]:
        """Return the bindings a new history entry records.

        Parameters
        ----------
        session : GenerativeSession
            The session.

        Returns
        -------
        Optional[Dict[str, Any]]
            The bindings snapshot.
        """
        with self._write_errors():
            return self.prompts.snapshot_bindings(session.id)

    def history_parameters(
        self,
        session: GenerativeSession,
        entry: GenerativeSessionParameterHistory,
    ) -> Dict[str, Any]:
        """Return a history entry's parameters with the prompts it recorded.

        Parameters
        ----------
        session : GenerativeSession
            The session the entry belongs to.
        entry : GenerativeSessionParameterHistory
            The history entry.

        Returns
        -------
        Dict[str, Any]
            The materialized parameters.

        Raises
        ------
        WorkflowConflictError
            When a recorded prompt cannot be resolved.
        """
        with self._read_errors():
            return self.prompts.materialize_history_parameters(
                dict(entry.parameters or {}),
                getattr(entry, "prompt_bindings", None),
                session_id=session.id,
            )

    def validate_update(
        self,
        session: GenerativeSession,
        new_parameters: Dict[str, Any],
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate a partial RAG update without touching any index.

        A ``prompts`` map is folded into a candidate configuration first, so a
        prompt can be sent for a slot the request does not repeat; only the
        keys the request or the map touches are validated, keeping partial
        update semantics.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        new_parameters : Dict[str, Any]
            Partial parameters sent by the client.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        Dict[str, Any]
            The normalized partial parameters, prompts included.

        Raises
        ------
        WorkflowSessionError
            When the update is invalid.
        WorkflowConflictError
            When a prompt collides with a stored one.
        """
        payload = new_parameters
        if isinstance(prompts, dict):
            with self._write_errors():
                candidate = {
                    **copy.deepcopy(
                        self.stored_parameters(dict(session.parameters or {}))
                    ),
                    **copy.deepcopy(new_parameters),
                }
                prepared = self.prompts.apply_prompt_map(candidate, prompts)
                touched = set(new_parameters) | {
                    self.prompts.slot_top_level_key(path) for path in prompts
                }
                payload = {
                    key: prepared.get(key, new_parameters.get(key)) for key in touched
                }
        try:
            return self._validator().validate_update_payload(payload)
        except (ValueError, RAGWorkflowError) as error:
            raise WorkflowSessionError(str(error)) from error

    def is_unchanged(
        self,
        session: GenerativeSession,
        old_parameters: Dict[str, Any],
        updated_parameters: Dict[str, Any],
        changes: Dict[str, Any],
        prompts: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Whether the update changes neither the configuration nor a prompt.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        old_parameters : Dict[str, Any]
            Prompt free parameters before the update.
        updated_parameters : Dict[str, Any]
            Prompt free parameters after the update.
        changes : Dict[str, Any]
            Changes returned by ``validate_update``.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        bool
            True when the save would record nothing new.
        """
        if updated_parameters != old_parameters:
            return False
        with self._write_errors():
            preview = self.prompts.preview_session_bindings(
                session.id,
                updated_parameters,
                self._prompt_inputs(changes, prompts),
                generation_default=changes.get("prompt"),
            )
            return preview == self.prompts.snapshot_bindings(session.id)

    def apply_update(
        self,
        session: GenerativeSession,
        old_parameters: Dict[str, Any],
        updated_parameters: Dict[str, Any],
        changes: Optional[Dict[str, Any]] = None,
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Stop a running index, delete what the update orphaned, bind prompts.

        The index job writes the very rows the cleanup deletes, so it is
        stopped first. Both parameter sets are prompt free, so editing a
        prompt never invalidates the retriever or the index. Nothing is
        committed: the update, the bindings and the history entry share one
        transaction.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        old_parameters : Dict[str, Any]
            Prompt free parameters before the update.
        updated_parameters : Dict[str, Any]
            Prompt free parameters after the update.
        changes : Optional[Dict[str, Any]]
            Changes returned by ``validate_update``.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        Optional[Dict[str, Any]]
            The bindings snapshot.
        """
        changes = changes or {}
        cancel_live_index_job(session, self.job_queue)
        CleanupService(self.db).cleanup_orphaned_resources(
            session.id, old_parameters, updated_parameters, commit=False
        )
        with self._write_errors():
            return self.prompts.sync_session_bindings(
                session.id,
                updated_parameters,
                self._prompt_inputs(changes, prompts),
                generation_default=changes.get("prompt"),
            )

    def check_ready(self, session: GenerativeSession) -> None:
        """Refuse a turn on a session with no documents.

        Answering here beats letting the job fit an index over no text.

        Parameters
        ----------
        session : GenerativeSession
            Session about to receive a turn.

        Raises
        ------
        WorkflowSessionError
            When the session has no documents.
        """
        if not ((session.parameters or {}).get(RAG_PARAM_DOCUMENTS) or []):
            raise WorkflowSessionError(NO_DOCUMENTS_MESSAGE)

    def delete(self, session: GenerativeSession) -> None:
        """Stage the deletion of a session and every RAG row it owns.

        Stops the index and removes the processes, history, document links,
        prompt bindings, chunk sets and pipeline of the session, uncommitted.

        Parameters
        ----------
        session : GenerativeSession
            Session to delete.
        """
        SessionDocumentService(self.db, self.job_queue).delete_session(
            session.id, commit=False
        )
