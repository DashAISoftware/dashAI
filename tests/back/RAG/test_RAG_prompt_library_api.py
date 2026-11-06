"""The prompt-library endpoints and the dependency checks behind deletion."""

import uuid

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGPipeline,
    RAGPrompt,
)
from DashAI.back.services.RAG.prompt_service import PromptService


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
        db.commit()
        return session.id


def test_library_lists_user_prompts_and_built_ins(client):
    template = _unique_template()
    library_id = _create_prompt(client, _unique_name("library"), template)
    with client.app.container["session_factory"]() as db:
        internal = PromptService(
            db, client.app.container["component_registry"]
        ).get_or_create(
            "CustomRAGGenerationPrompt",
            "pipeline_1_CustomRAGGenerationPrompt",
            {"template": _unique_template()},
        )

    response = client.get("/api/v1/prompt/library")

    assert response.status_code == 200, response.text
    payload = response.json()
    ids = [prompt["id"] for prompt in payload]
    assert library_id in ids
    assert internal.id not in ids
    builtin_classes = {
        prompt["class_name"] for prompt in payload if not prompt["is_library"]
    }
    assert {
        "DefaultRAGGenerationPrompt",
        "DefaultQARAGGenerationPrompt",
        "DefaultAugmentationPrompt",
        "DefaultQueryRewritingPrompt",
        "DefaultQueryExpansionPrompt",
        "DefaultQueryDecompositionPrompt",
        "DefaultRetrievalSufficiencyPrompt",
        "DefaultLLMFilterPrompt",
    }.issubset(builtin_classes)
    assert all(
        prompt["is_library"]
        for prompt in payload
        if prompt["class_name"] == "CustomRAGGenerationPrompt"
    )
    assert all(prompt["prompt_type"] for prompt in payload)
    transformation = next(
        prompt
        for prompt in payload
        if prompt["class_name"] == "DefaultQueryRewritingPrompt"
    )
    assert transformation["prompt_type"] == "transformation"
    assert transformation["prompt_subtype"] == "rewriting"


def test_create_promotes_an_internal_row_with_the_same_template(client):
    template = _unique_template()
    with client.app.container["session_factory"]() as db:
        internal = PromptService(
            db, client.app.container["component_registry"]
        ).get_or_create(
            "CustomRAGGenerationPrompt",
            "pipeline_3_CustomRAGGenerationPrompt",
            {"template": template},
        )
        internal_id = internal.id

    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": _unique_name("promoted"),
            "parameters": {"template": template},
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["id"] == internal_id
    with client.app.container["session_factory"]() as db:
        row = db.get(RAGPrompt, internal_id)
        assert row.is_library is True
        assert row.name.startswith("promoted_")
    library_ids = [
        prompt["id"] for prompt in client.get("/api/v1/prompt/library").json()
    ]
    assert internal_id in library_ids


def test_resolve_a_library_prompt_keeps_its_stored_shape(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("resolve"), template)

    with client.app.container["session_factory"]() as db:
        service = PromptService(db, client.app.container["component_registry"])
        resolved = service.resolve_prompt_id_to_component(prompt_id)

    assert resolved == {
        "component": "CustomRAGGenerationPrompt",
        "params": {"template": template},
    }


def test_delete_an_unused_library_prompt(client):
    prompt_id = _create_prompt(client, _unique_name("unused"), _unique_template())

    response = client.delete(f"/api/v1/prompt/{prompt_id}")

    assert response.status_code == 204, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, prompt_id) is None


def test_delete_a_prompt_in_use_without_cascade_is_refused(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("in-use"), template)
    session_id = _create_session_with_prompt(client, prompt_id, template)

    response = client.delete(f"/api/v1/prompt/{prompt_id}")

    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert [session["id"] for session in detail["sessions"]] == [session_id]
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, prompt_id) is not None
        assert db.get(GenerativeSession, session_id) is not None


def test_delete_a_prompt_in_use_cascades_its_sessions(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("cascade"), template)
    session_id = _create_session_with_prompt(client, prompt_id, template)

    response = client.delete(f"/api/v1/prompt/{prompt_id}?cascade_sessions=true")

    assert response.status_code == 204, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, prompt_id) is None
        assert db.get(GenerativeSession, session_id) is None
        assert (
            db.query(RAGPipeline).filter(RAGPipeline.prompt_id == prompt_id).count()
            == 0
        )


def test_delete_a_built_in_prompt_is_refused(client):
    library = client.get("/api/v1/prompt/library").json()
    builtin = next(prompt for prompt in library if not prompt["is_library"])

    response = client.delete(f"/api/v1/prompt/{builtin['id']}")

    assert response.status_code == 409, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, builtin["id"]) is not None


def test_delete_an_internal_prompt_is_refused(client):
    with client.app.container["session_factory"]() as db:
        internal = PromptService(
            db, client.app.container["component_registry"]
        ).get_or_create(
            "CustomRAGGenerationPrompt",
            "pipeline_2_CustomRAGGenerationPrompt",
            {"template": _unique_template()},
        )
        internal_id = internal.id

    response = client.delete(f"/api/v1/prompt/{internal_id}")

    assert response.status_code == 409, response.text
    with client.app.container["session_factory"]() as db:
        assert db.get(RAGPrompt, internal_id) is not None


def test_sessions_using_ignores_language_only_differences(client):
    template = _unique_template()
    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": _unique_name("language"),
            "parameters": {"template": template, "language": "en"},
        },
    )
    assert response.status_code == 201, response.text
    prompt_id = response.json()["id"]
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            name=_unique_name("no-language"),
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
        session_id = session.id

        service = PromptService(db, client.app.container["component_registry"])
        assert [item.id for item in service.sessions_using(prompt_id)] == [session_id]


def test_sessions_using_finds_nested_transformation_prompts(client):
    template = "Rewrite {input} using {history} " + uuid.uuid4().hex
    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomQueryRewritingPrompt",
            "name": _unique_name("transformation"),
            "parameters": {"template": template},
        },
    )
    assert response.status_code == 201, response.text
    prompt_id = response.json()["id"]
    with client.app.container["session_factory"]() as db:
        session = GenerativeSession(
            name=_unique_name("nested"),
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters={
                "documents": [],
                "query_transformation": {
                    "component": "LLMQueryRewriter",
                    "params": {
                        "prompt": {
                            "component": "CustomQueryRewritingPrompt",
                            "params": {"template": template},
                        }
                    },
                },
            },
        )
        db.add(session)
        db.commit()
        session_id = session.id

        service = PromptService(db, client.app.container["component_registry"])
        assert [item.id for item in service.sessions_using(prompt_id)] == [session_id]


def test_sessions_using_matches_the_stored_prompt_parameters(client):
    template = _unique_template()
    prompt_id = _create_prompt(client, _unique_name("match"), template)
    with client.app.container["session_factory"]() as db:
        matching = GenerativeSession(
            name=_unique_name("matching"),
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
        other = GenerativeSession(
            name=_unique_name("other"),
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters={
                "documents": [],
                "prompt": {
                    "component": "CustomRAGGenerationPrompt",
                    "params": {"template": _unique_template()},
                },
            },
        )
        db.add_all([matching, other])
        db.commit()
        matching_id = matching.id

        service = PromptService(db, client.app.container["component_registry"])
        assert [session.id for session in service.sessions_using(prompt_id)] == [
            matching_id
        ]
