from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    GenerativeSessionParameterHistory,
    ProcessData,
)

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry


class WorkflowSessionError(ValueError):
    """A session request the workflow refuses; its message is shown to the user."""


class WorkflowConflictError(Exception):
    """A request that conflicts with what the session already stores."""


class WorkflowStorageError(RuntimeError):
    """The workflow could not read or write its own rows; a server fault."""


class WorkflowSessionService:
    """Session lifecycle steps a workflow adds to the generic session endpoints.

    The defaults are the inference behaviour: the session model is the one the
    client picks, its own schema validates the parameters, ``GenerativeJob``
    runs each turn, the session has no prompts and nothing happens around
    updates, turns or deletion. A workflow that needs more subclasses this and
    registers the subclass with ``session_service_for``.

    Parameters
    ----------
    db : Session
        Database session of the request.
    component_registry : ComponentRegistry
        Registry used to resolve components.
    job_queue : Any, optional
        Job queue, for workflows that run background jobs.

    Attributes
    ----------
    JOB : str
        Name of the registered job that runs a turn.
    """

    JOB: str = "GenerativeJob"

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
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate and complete the parameters of a new session.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Parameters sent by the client.
        language : Optional[str]
            Client language, for language dependent defaults.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent next to the parameters.

        Returns
        -------
        Dict[str, Any]
            The complete parameters.
        """
        return parameters

    def stored_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Return the part of the parameters the session row stores.

        Parameters
        ----------
        parameters : Dict[str, Any]
            Complete parameters.

        Returns
        -------
        Dict[str, Any]
            The parameters to store; all of them by default.
        """
        return dict(parameters)

    def bind_new_session(
        self,
        session: GenerativeSession,
        parameters: Dict[str, Any],
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Store what a new, flushed session keeps outside its row.

        Parameters
        ----------
        session : GenerativeSession
            The new session, flushed but not committed.
        parameters : Dict[str, Any]
            Complete parameters returned by ``prepare_parameters``.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        Optional[Dict[str, Any]]
            Snapshot of the session's prompts for its history, or ``None``
            when the workflow has no prompts.
        """
        return None

    def client_parameters(
        self, session: GenerativeSession, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return stored parameters in the shape the client edits.

        Parameters
        ----------
        session : GenerativeSession
            The session.
        parameters : Dict[str, Any]
            Stored parameters.

        Returns
        -------
        Dict[str, Any]
            The parameters to send back; unchanged by default.
        """
        return parameters

    def read_parameters(
        self, session: GenerativeSession
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Return a stored session's parameters and prompts for the client.

        Parameters
        ----------
        session : GenerativeSession
            The stored session.

        Returns
        -------
        Tuple[Dict[str, Any], Optional[Dict[str, Any]]]
            The parameters and the prompt bindings, ``None`` without prompts.
        """
        return dict(session.parameters or {}), None

    def snapshot_prompts(self, session: GenerativeSession) -> Optional[Dict[str, Any]]:
        """Return the prompts a new history entry of the session records.

        Parameters
        ----------
        session : GenerativeSession
            The session.

        Returns
        -------
        Optional[Dict[str, Any]]
            The prompt bindings, ``None`` without prompts.
        """
        return None

    def history_parameters(
        self,
        session: GenerativeSession,
        entry: GenerativeSessionParameterHistory,
    ) -> Dict[str, Any]:
        """Return the parameters a history entry shows the client.

        Parameters
        ----------
        session : GenerativeSession
            The session the entry belongs to.
        entry : GenerativeSessionParameterHistory
            The history entry.

        Returns
        -------
        Dict[str, Any]
            The entry's parameters.
        """
        return dict(entry.parameters or {})

    def model_name_from(self, parameters: Optional[Dict[str, Any]]) -> Optional[str]:
        """Return the model the session parameters name, if any.

        Parameters
        ----------
        parameters : Optional[Dict[str, Any]]
            Session parameters.

        Returns
        -------
        Optional[str]
            ``None``: the session model is the one the client picks.
        """
        return None

    def check_parameters(self, model_class: type, parameters: Dict[str, Any]) -> None:
        """Validate complete session parameters before they are stored.

        Parameters
        ----------
        model_class : type
            Class of the session model.
        parameters : Dict[str, Any]
            The parameters to store.

        Raises
        ------
        ValueError
            When the model's schema rejects them.
        """
        model_class.SCHEMA.model_validate(parameters)

    def validate_update(
        self,
        session: GenerativeSession,
        new_parameters: Dict[str, Any],
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate a partial parameter update without side effects.

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
            The validated changes.
        """
        return new_parameters

    def is_unchanged(
        self,
        session: GenerativeSession,
        old_parameters: Dict[str, Any],
        updated_parameters: Dict[str, Any],
        changes: Dict[str, Any],
        prompts: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Whether an accepted update leaves the session as it was.

        An unchanged update is answered without a new history entry.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        old_parameters : Dict[str, Any]
            Stored parameters before the update.
        updated_parameters : Dict[str, Any]
            Stored parameters after the update.
        changes : Dict[str, Any]
            Changes returned by ``validate_update``.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        bool
            ``False``: every update is recorded by default.
        """
        return False

    def apply_update(
        self,
        session: GenerativeSession,
        old_parameters: Dict[str, Any],
        updated_parameters: Dict[str, Any],
        changes: Optional[Dict[str, Any]] = None,
        prompts: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run the side effects of an accepted update, before it is stored.

        Parameters
        ----------
        session : GenerativeSession
            Session being updated.
        old_parameters : Dict[str, Any]
            Stored parameters before the update.
        updated_parameters : Dict[str, Any]
            Stored parameters after the update.
        changes : Optional[Dict[str, Any]]
            Changes returned by ``validate_update``.
        prompts : Optional[Dict[str, Any]]
            Slot path to prompt input map sent by the client.

        Returns
        -------
        Optional[Dict[str, Any]]
            Snapshot of the session's prompts for its history, or ``None``
            when the workflow has no prompts.
        """
        return None

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

    def delete(self, session: GenerativeSession) -> None:
        """Stage the deletion of a session and every row it owns, uncommitted.

        Deletes the session's processes with their data, its parameter history
        and the session itself; the caller commits.

        Parameters
        ----------
        session : GenerativeSession
            Session to delete.
        """
        processes = (
            self.db.query(GenerativeProcess)
            .filter(GenerativeProcess.session_id == session.id)
            .all()
        )
        for process in processes:
            self.db.query(ProcessData).filter(
                ProcessData.process_id == process.id
            ).delete(synchronize_session="fetch")
        for process in processes:
            self.db.delete(process)
        self.db.query(GenerativeSessionParameterHistory).filter(
            GenerativeSessionParameterHistory.session_id == session.id
        ).delete(synchronize_session="fetch")
        self.db.delete(session)
