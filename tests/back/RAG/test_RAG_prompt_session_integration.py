"""Prompt bindings across the session API and the RAG runtime.

Covers Phase 2B1 of the prompt redesign: sessions persist prompt-free
parameters, prompt references embedded in the request are split into
``rag_session_prompt`` bindings, reads inject the prompts back for the current
frontend, and library/default edits keep their expected sharing semantics.
"""

import uuid

from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGPrompt,
    RAGSessionPrompt,
)
from DashAI.back.services.RAG.prompt_service import PromptService
from DashAI.back.services.RAG.utils import build_prompt_hash
from tests.back.RAG.conftest import BOW_PARAMS, _create_data_document


def _base_session_params() -> dict:
    """Return the minimal valid RAG session payload."""
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "parameters": {
            "chunking_model": {
                "component": "CharacterChunkModel",
                "params": {"chunk_size": 400, "chunk_overlap": 40},
            },
            "retriever_model": {
                "component": "BM25Retriever",
                "params": {
                    "vectorizer": {
                        "component": "BagOfWordsConverter",
                        "params": dict(BOW_PARAMS),
                    },
                    "k1": 1.5,
                    "b": 0.75,
                    "delta": 0.0,
                    "similarity_function": "cosine",
                    "top_k": 5,
                },
            },
            "generation_model": {
                "component": "Llama32_1BInstruct",
                "params": {
                    "max_tokens": 100,
                    "temperature": 0.7,
                    "frequency_penalty": 0.1,
                    "context_window": 512,
                    "device": "CPU",
                },
            },
            "prompt": {
                "component": "DefaultRAGGenerationPrompt",
                "params": {"language": "en"},
            },
        },
        "name": f"prompt_integration_{uuid.uuid4().hex[:8]}",
        "description": None,
    }


def _create_prompt(client: TestClient, template: str, name: str) -> int:
    """Create a CustomRAGGenerationPrompt through the prompt API."""
    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": name,
            "parameters": {"template": template},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_session(client: TestClient, *, prompt_id: int | None = None) -> int:
    """Create a RAG session, optionally bound to a library prompt id."""
    params = _base_session_params()
    if prompt_id is not None:
        # ``prompt_id`` is resolved to its component reference during create.
        params["parameters"]["prompt_id"] = prompt_id
    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _service(client: TestClient, db) -> PromptService:
    return PromptService(db, client.app.container["component_registry"])


def _template(prefix: str) -> str:
    return f"Context: {{chunks}}\nUser: {{input}}\n{prefix}_{uuid.uuid4().hex}"


def test_create_with_default_prompt_stores_prompt_free_parameters(client):
    """A created session stores no prompt and binds the default generation slot."""
    session_id = _create_session(client)

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = db.get(GenerativeSession, session_id)
        assert "prompt" not in session.parameters
        assert "prompt_id" not in session.parameters

        binding = db.get(RAGSessionPrompt, (session_id, "generation"))
        assert binding is not None
        prompt = db.get(RAGPrompt, binding.prompt_id)
        assert prompt.is_default is True
        binding_id = binding.prompt_id

    response = client.get(f"/api/v1/generative-session/{session_id}")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["parameters"]["prompt"]["component"] == "DefaultRAGGenerationPrompt"
    assert payload["parameters"]["prompt"]["params"]["language"] == "en"
    assert payload["prompts"]["generation"]["prompt_id"] == binding_id
    assert payload["prompts"]["generation"]["is_default"] is True


