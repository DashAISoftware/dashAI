"""Template and ``prompt_id`` type validation across every prompt entry point.

The library CRUD endpoints, the fork endpoint and the session ``prompts`` map
all feed the same validation: a template must be a non-empty string (or a
non-empty language map of them), ``template`` and ``templates`` cannot be
combined, and a ``prompt_id`` must be a plain integer. Before this contract,
``{"template": 123}`` was coerced by the component schema and
``{"prompt_id": true}`` quietly addressed prompt 1.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.back.RAG.conftest import BOW_PARAMS


def _unique_name(prefix: str = "prompt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _template() -> str:
    return f"Context: {{chunks}}\nQuestion: {{input}} {uuid.uuid4().hex}"


#: Payloads that must be rejected everywhere a prompt template is accepted.
INVALID_TEMPLATE_PAYLOADS = {
    "null_template": {"template": None},
    "numeric_template": {"template": 123},
    "list_template": {"template": ["{input} {chunks}"]},
    "string_templates": {"templates": "en"},
    "numeric_templates_value": {"templates": {"en": 5}},
    "empty_templates": {"templates": {}},
    "empty_templates_value": {"templates": {"en": ""}},
    "both_keys": {
        "template": "Context: {chunks}\nQuestion: {input}",
        "templates": {"en": "Context: {chunks}\nQuestion: {input}"},
    },
}


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


def _create_session(client: TestClient) -> int:
    response = client.post("/api/v1/generative-session/", json=_base_session_params())
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_library_prompt(client: TestClient) -> int:
    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": _unique_name("library"),
            "parameters": {"template": _template()},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ===================================================================
# Library POST / PATCH / fork
# ===================================================================


@pytest.mark.parametrize(
    "parameters",
    INVALID_TEMPLATE_PAYLOADS.values(),
    ids=INVALID_TEMPLATE_PAYLOADS.keys(),
)
def test_create_prompt_rejects_malformed_templates(
    client: TestClient, parameters: dict
):
    response = client.post(
        "/api/v1/prompt/",
        json={
            "class_name": "CustomRAGGenerationPrompt",
            "name": _unique_name("invalid"),
            "parameters": parameters,
        },
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "parameters",
    INVALID_TEMPLATE_PAYLOADS.values(),
    ids=INVALID_TEMPLATE_PAYLOADS.keys(),
)
def test_patch_prompt_rejects_malformed_templates(client: TestClient, parameters: dict):
    prompt_id = _create_library_prompt(client)

    response = client.patch(
        f"/api/v1/prompt/{prompt_id}", json={"parameters": parameters}
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "parameters",
    INVALID_TEMPLATE_PAYLOADS.values(),
    ids=INVALID_TEMPLATE_PAYLOADS.keys(),
)
def test_fork_prompt_rejects_malformed_templates(client: TestClient, parameters: dict):
    prompt_id = _create_library_prompt(client)

    response = client.post(
        f"/api/v1/prompt/{prompt_id}/fork",
        json={"name": _unique_name("fork"), "parameters": parameters},
    )

    assert response.status_code == 400, response.text


# ===================================================================
# Session create / update through the ``prompts`` map
# ===================================================================


@pytest.mark.parametrize(
    "parameters",
    INVALID_TEMPLATE_PAYLOADS.values(),
    ids=INVALID_TEMPLATE_PAYLOADS.keys(),
)
def test_create_session_rejects_malformed_prompt_map_templates(
    client: TestClient, parameters: dict
):
    response = client.post(
        "/api/v1/generative-session/",
        json={
            **_base_session_params(),
            "prompts": {
                "generation": {
                    "component": "CustomRAGGenerationPrompt",
                    "params": parameters,
                }
            },
        },
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "parameters",
    INVALID_TEMPLATE_PAYLOADS.values(),
    ids=INVALID_TEMPLATE_PAYLOADS.keys(),
)
def test_update_session_rejects_malformed_prompt_map_templates(
    client: TestClient, parameters: dict
):
    session_id = _create_session(client)

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={
            "prompts": {
                "generation": {
                    "component": "CustomRAGGenerationPrompt",
                    "params": parameters,
                }
            }
        },
    )

    assert response.status_code == 400, response.text


# ===================================================================
# ``prompt_id`` typing
# ===================================================================

INVALID_PROMPT_IDS = {
    "boolean": True,
    "float": 1.0,
    "string": "1",
    "list": [1],
    "object": {"id": 1},
}


@pytest.mark.parametrize(
    "prompt_id", INVALID_PROMPT_IDS.values(), ids=INVALID_PROMPT_IDS.keys()
)
def test_session_prompt_map_rejects_non_integer_prompt_ids(
    client: TestClient, prompt_id
):
    response = client.post(
        "/api/v1/generative-session/",
        json={
            **_base_session_params(),
            "prompts": {"generation": {"prompt_id": prompt_id}},
        },
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "prompt_id", INVALID_PROMPT_IDS.values(), ids=INVALID_PROMPT_IDS.keys()
)
def test_session_update_rejects_non_integer_prompt_ids(client: TestClient, prompt_id):
    session_id = _create_session(client)

    response = client.put(
        f"/api/v1/generative-session/{session_id}/parameters",
        json={"prompts": {"generation": {"prompt_id": prompt_id}}},
    )

    assert response.status_code == 400, response.text


@pytest.mark.parametrize(
    "prompt_id", INVALID_PROMPT_IDS.values(), ids=INVALID_PROMPT_IDS.keys()
)
def test_legacy_parameters_prompt_id_must_be_an_integer(client: TestClient, prompt_id):
    params = _base_session_params()
    params["parameters"]["prompt_id"] = prompt_id

    response = client.post("/api/v1/generative-session/", json=params)

    assert response.status_code == 400, response.text
