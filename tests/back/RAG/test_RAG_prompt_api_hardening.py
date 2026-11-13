"""Regressions for the session/prompt API review of the prompt redesign.

Each test pins one defect found in the API QA:

* a failed prompt materialisation must not leave a committed session or a
  half-applied update behind;
* a prompt referenced only by a legacy ``parameters.prompt_id`` still counts as
  a dependency, and reading that session reports a 409 instead of a 500;
* internal drafts are never published by forking them or by promoting them
  through a library create;
* a ``prompts`` map either names a real slot or is rejected, and it can supply
  a required nested slot;
* the session collection survives one unreadable session;
* a no-op save writes no history row.
"""

import uuid

from fastapi.testclient import TestClient

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    GenerativeSessionParameterHistory,
    RAGPrompt,
    RAGSessionPrompt,
)
from DashAI.back.services.RAG.prompt_service import PromptService
from DashAI.back.services.RAG.utils import build_prompt_hash
from tests.back.RAG.conftest import BOW_PARAMS


def _unique_name(prefix: str = "prompt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _generation_template(prefix: str = "hardening") -> str:
    return f"Context: {{chunks}}\nQuestion: {{input}}\n{prefix}_{uuid.uuid4().hex}"


def _base_session_params(name: str | None = None) -> dict:
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
        "name": name or _unique_name("session"),
        "description": None,
    }


def _create_session(client: TestClient, *, name: str | None = None) -> int:
    response = client.post(
        "/api/v1/generative-session/", json=_base_session_params(name)
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_library_prompt(client: TestClient, template: str | None = None) -> int:
    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": _unique_name("library"),
            "parameters": {"template": template or _generation_template()},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _insert_unreadable_prompt(client: TestClient) -> int:
    """Insert a library prompt whose stored body has no template at all."""
    # A unique extra key keeps every inserted row's content hash distinct while
    # leaving no ``template``/``templates`` for the reader to resolve.
    parameters: dict = {"language": "en", "note": uuid.uuid4().hex}
    with client.app.container["session_factory"]() as db:
        prompt = RAGPrompt(
            class_name="CustomRAGGenerationPrompt",
            name=_unique_name("broken"),
            parameters=parameters,
            parameters_hash=build_prompt_hash("CustomRAGGenerationPrompt", parameters),
            is_library=True,
            is_default=False,
        )
        db.add(prompt)
        db.commit()
        return prompt.id


# ===================================================================
# C1 — a prompt failure must not commit a session or an update
# ===================================================================


def test_create_with_an_unreadable_prompt_leaves_no_session_and_can_be_retried(
    client: TestClient,
):
    """A rejected create commits nothing, so the name stays reusable."""
    broken_id = _insert_unreadable_prompt(client)
    params = _base_session_params()

    response = client.post(
        "/api/v1/generative-session/",
        json={**params, "prompts": {"generation": {"prompt_id": broken_id}}},
    )

    assert response.status_code == 400, response.text

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        assert (
            db.query(GenerativeSession)
            .filter(GenerativeSession.name == params["name"])
            .count()
            == 0
        )
        assert (
            db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.prompt_id == broken_id)
            .count()
            == 0
        )

    # The phantom session used to make this retry fail with 409.
    retry = client.post("/api/v1/generative-session/", json=params)
    assert retry.status_code == 201, retry.text


def test_update_with_an_unreadable_bound_prompt_rolls_back_the_update(
    client: TestClient,
):
    """An update that cannot materialise its prompts changes nothing."""
    session_id = _create_session(client)
    broken_id = _insert_unreadable_prompt(client)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        # Bind the broken row behind the API's back, as a legacy database state
        # would: the binding itself is valid, its content is not.
        binding = db.get(RAGSessionPrompt, (session_id, "generation"))
        binding.prompt_id = broken_id
        db.commit()
        before_parameters = dict(db.get(GenerativeSession, session_id).parameters)
        before_history = (
            db.query(GenerativeSessionParameterHistory)
            .filter(GenerativeSessionParameterHistory.session_id == session_id)
            .count()
        )

    new_chunking = {
        "component": "CharacterChunkModel",
        "params": {"chunk_size": 200, "chunk_overlap": 20},
    }
    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"chunking_model": new_chunking},
    )

    assert response.status_code == 400, response.text

    with session_factory() as db:
        session = db.get(GenerativeSession, session_id)
        assert session.parameters == before_parameters
        assert (
            db.query(GenerativeSessionParameterHistory)
            .filter(GenerativeSessionParameterHistory.session_id == session_id)
            .count()
            == before_history
        )