def test_update_prompt_embedded_in_parameters_stays_prompt_free(client):
    """A prompt sent inside parameters updates the binding, not the stored blob."""
    first_id = _create_session(client)
    second_id = _create_session(client)

    template = _template("updated")
    prompt_id = _create_prompt(client, template, f"embedded_{uuid.uuid4().hex[:8]}")

    response = client.put(
        f"/api/v1/generative-session/{first_id}/parameters",
        json={
            "prompt": {
                "component": "CustomRAGGenerationPrompt",
                "params": {"template": template},
            }
        },
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["parameters"]["prompt"]["params"]["template"] == template
    assert updated["prompts"]["generation"]["prompt_id"] == prompt_id

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        stored = db.get(GenerativeSession, first_id)
        assert "prompt" not in stored.parameters
        binding = db.get(RAGSessionPrompt, (first_id, "generation"))
        assert binding.prompt_id == prompt_id

        other_binding = db.get(RAGSessionPrompt, (second_id, "generation"))
        other_prompt = db.get(RAGPrompt, other_binding.prompt_id)
        assert other_prompt.is_default is True

    other = client.get(f"/api/v1/generative-session/{second_id}")
    assert other.status_code == 200, other.text
    assert other.json()["parameters"]["prompt"]["component"] == (
        "DefaultRAGGenerationPrompt"
    )


def test_editing_a_library_prompt_is_visible_to_every_bound_session(client):
    """Both sessions bound to one library prompt see an in-place edit."""
    original = _template("original")
    edited = _template("edited")
    prompt_id = _create_prompt(client, original, f"shared_{uuid.uuid4().hex[:8]}")

    first_id = _create_session(client, prompt_id=prompt_id)
    second_id = _create_session(client, prompt_id=prompt_id)

    before = client.get(f"/api/v1/generative-session/{first_id}").json()
    assert before["parameters"]["prompt"]["params"]["template"] == original

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        _service(client, db).update_library_prompt(
            prompt_id, parameters={"template": edited}
        )

    for session_id in (first_id, second_id):
        response = client.get(f"/api/v1/generative-session/{session_id}")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["parameters"]["prompt"]["params"]["template"] == edited
        assert payload["prompts"]["generation"]["prompt_id"] == prompt_id


def test_editing_a_default_inside_a_session_creates_a_custom_draft(client):
    """A session-local default edit forks the default without changing it."""
    session_id = _create_session(client)

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        default = (
            db.query(RAGPrompt)
            .filter(
                RAGPrompt.class_name == "DefaultRAGGenerationPrompt",
                RAGPrompt.is_default.is_(True),
            )
            .one()
        )
        default_id = default.id
        original_parameters = dict(default.parameters)

    template = _template("session_edit")
    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={
            "prompt": {
                "component": "DefaultRAGGenerationPrompt",
                "params": {"language": "en", "template": template},
            }
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["parameters"]["prompt"]["component"] == (
        "CustomRAGGenerationPrompt"
    )
    assert response.json()["parameters"]["prompt"]["params"]["template"] == template

    with session_factory() as db:
        binding = db.get(RAGSessionPrompt, (session_id, "generation"))
        draft = db.get(RAGPrompt, binding.prompt_id)
        db.expire_all()
        stored_default = db.get(RAGPrompt, default_id)

        assert draft.class_name == "CustomRAGGenerationPrompt"
        assert draft.is_library is False
        assert draft.is_default is False
        assert draft.based_on_id == default_id
        assert draft.parameters == {"template": template}
        assert stored_default.parameters == original_parameters


def test_legacy_session_with_prompt_in_parameters_round_trips(client):
    """A session that still stores its prompt in parameters reads unchanged."""
    legacy_parameters = {
        "documents": [],
        "prompt": {
            "component": "CustomRAGGenerationPrompt",
            "params": {"template": _template("legacy")},
        },
    }
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = GenerativeSession(
            name=f"legacy_{uuid.uuid4().hex[:8]}",
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters=legacy_parameters,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
        service = _service(client, db)
        materialized = service.materialize_session_parameters(
            session_id, dict(session.parameters)
        )

        assert materialized == legacy_parameters
        assert (
            db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.session_id == session_id)
            .count()
            == 0
        )

    response = client.get(f"/api/v1/generative-session/{session_id}")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert (
        payload["parameters"]["prompt"]["params"]["template"]
        == (legacy_parameters["prompt"]["params"]["template"])
    )


def _create_draft_prompt(client) -> int:
    """Insert an internal draft prompt that belongs to no session yet."""
    parameters = {"template": _template("foreign_draft")}
    with client.app.container["session_factory"]() as db:
        prompt = RAGPrompt(
            class_name="CustomRAGGenerationPrompt",
            name=None,
            parameters=parameters,
            parameters_hash=build_prompt_hash("CustomRAGGenerationPrompt", parameters),
            is_library=False,
            is_default=False,
        )
        db.add(prompt)
        db.commit()
        return prompt.id


def test_create_with_a_foreign_draft_prompt_returns_400_and_commits_nothing(client):
    """A rejected prompt must not leave a session committed without bindings."""
    draft_id = _create_draft_prompt(client)
    params = _base_session_params()
    name = params["name"]

    response = client.post(
        "/api/v1/generative-session/",
        json={**params, "prompts": {"generation": {"prompt_id": draft_id}}},
    )

    assert response.status_code == 400, response.text
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        assert (
            db.query(GenerativeSession).filter(GenerativeSession.name == name).count()
            == 0
        )


def test_update_with_a_foreign_draft_prompt_returns_400_and_keeps_bindings(client):
    """A failed prompt edit rolls back the whole PUT transaction."""
    session_id = _create_session(client)
    draft_id = _create_draft_prompt(client)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        before = db.get(RAGSessionPrompt, (session_id, "generation")).prompt_id

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"prompts": {"generation": {"prompt_id": draft_id}}},
    )

    assert response.status_code == 400, response.text
    with session_factory() as db:
        after = db.get(RAGSessionPrompt, (session_id, "generation")).prompt_id
    assert after == before

    fetched = client.get(f"/api/v1/generative-session/{session_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["parameters"]["prompt"]["component"] == (
        "DefaultRAGGenerationPrompt"
    )


