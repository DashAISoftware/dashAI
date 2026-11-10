"""Unit tests for the per workflow session services.

The generic session endpoints call these hooks instead of branching on RAG.
The inference service is a pass through; the RAG service delegates to the RAG
validation, index and cleanup services. Those collaborators touch the job queue
and the RAG tables, so they are replaced by recording fakes here; the API
suites exercise them for real.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.dependencies.database.models import Base, GenerativeSession
from DashAI.back.models.RAG.exceptions.base import RAGWorkflowError
from DashAI.back.services.workflows import RAG_workflow_session_service as rag_module
from DashAI.back.services.workflows import (
    RAGWorkflowSessionService,
    WorkflowSessionError,
    WorkflowSessionService,
    session_service_for,
)


class FakeValidator:
    """Stands in for ``SessionValidationService``, recording every call."""

    calls: List[tuple] = []
    result: Dict[str, Any] = {}
    error: Optional[Exception] = None

    def __init__(self, db: Any, registry: Any) -> None:
        """Remember the collaborators the service was built with.

        Parameters
        ----------
        db : Any
            Database session.
        registry : Any
            Component registry.
        """
        FakeValidator.calls.append(("init", db, registry))

    def prepare_RAG_params(  # noqa: N802
        self, raw_params: Dict[str, Any], accept_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a creation request.

        Parameters
        ----------
        raw_params : Dict[str, Any]
            Parameters sent by the client.
        accept_language : Optional[str]
            Client language.

        Returns
        -------
        Dict[str, Any]
            The configured result.
        """
        FakeValidator.calls.append(("prepare", raw_params, accept_language))
        if FakeValidator.error is not None:
            raise FakeValidator.error
        return FakeValidator.result

    def validate_update_payload(self, new_params: Dict[str, Any]) -> Dict[str, Any]:
        """Record an update request.

        Parameters
        ----------
        new_params : Dict[str, Any]
            Partial parameters sent by the client.

        Returns
        -------
        Dict[str, Any]
            The configured result.
        """
        FakeValidator.calls.append(("validate_update", new_params))
        if FakeValidator.error is not None:
            raise FakeValidator.error
        return FakeValidator.result


class FakeCleanup:
    """Stands in for ``CleanupService``, recording every call."""

    def __init__(self, db: Any) -> None:
        """Keep the database session.

        Parameters
        ----------
        db : Any
            Database session.
        """
        self.db = db

    def cleanup_orphaned_resources(
        self,
        session_id: int,
        old_parameters: dict,
        new_parameters: Optional[dict] = None,
    ) -> None:
        """Record an orphan sweep.

        Parameters
        ----------
        session_id : int
            Session id.
        old_parameters : dict
            Parameters before the change.
        new_parameters : Optional[dict]
            Parameters after the change, ``None`` on deletion.
        """
        EVENTS.append(("cleanup", session_id, old_parameters, new_parameters))

    def invalidate_session_artifacts(self, session_id: int, *, commit: bool) -> None:
        """Record an artifact discard.

        Parameters
        ----------
        session_id : int
            Session id.
        commit : bool
            Whether the call commits.
        """
        EVENTS.append(("invalidate", session_id, commit))


EVENTS: List[tuple] = []


def fake_cancel(session: GenerativeSession, job_queue: Any) -> bool:
    """Record an index cancellation.

    Parameters
    ----------
    session : GenerativeSession
        Session whose index is cancelled.
    job_queue : Any
        Job queue.

    Returns
    -------
    bool
        Always ``False``.
    """
    EVENTS.append(("cancel", session.id, job_queue))
    return False


@pytest.fixture(name="db")
def fixture_db():
    """Yield a session on an in memory database with every table.

    Yields
    ------
    Session
        Database session.
    """
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()
    engine.dispose()