# ===================================================================
# C2 — legacy ``parameters.prompt_id`` references
# ===================================================================


def _create_legacy_session(client: TestClient, prompt_id: int | None) -> int:
    """Insert a pre-redesign session that keeps its prompt id in parameters."""
    parameters = {"documents": []}
    if prompt_id is not None:
        parameters["prompt_id"] = prompt_id
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = GenerativeSession(
            name=_unique_name("legacy"),
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters=parameters,
        )
        db.add(session)
        db.commit()
        return session.id


def test_delete_refuses_a_prompt_referenced_only_by_a_legacy_session(
    client: TestClient,
):
    """The legacy ``prompt_id`` counts as a dependency even without a binding."""
    prompt_id = _create_library_prompt(client)
    session_id = _create_legacy_session(client, prompt_id)

    response = client.delete(f"/api/v1/prompt/{prompt_id}")

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert [session["id"] for session in detail["sessions"]] == [session_id]
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        assert db.get(RAGPrompt, prompt_id) is not None


def test_getting_a_session_whose_legacy_prompt_was_deleted_returns_409(
    client: TestClient,
):
    """A missing prompt is a state conflict with a JSON body, not a 500."""
    prompt_id = _create_library_prompt(client)
    session_id = _create_legacy_session(client, prompt_id)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        # Delete straight from the table: the API now refuses this delete.
        db.delete(db.get(RAGPrompt, prompt_id))
        db.commit()

    response = client.get(f"/api/v1/generative-session/{session_id}")

    assert response.status_code == 409, response.text
    assert "detail" in response.json()


# ===================================================================
# C3 — internal drafts are never published
# ===================================================================


def test_forking_an_internal_draft_is_rejected(client: TestClient):
    """An unbound internal draft cannot be turned into a library prompt."""
    with client.app.container["session_factory"]() as db:
        draft = PromptService(
            db, client.app.container["component_registry"]
        ).get_or_create(
            "CustomRAGGenerationPrompt",
            "pipeline_draft_CustomRAGGenerationPrompt",
            {"template": _generation_template("draft")},
        )
        draft_id = draft.id

    response = client.post(
        f"/api/v1/prompt/{draft_id}/fork",
        json={"name": _unique_name("forked_draft")},
    )

    assert 400 <= response.status_code < 500, response.text
    with client.app.container["session_factory"]() as db:
        row = db.get(RAGPrompt, draft_id)
        assert row.is_library is False
        assert row.is_default is False
        assert row.name == "pipeline_draft_CustomRAGGenerationPrompt"


def test_create_matching_a_bound_draft_is_refused_and_keeps_the_session_draft(
    client: TestClient,
):
    """Promoting a bound draft would silently change the owning session."""
    session_id = _create_session(client)
    template = _generation_template("bound_draft")
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

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        draft_id = db.get(RAGSessionPrompt, (session_id, "generation")).prompt_id
        assert db.get(RAGPrompt, draft_id).is_library is False

    created = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": _unique_name("promote_bound"),
            "parameters": {"template": template},
        },
    )

    assert created.status_code == 409, created.text
    with session_factory() as db:
        binding = db.get(RAGSessionPrompt, (session_id, "generation"))
        assert binding.prompt_id == draft_id
        assert db.get(RAGPrompt, draft_id).is_library is False


# ===================================================================
# M1 / M2 — the ``prompts`` map
# ===================================================================


def test_unknown_prompt_slot_paths_are_rejected(client: TestClient):
    """A map entry that names no slot must not be dropped silently."""
    response = client.post(
        "/api/v1/generative-session/",
        json={
            **_base_session_params(),
            "prompts": {
                "not_a_slot": {
                    "component": "CustomRAGGenerationPrompt",
                    "params": {"template": _generation_template()},
                }
            },
        },
    )

    assert response.status_code == 400, response.text
    assert "not_a_slot" in response.json()["detail"]


