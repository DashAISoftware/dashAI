from typing import TYPE_CHECKING, Any, Dict, Type

from sqlalchemy.orm import Session

from DashAI.back.models.RAG.RAG_constants import RAG_WORKFLOW_NAME
from DashAI.back.services.workflows.base import (
    WorkflowSessionError,
    WorkflowSessionService,
)
from DashAI.back.services.workflows.RAG_workflow_session_service import (
    RAGWorkflowSessionService,
)

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry

_SERVICES: Dict[str, Type[WorkflowSessionService]] = {
    RAG_WORKFLOW_NAME: RAGWorkflowSessionService,
}


def session_service_for(
    workflow_name: str,
    db: Session,
    component_registry: "ComponentRegistry",
    job_queue: Any = None,
) -> WorkflowSessionService:
    """Return the session service of a workflow.

    Parameters
    ----------
    workflow_name : str
        Name of the session's workflow.
    db : Session
        Database session of the request.
    component_registry : ComponentRegistry
        Registry used to resolve components.
    job_queue : Any, optional
        Job queue, for workflows that run background jobs.

    Returns
    -------
    WorkflowSessionService
        The workflow's own service, or the pass through default for a
        workflow without one.
    """
    service_class = _SERVICES.get(workflow_name, WorkflowSessionService)
    return service_class(db, component_registry, job_queue)


def job_name_for(workflow_name: str) -> str:
    """Return the name of the job that runs a turn of a workflow's sessions.

    Parameters
    ----------
    workflow_name : str
        Name of the session's workflow.

    Returns
    -------
    str
        The registered job name.
    """
    return _SERVICES.get(workflow_name, WorkflowSessionService).JOB


__all__ = [
    "RAGWorkflowSessionService",
    "WorkflowSessionError",
    "WorkflowSessionService",
    "job_name_for",
    "session_service_for",
]
