"""Prompt CRUD endpoints: read, edit, fork and the delete policies."""

import uuid

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGPipeline,
    RAGPrompt,
    RAGSessionPrompt,
)


def _unique_name(prefix: str = "prompt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _unique_template() -> str:
    return f"Use {{chunks}} to answer {{input}} {uuid.uuid4().hex}"


def _create_prompt(client, name: str, template: str) -> int:
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


def _default_prompt(client) -> dict:
    library = client.get("/api/v1/prompt/library").json()
    return next(prompt for prompt in library if prompt["is_default"])


def _create_session_with_prompt(client, prompt_id: int, template: str) -> int:
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            name=_unique_name("session"),
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters={
                "documents": [],
                "prompt": {
                    "component": "CustomRAGGenerationPrompt",
                    "params": {"template": template},
                },
            },
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        db.add(
            RAGPipeline(
                session_id=session.id,
                name="",
                description=None,
                parameters=None,
                prompt_id=prompt_id,
            )
        )
        db.add(
            RAGSessionPrompt(
                session_id=session.id,
                slot_path="generation",
                prompt_id=prompt_id,
            )
        )
        db.commit()
        return session.id


def test_get_prompt_by_id(client):
    prompt_id = _create_prompt(client, _unique_name("read"), _unique_template())

    response = client.get(f"/api/v1/prompt/{prompt_id}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == prompt_id
    assert payload["class_name"] == "CustomRAGGenerationPrompt"
    assert payload["is_library"] is True
    assert payload["origin"] == "library"


def test_get_unknown_prompt_returns_404(client):
    response = client.get("/api/v1/prompt/999999")

    assert response.status_code == 404, response.text


def test_patch_library_prompt_updates_in_place(client):
    prompt_id = _create_prompt(client, _unique_name("edit"), _unique_template())
    new_template = _unique_template()

    response = client.patch(
        f"/api/v1/prompt/{prompt_id}",
        json={
            "name": _unique_name("renamed"),
            "parameters": {"template": new_template},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == prompt_id
    assert payload["name"].startswith("renamed_")
    assert payload["parameters"]["template"] == new_template

    stored = client.get(f"/api/v1/prompt/{prompt_id}").json()
    assert stored["parameters"]["template"] == new_template


def test_patch_default_prompt_is_refused(client):
    default = _default_prompt(client)

    response = client.patch(
        f"/api/v1/prompt/{default['id']}",
        json={"name": _unique_name("default_edit")},
    )

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert "fork" in detail.lower()
    with client.app.container["session_factory"]() as db:
        stored = db.get(RAGPrompt, default["id"])
        assert stored.name == default["name"]


def test_patch_duplicate_content_is_refused(client):
    first_template = _unique_template()
    _create_prompt(client, _unique_name("first"), first_template)
    second_id = _create_prompt(client, _unique_name("second"), _unique_template())

    response = client.patch(
        f"/api/v1/prompt/{second_id}",
        json={"parameters": {"template": first_template}},
    )

    assert response.status_code == 409, response.text

    with client.app.container["session_factory"]() as db:
        second = db.get(RAGPrompt, second_id)
        assert second.parameters["template"] != first_template


def test_fork_default_creates_a_custom_library_prompt(client):
    default = _default_prompt(client)
    fork_name = _unique_name("fork")

    response = client.post(
        f"/api/v1/prompt/{default['id']}/fork",
        json={"name": fork_name},
    )

    assert response.status_code == 201, response.text
    fork = response.json()
    assert fork["id"] != default["id"]
    assert fork["class_name"] == "CustomRAGGenerationPrompt"
    assert fork["based_on_id"] == default["id"]
    assert fork["is_library"] is True
    assert fork["is_default"] is False
    assert fork["name"] == fork_name

    stored_default = client.get(f"/api/v1/prompt/{default['id']}").json()
    assert stored_default["parameters"] == default["parameters"]
    assert stored_default["name"] == default["name"]


def test_delete_with_detach_keeps_the_session_and_repoints_its_binding(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("detach"), template)
    session_id = _create_session_with_prompt(client, prompt_id, template)

    response = client.delete(f"/api/v1/prompt/{prompt_id}?detach=true")

    assert response.status_code == 204, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, prompt_id) is None
        assert db.get(GenerativeSession, session_id) is not None
        binding = db.get(RAGSessionPrompt, (session_id, "generation"))
        assert binding is not None
        assert binding.prompt_id != prompt_id
        draft = db.get(RAGPrompt, binding.prompt_id)
        assert draft.is_library is False
        assert draft.is_default is False
        assert draft.parameters["template"] == template


def test_delete_with_cascade_removes_the_session(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("cascade"), template)
    session_id = _create_session_with_prompt(client, prompt_id, template)

    response = client.delete(f"/api/v1/prompt/{prompt_id}?cascade_sessions=true")

    assert response.status_code == 204, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, prompt_id) is None
        assert db.get(GenerativeSession, session_id) is None
        assert (
            db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.session_id == session_id)
            .count()
            == 0
        )


def test_delete_with_both_options_is_rejected(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("both"), template)

    response = client.delete(
        f"/api/v1/prompt/{prompt_id}?detach=true&cascade_sessions=true"
    )

    assert response.status_code == 400, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, prompt_id) is not None
