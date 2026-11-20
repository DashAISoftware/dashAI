"""A session's history summary is dropped when a turn it covers changes (#977).

The summary stands for every turn up to ``history_summary_until``. Deleting or
retrying one of those turns makes it stale; a later turn does not.

Lives under ``tests/back/api`` to reuse the ``client`` fixture from this
package's ``conftest.py``.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
)


@pytest.mark.parametrize(
    ("action", "which", "cleared"),
    [
        ("delete", "covered", True),
        ("retry", "covered", True),
        ("delete", "later", False),
        ("retry", "later", False),
    ],
)
def test_summary_is_cleared_only_when_a_covered_turn_changes(
    client: TestClient, action: str, which: str, cleared: bool
):
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            task_name="TextToTextGenerationTask",
            model_name="SomeModel",
            parameters={},
            name=f"summary_{uuid.uuid4().hex[:8]}",
            description=None,
        )
        db.add(session)
        db.commit()
        session_id = session.id
        turns = []
        for status in (RunStatus.FINISHED, RunStatus.ERROR, RunStatus.ERROR):
            turn = GenerativeProcess(session_id=session_id, status=status)
            db.add(turn)
            db.commit()
            turns.append(turn.id)
        _, covered, later = turns
        session.history_summary = "old"
        session.history_summary_until = covered
        db.commit()

    target = covered if which == "covered" else later
    url = f"/api/v1/generative-process/{target}"
    response = client.delete(url) if action == "delete" else client.post(url + "/retry")
    assert response.status_code in (200, 204), response.text

    with client.app.container["session_factory"]() as db:
        session = db.get(GenerativeSession, session_id)
        assert (session.history_summary is None) == cleared
        assert (session.history_summary_until is None) == cleared


def test_summary_is_cleared_when_the_parameters_change(client: TestClient):
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            task_name="TextToTextGenerationTask",
            model_name="SomeModel",
            parameters={"context_window": 4096},
            name=f"summary_{uuid.uuid4().hex[:8]}",
            description=None,
            history_summary="old",
            history_summary_until=1,
        )
        db.add(session)
        db.commit()
        session_id = session.id

    url = f"/api/v1/generative-session/{session_id}/parameters"
    unchanged = client.put(url, json={"context_window": 4096})
    assert unchanged.status_code == 200, unchanged.text
    with client.app.container["session_factory"]() as db:
        session = db.get(GenerativeSession, session_id)
        assert (session.history_summary, session.history_summary_until) == ("old", 1)

    response = client.put(url, json={"context_window": 1024})
    assert response.status_code == 200, response.text

    with client.app.container["session_factory"]() as db:
        session = db.get(GenerativeSession, session_id)
        assert session.history_summary is None
        assert session.history_summary_until is None