def test_prompt_map_can_configure_a_required_nested_slot(client: TestClient):
    """The transformation prompt may arrive only through the map."""
    template = f"Rewrite {{input}} with {{history}} {uuid.uuid4().hex}"
    params = _base_session_params()
    params["parameters"]["query_transformation"] = {
        "component": "LLMQueryRewriter",
        "params": {"llm_model": {"component": "Llama32_1BInstruct", "params": {}}},
    }

    response = client.post(
        "/api/v1/generative-session/",
        json={
            **params,
            "prompts": {
                "query_transformation.prompt": {
                    "component": "CustomQueryRewritingPrompt",
                    "params": {"template": template},
                }
            },
        },
    )

    assert response.status_code == 201, response.text
    session_id = response.json()["id"]

    with client.app.container["session_factory"]() as db:
        binding = db.get(RAGSessionPrompt, (session_id, "query_transformation.prompt"))
        assert binding is not None
        prompt = db.get(RAGPrompt, binding.prompt_id)
        assert prompt.parameters["template"] == template


# ===================================================================
# M3 — malformed wrappers and unknown keys
# ===================================================================


def test_update_rejects_a_non_dict_parameters_wrapper(client: TestClient):
    session_id = _create_session(client)

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"parameters": "not-an-object"},
    )

    assert response.status_code == 400, response.text


def test_update_rejects_unknown_top_level_keys(client: TestClient):
    session_id = _create_session(client)

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"retreiver_model": {"component": "BM25Retriever", "params": {}}},
    )

    assert response.status_code == 400, response.text
    assert "retreiver_model" in response.json()["detail"]


def test_create_rejects_unknown_top_level_keys(client: TestClient):
    params = _base_session_params()
    params["parameters"]["unknown_key"] = 1

    response = client.post("/api/v1/generative-session/", json=params)

    assert response.status_code == 400, response.text
    assert "unknown_key" in response.json()["detail"]


# ===================================================================
# M5 — prompt responses report their sessions
# ===================================================================


def test_prompt_reads_report_the_using_sessions(client: TestClient):
    """Single-read and list payloads agree with the library listing."""
    prompt_id = _create_library_prompt(client)
    session_id = _create_session(client)
    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"prompts": {"generation": {"prompt_id": prompt_id}}},
    )
    assert response.status_code == 200, response.text

    single = client.get(f"/api/v1/prompt/{prompt_id}")
    assert single.status_code == 200, single.text
    assert [item["id"] for item in single.json()["sessions"]] == [session_id]

    listing = client.get("/api/v1/prompt/")
    assert listing.status_code == 200, listing.text
    entry = next(prompt for prompt in listing.json() if prompt["id"] == prompt_id)
    assert [item["id"] for item in entry["sessions"]] == [session_id]

    library = client.get("/api/v1/prompt/library")
    library_entry = next(
        prompt for prompt in library.json() if prompt["id"] == prompt_id
    )
    assert library_entry["sessions"] == entry["sessions"]


# ===================================================================
# M6 — the collection survives one unreadable session
# ===================================================================


def test_session_list_keeps_returning_healthy_sessions(client: TestClient):
    """One broken session is reported, not raised, by the list endpoint."""
    healthy_id = _create_session(client)
    broken_id = _create_session(client)
    unreadable_id = _insert_unreadable_prompt(client)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        binding = db.get(RAGSessionPrompt, (broken_id, "generation"))
        binding.prompt_id = unreadable_id
        db.commit()

    response = client.get("/api/v1/generative-session/")

    assert response.status_code == 200, response.text
    by_id = {payload["id"]: payload for payload in response.json()}
    assert healthy_id in by_id
    assert "prompt_error" not in by_id[healthy_id]
    assert by_id[broken_id]["prompt_error"]
    assert "prompt" not in by_id[broken_id]["parameters"]


# ===================================================================
# M7 — a no-op save writes nothing
# ===================================================================


def test_identical_update_writes_no_history_row(client: TestClient):
    """Saving the configuration unchanged must not bump the history."""
    session_id = _create_session(client)
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        stored = dict(db.get(GenerativeSession, session_id).parameters)
        # ``documents`` belongs to the document endpoints and is rejected in a
        # parameter payload, so a faithful no-op save excludes it.
        stored.pop("documents", None)
        binding_id = db.get(RAGSessionPrompt, (session_id, "generation")).prompt_id
        before_history = (
            db.query(GenerativeSessionParameterHistory)
            .filter(GenerativeSessionParameterHistory.session_id == session_id)
            .count()
        )

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={
            "parameters": stored,
            "prompts": {"generation": {"prompt_id": binding_id}},
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["prompts"]["generation"]["prompt_id"] == binding_id

    with session_factory() as db:
        assert (
            db.query(GenerativeSessionParameterHistory)
            .filter(GenerativeSessionParameterHistory.session_id == session_id)
            .count()
            == before_history
        )
