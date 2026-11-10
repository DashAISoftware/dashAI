from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import GenerativeSession

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry


class WorkflowSessionError(ValueError):
    """A session request the workflow refuses; its message is shown to the user."""


class WorkflowSessionService:
    """Session lifecycle steps a workflow adds to the generic session endpoints.

    The defaults are the inference behaviour: parameters pass through as sent
    and nothing happens around updates, turns or deletion. A workflow that
    needs more subclasses this and registers the subclass with
    ``session_service_for``.

    Parameters
    ----------
    db : Session
        Database session of the request.
    component_registry : ComponentRegistry
        Registry used to resolve components.
    job_queue : Any, optional
        Job queue, for workflows that run background jobs.
    """

    def __init__(
        self,
        db: Session,
        component_registry: "ComponentRegistry",
        job_queue: Any = None,
    ) -> None:
        self.db = db
        self.component_registry = component_registry
        self.job_queue = job_queue

    def prepare_parameters(
        self,
        parameters: Dict[str, Any],
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate and complete the parameters of a new session.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Parameters sent by the client.
        language : Optional[str]
            Client language, for language dependent defaults.

        Returns
        -------
        Dict[str, Any]
            The parameters to store.
        """
        return parameters

    def validate_update(
        self,
        session: GenerativeSession,
        new_parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate a partial parameter update without side effects.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        new_parameters : Dict[str, Any]
            Partial parameters sent by the client.

        Returns
        -------
        Dict[str, Any]
            The parameters to merge over the stored ones.
        """
        return new_parameters

    def apply_update(
        self,
        session: GenerativeSession,
        old_parameters: Dict[str, Any],
        updated_parameters: Dict[str, Any],
    ) -> None:
        """Run the side effects of an accepted update, before it is stored.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        old_parameters : Dict[str, Any]
            Parameters before the update.
        updated_parameters : Dict[str, Any]
            Parameters after the update.
        """

    def check_ready(self, session: GenerativeSession) -> None:
        """Refuse a turn the session cannot answer yet.

        Parameters
        ----------
        session : GenerativeSession
            Session about to receive a turn.

        Raises
        ------
        WorkflowSessionError
            When the session cannot answer yet.
        """

    def before_delete(self, session: GenerativeSession) -> None:
        """Release what the session owns, inside the deleting transaction.

        Parameters
        ----------
        session : GenerativeSession
            Session about to be deleted.
        """

    def after_delete(self, session_id: int, old_parameters: Dict[str, Any]) -> None:
        """Sweep what the deleted session left unused.

        Parameters
        ----------
        session_id : int
            Id of the deleted session.
        old_parameters : Dict[str, Any]
            Parameters the session had.
        """