@pytest.fixture(name="session")
def fixture_session(db) -> GenerativeSession:
    """Insert one session row.

    Parameters
    ----------
    db : Session
        Database session.

    Returns
    -------
    GenerativeSession
        The committed session.
    """
    session = GenerativeSession(
        name="s",
        task_name="TextToTextGenerationTask",
        model_name="Qwen25_05BInstruct",
        parameters={"documents": []},
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture(autouse=True)
def fake_collaborators(monkeypatch):
    """Replace the RAG collaborators with recording fakes."""
    FakeValidator.calls = []
    FakeValidator.result = {"normalized": True}
    FakeValidator.error = None
    EVENTS.clear()
    monkeypatch.setattr(rag_module, "SessionValidationService", FakeValidator)
    monkeypatch.setattr(rag_module, "CleanupService", FakeCleanup)
    monkeypatch.setattr(rag_module, "cancel_live_index_job", fake_cancel)


def _rag_service(db) -> RAGWorkflowSessionService:
    """Build a RAG service over the given database.

    Parameters
    ----------
    db : Session
        Database session.

    Returns
    -------
    RAGWorkflowSessionService
        The service, with sentinel registry and job queue.
    """
    return RAGWorkflowSessionService(db, "registry", "queue")


def test_inference_workflow_gets_the_default_service(db):
    """Inference sessions use the pass through service."""
    service = session_service_for("InferenceWorkflow", db, "registry", "queue")

    assert type(service) is WorkflowSessionService


def test_unknown_workflow_gets_the_default_service(db):
    """A workflow without its own service, a plugin's say, passes through."""
    service = session_service_for("PluginWorkflow", db, "registry", "queue")

    assert type(service) is WorkflowSessionService


def test_rag_workflow_gets_the_rag_service(db):
    """RAG sessions use the RAG service."""
    service = session_service_for("RAGWorkflow", db, "registry", "queue")

    assert isinstance(service, RAGWorkflowSessionService)


def test_workflow_session_error_is_a_value_error():
    """Callers that already map ValueError to 400 keep working."""
    assert issubclass(WorkflowSessionError, ValueError)


def test_default_service_passes_parameters_through(db, session):
    """Inference creation and update keep the parameters as sent."""
    service = WorkflowSessionService(db, "registry", "queue")
    parameters = {"temperature": 0.5}

    assert service.prepare_parameters(parameters, "en") == parameters
    assert service.validate_update(session, {"temperature": 0.1}) == {
        "temperature": 0.1
    }


def test_default_service_hooks_do_nothing(db, session):
    """Inference sessions need no readiness check, side effect or cleanup."""
    service = WorkflowSessionService(db, "registry", "queue")

    service.apply_update(session, {"a": 1}, {"a": 2})
    service.check_ready(session)
    service.before_delete(session)
    service.after_delete(session.id, {"a": 1})

    assert EVENTS == []
    assert FakeValidator.calls == []


def test_rag_prepare_parameters_returns_the_validated_parameters(db):
    """Creation goes through the RAG validator with the client language."""
    result = _rag_service(db).prepare_parameters({"raw": 1}, "es")

    assert result == {"normalized": True}
    assert FakeValidator.calls == [
        ("init", db, "registry"),
        ("prepare", {"raw": 1}, "es"),
    ]


@pytest.mark.parametrize(
    "error", [ValueError("bad value"), RAGWorkflowError("bad component")]
)
def test_rag_prepare_parameters_reports_validation_errors(db, error):
    """Validation failures surface as WorkflowSessionError with their message."""
    FakeValidator.error = error

    with pytest.raises(WorkflowSessionError, match=str(error)):
        _rag_service(db).prepare_parameters({"raw": 1}, None)


def test_rag_validate_update_has_no_side_effects(db, session):
    """Validating an update never cancels an index or deletes anything."""
    result = _rag_service(db).validate_update(session, {"prompt": {}})

    assert result == {"normalized": True}
    assert FakeValidator.calls[-1] == ("validate_update", {"prompt": {}})
    assert EVENTS == []


@pytest.mark.parametrize(
    "error", [ValueError("bad value"), RAGWorkflowError("bad component")]
)
def test_rag_validate_update_reports_validation_errors(db, session, error):
    """Update validation failures surface as WorkflowSessionError."""
    FakeValidator.error = error

    with pytest.raises(WorkflowSessionError, match=str(error)):
        _rag_service(db).validate_update(session, {"prompt": {}})


def test_rag_apply_update_cancels_the_index_before_cleaning_up(db, session):
    """A running index is stopped before the rows it writes are deleted."""
    old = {"retriever_model": {"component": "A"}}
    new = {"retriever_model": {"component": "B"}}

    _rag_service(db).apply_update(session, old, new)

    assert [
        ("cancel", session.id, "queue"),
        ("cleanup", session.id, old, new),
    ] == EVENTS


@pytest.mark.parametrize("parameters", [{"documents": []}, {}, None])
def test_rag_check_ready_refuses_a_session_without_documents(db, session, parameters):
    """A turn over no documents is refused before any job runs."""
    session.parameters = parameters

    with pytest.raises(WorkflowSessionError, match="Add at least one document"):
        _rag_service(db).check_ready(session)


def test_rag_check_ready_accepts_a_session_with_documents(db, session):
    """A session with documents may answer."""
    session.parameters = {"documents": [3]}

    _rag_service(db).check_ready(session)


def test_rag_before_delete_stops_the_index_and_discards_artifacts(db, session):
    """Deletion stops the index, then discards artifacts inside the caller's
    transaction."""
    _rag_service(db).before_delete(session)

    assert [
        ("cancel", session.id, "queue"),
        ("invalidate", session.id, False),
    ] == EVENTS


def test_rag_after_delete_sweeps_orphaned_resources(db):
    """After deletion the shared rows nobody uses any more are swept."""
    old = {"chunking_model": {"component": "CharacterChunkModel"}}

    _rag_service(db).after_delete(7, old)

    assert [("cleanup", 7, old, None)] == EVENTS