def test_create_with_an_embedded_foreign_draft_prompt_returns_400(client):
    """``parameters.prompt_id`` is resolved but still guarded against drafts."""
    draft_id = _create_draft_prompt(client)
    params = _base_session_params()
    name = params["name"]
    params["parameters"]["prompt_id"] = draft_id

    response = client.post("/api/v1/generative-session/", json=params)

    assert 400 <= response.status_code < 500, response.text

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        assert (
            db.query(GenerativeSession).filter(GenerativeSession.name == name).count()
            == 0
        )
        assert (
            db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.prompt_id == draft_id)
            .count()
            == 0
        )


def test_update_with_an_embedded_foreign_draft_prompt_returns_400(client):
    """The same guard applies when ``prompt_id`` arrives through a PUT body."""
    session_id = _create_session(client)
    draft_id = _create_draft_prompt(client)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        before = db.get(RAGSessionPrompt, (session_id, "generation")).prompt_id

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"prompt_id": draft_id},
    )

    assert 400 <= response.status_code < 500, response.text

    with session_factory() as db:
        after = db.get(RAGSessionPrompt, (session_id, "generation")).prompt_id
        assert after == before
        assert after != draft_id


def test_document_history_keeps_the_prompt_snapshot_between_two_edits(client):
    """A document entry must not hide a later prompt edit from the diff."""
    session_id = _create_session(client)
    first_template = _template("first_edit")
    second_template = _template("second_edit")

    first = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={
            "prompt": {
                "component": "CustomRAGGenerationPrompt",
                "params": {"template": first_template},
            }
        },
    )
    assert first.status_code == 200, first.text

    document_id = _create_data_document(client, text="history document")
    attached = client.post(
        f"/api/v1/rag/sessions/{session_id}/documents",
        json={"document_ids": [document_id]},
    )
    assert attached.status_code == 200, attached.text

    second = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={
            "prompt": {
                "component": "CustomRAGGenerationPrompt",
                "params": {"template": second_template},
            }
        },
    )
    assert second.status_code == 200, second.text

    events = client.get(
        f"/api/v1/generative-session/parameters-history/{session_id}"
    ).json()
    assert events, "Expected at least one history event"
    last_changes = events[-1]["changes"]
    prompt_changes = [
        change for change in last_changes if change["parameter"] == "prompt"
    ]
    assert prompt_changes, last_changes
    assert prompt_changes[0]["newValue"]["params"]["template"] == second_template


def test_editing_only_the_generation_prompt_does_not_invalidate_the_index(
    client, monkeypatch
):
    """Prompt-only updates leave retriever artifacts and reindex state alone."""
    session_id = _create_session(client)
    captured: dict = {}

    def _capture(self, session, old_parameters, new_parameters=None, **kwargs):
        captured["old"] = dict(old_parameters)
        captured["new"] = dict(new_parameters or {})

    monkeypatch.setattr(
        "DashAI.back.api.api_v1.endpoints.generative_session."
        "CleanupService.cleanup_orphaned_resources",
        _capture,
    )

    template = _template("prompt_only")
    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={
            "prompt": {
                "component": "CustomRAGGenerationPrompt",
                "params": {"template": template},
            }
        },
    )
    assert response.status_code == 200, response.text

    assert "prompt" not in captured["old"]
    assert "prompt" not in captured["new"]
    assert captured["old"]["retriever_model"] == captured["new"]["retriever_model"]
    assert captured["old"]["chunking_model"] == captured["new"]["chunking_model"]

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = db.get(GenerativeSession, session_id)
        assert session.needs_reindex is False
