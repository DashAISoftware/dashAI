from datetime import datetime

import pytest

from DashAI.back.dependencies.database.models import GenerativeSession, RAGPrompt


def _get_prompt_list(client):
    response = client.get("/api/v1/prompt/")
    assert response.status_code == 200
    return response.json()


def _create_rag_session(session_factory, prompt_id: int, name: str):
    params = {
        "documents": [1],
        "chunking_model": {
            "component": "CharacterChunkModel",
            "params": {
                "chunk_size": 8,
                "chunk_overlap": 2,
            },
        },
        "retriever_model": {
            "component": "TFIDFRetriever",
            "params": {
                "TFIDFVectorizer": {
                    "component": "TFIDFVectorizerModel",
                    "params": {},
                },
                "similarity_function": "cosine",
                "top_k": 1,
                "similarity_threshold": None,
            },
        },
        "generation_model": {
            "component": "QwenModel",
            "params": {
                "model_name": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                "max_tokens": 32,
                "temperature": 0.2,
                "frequency_penalty": 0.0,
                "context_window": 128,
                "device": "CPU",
            },
        },
        "prompt_id": prompt_id,
    }

    with session_factory() as db:
        session = GenerativeSession(
            model_name="RAGPipeline",
            task_name="RAGTask",
            parameters=params,
            name=name,
            description=None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id


def test_update_prompt_in_place(client):
    prompts = _get_prompt_list(client)
    prompt = prompts[0]

    response = client.patch(
        f"/api/v1/prompt/{prompt['id']}",
        json={"name": f"{prompt['name']} (updated)"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == prompt["id"]
    assert data["name"] == f"{prompt['name']} (updated)"


def test_clone_prompt_for_session(client):
    prompts = _get_prompt_list(client)
    prompt = prompts[1]
    session_factory = client.app.container["session_factory"]
    session_id = _create_rag_session(session_factory, prompt["id"], "rag-session-clone")

    response = client.post(f"/api/v1/prompt/{prompt['id']}/sessions/{session_id}", json={})

    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == session_id
    assert data["parameters"]["prompt_id"] == data["prompt"]["id"]
    assert data["prompt"]["name"].endswith(f"session {session_id}")


def test_session_parameter_update_cleans_orphan_prompt(client):
    prompts = _get_prompt_list(client)
    base_prompt = prompts[1]
    session_factory = client.app.container["session_factory"]
    session_id = _create_rag_session(session_factory, base_prompt["id"], "rag-session-cleanup")

    clone_response = client.post(
        f"/api/v1/prompt/{base_prompt['id']}/sessions/{session_id}",
        json={},
    )
    assert clone_response.status_code == 201
    cloned_prompt_id = clone_response.json()["prompt"]["id"]

    update_response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"prompt_id": base_prompt["id"]},
    )

    assert update_response.status_code == 200
    assert update_response.json()["parameters"]["prompt_id"] == base_prompt["id"]

    with session_factory() as db:
        assert db.get(RAGPrompt, cloned_prompt_id) is None
