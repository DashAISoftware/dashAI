from typing import Any, Dict, Optional

from DashAI.back.dependencies.database.models import GenerativeSession
from DashAI.back.models.RAG.exceptions.base import RAGWorkflowError
from DashAI.back.models.RAG.RAG_constants import (
    RAG_PARAM_DOCUMENTS,
    RAG_PARAM_GENERATION_MODEL,
)
from DashAI.back.services.RAG.cleanup_service import CleanupService
from DashAI.back.services.RAG.index_job_service import cancel_live_index_job
from DashAI.back.services.RAG.session_validation_service import (
    SessionValidationService,
)
from DashAI.back.services.workflows.base import (
    WorkflowSessionError,
    WorkflowSessionService,
)

NO_DOCUMENTS_MESSAGE = (
    "Add at least one document to this session before sending a message."
)


class RAGWorkflowSessionService(WorkflowSessionService):
    """Session lifecycle of the RAG workflow.

    The session model is the generation LLM its ``generation_model``
    parameter names, and ``RAGJob`` runs each turn. Creation fills the RAG
    defaults and updates are validated strictly, component by component,
    cleaning up the indexes they invalidate; a turn needs at least one
    document, and deletion stops the index and sweeps the RAG rows the
    session owned.
    """

    JOB = "RAGJob"

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
    ) -> Dict[str, Any]:
        """Validate a new RAG session and fill the components left out.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Parameters sent by the client.
        language : Optional[str]
            Client language, used for the default prompt templates.

        Returns
        -------
        Dict[str, Any]
            The normalized parameters.

        Raises
        ------
        WorkflowSessionError
            When the parameters are invalid.
        """
        try:
            return self._validator().prepare_RAG_params(parameters, language)
        except (ValueError, RAGWorkflowError) as error:
            raise WorkflowSessionError(str(error)) from error

    def validate_update(
        self,
        session: GenerativeSession,
        new_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate a partial RAG update without touching any index.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        new_parameters : Dict[str, Any]
            Partial parameters sent by the client.

        Returns
        -------
        Dict[str, Any]
            The normalized partial parameters.

        Raises
        ------
        WorkflowSessionError
            When the update is invalid.
        """
        try:
            return self._validator().validate_update_payload(new_parameters)
        except (ValueError, RAGWorkflowError) as error:
            raise WorkflowSessionError(str(error)) from error

    def apply_update(
        self,
        session: GenerativeSession,
        old_parameters: Dict[str, Any],
        updated_parameters: Dict[str, Any],
    ) -> None:
        """Stop a running index, then delete what the update orphaned.

        The index job writes the very rows the cleanup deletes, so it is
        stopped first.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        old_parameters : Dict[str, Any]
            Parameters before the update.
        updated_parameters : Dict[str, Any]
            Parameters after the update.
        """
        cancel_live_index_job(session, self.job_queue)
        CleanupService(self.db).cleanup_orphaned_resources(
            session.id, old_parameters, updated_parameters
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

    def before_delete(self, session: GenerativeSession) -> None:
        """Stop the index and discard the session's chunk sets, uncommitted.

        Parameters
        ----------
        session : GenerativeSession
            Session about to be deleted.
        """
        cancel_live_index_job(session, self.job_queue)
        CleanupService(self.db).invalidate_session_artifacts(session.id, commit=False)

    def after_delete(self, session_id: int, old_parameters: Dict[str, Any]) -> None:
        """Delete the shared RAG rows the deleted session left unused.

        Commits, so it runs once the deletion itself is staged or committed.

        Parameters
        ----------
        session_id : int
            Id of the deleted session.
        old_parameters : Dict[str, Any]
            Parameters the session had.
        """
        CleanupService(self.db).cleanup_orphaned_resources(session_id, old_parameters)
