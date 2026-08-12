"""Integration tests for the strict recursive RAG session validation contract.

``SessionValidationService`` (used by ``POST /api/v1/generative-session/`` and
``PUT /api/v1/generative-session/{id}/parameters``) recursively validates every
``{component, params}`` reference — including nested sub-components such as
the ``BM25VectorizerModel`` inside a ``BM25Retriever`` — against the
component's own schema (``SCHEMA.model_validate(params)``).  A failing
sub-component rejects the whole request with HTTP 400.

Every schema field carries a ``default`` (its placeholder), so empty or
missing params are accepted and filled with the schema defaults.  The default
prompts (``DefaultRAGGenerationPrompt`` and ``DefaultQARAGenerationPrompt`` —
the QA class name contains a double ``GG``) additionally accept a
language-only ``{"language": ...}`` body: the backend injects
``template = TEMPLATES[language]`` and persists the resolved template.  Empty,
whitespace-only or ``None`` templates are normalised the same way.  Truly
invalid values (wrong types, out-of-range numbers, unknown enums, missing
placeholders) are still rejected with HTTP 400.
"""

import pytest
from fastapi.testclient import TestClient

from tests.back.RAG.conftest import _create_test_document

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------
LLAMA_1B = "bartowski/Llama-3.2-1B-Instruct-GGUF"

COMPLETE_BM25_VECTORIZER_PARAMS = {
    "strip_accents": None,
    "lowercase": True,
    "stop_words": None,
    "max_df": 1.0,
    "min_df": 0.0,
    "max_features": None,
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _complete_params(doc_id, name="strict_valid"):
    """Return a fully-valid RAG session payload for the given document."""
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": name,
        "description": None,
        "parameters": {
            "documents": [doc_id],
            "chunking_model": {
                "component": "CharacterChunkModel",
                "params": {"chunk_size": 200, "chunk_overlap": 20},
            },
            "retriever_model": {
                "component": "BM25Retriever",
                "params": {
                    "BM25Vectorizer": {
                        "component": "BM25VectorizerModel",
                        "params": COMPLETE_BM25_VECTORIZER_PARAMS,
                    },
                    "k1": 1.5,
                    "b": 0.75,
                    "delta": 0.0,
                    "similarity_function": "cosine",
                    "top_k": 5,
                },
            },
            "generation_model": {
                "component": "LlamaModel",
                "params": {
                    "model_name": LLAMA_1B,
                    "quantization": "Q4_K_M",
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
    }


def _bm25_retriever_ref(vectorizer_params: dict) -> dict:
    """Build a ``BM25Retriever`` component reference with vectorizer params."""
    return {
        "component": "BM25Retriever",
        "params": {
            "BM25Vectorizer": {
                "component": "BM25VectorizerModel",
                "params": vectorizer_params,
            },
            "k1": 1.5,
            "b": 0.75,
            "delta": 0.0,
            "similarity_function": "cosine",
            "top_k": 5,
        },
    }


@pytest.fixture(scope="module")
def test_doc_id(client: TestClient) -> int:
    """Module-scoped test document shared across all tests in this file."""
    return _create_test_document(client, suffix="_strict_validation")


# ===================================================================
# POST  /api/v1/generative-session/
# ===================================================================


def test_create_session_with_empty_vectorizer_params_accepted(
    client: TestClient, test_doc_id: int
) -> None:
    """Empty vectorizer ``params`` are accepted and filled with schema defaults."""
    params = _complete_params(test_doc_id, name="strict_incomplete_vectorizer")
    params["parameters"]["retriever_model"]["params"]["BM25Vectorizer"]["params"] = {}

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "An empty BM25 vectorizer params dict should fall back to defaults, "
        f"got {response.status_code}: {response.text}"
    )


def test_create_session_with_empty_generation_model_params_accepted(
    client: TestClient, test_doc_id: int
) -> None:
    """Empty ``LlamaModel`` params are accepted and filled with schema defaults."""
    params = _complete_params(test_doc_id, name="strict_incomplete_llama")
    params["parameters"]["generation_model"]["params"] = {}

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "An empty LlamaModel params dict should fall back to defaults, "
        f"got {response.status_code}: {response.text}"
    )


def test_create_session_with_default_prompt_accepts_language_only(
    client: TestClient, test_doc_id: int
) -> None:
    """A default prompt with only ``language`` is accepted and the injected
    template is persisted."""
    params = _complete_params(test_doc_id, name="strict_default_prompt_language_only")
    params["parameters"]["prompt"] = {
        "component": "DefaultRAGGenerationPrompt",
        "params": {"language": "en"},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "A default prompt with language only should be accepted, "
        f"got {response.status_code}: {response.text}"
    )
    template = response.json()["parameters"]["prompt"]["params"]["template"]
    assert "{input}" in template
    assert "{chunks}" in template


def test_create_session_with_custom_prompt_no_template_uses_default(
    client: TestClient, test_doc_id: int
) -> None:
    """A custom prompt without an explicit template uses the schema default."""
    params = _complete_params(test_doc_id, name="strict_custom_prompt_no_template")
    params["parameters"]["prompt"] = {
        "component": "CustomRAGGenerationPrompt",
        "params": {},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "A custom prompt without a template should use the schema default, "
        f"got {response.status_code}: {response.text}"
    )


def test_create_session_with_invalid_subfield_rejected(
    client: TestClient, test_doc_id: int
) -> None:
    """A non-numeric ``temperature`` fails the recursive schema check → 400."""
    params = _complete_params(test_doc_id, name="strict_invalid_temperature")
    params["parameters"]["generation_model"]["params"]["temperature"] = "not-a-number"

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 400, (
        "An invalid temperature type should be rejected, "
        f"got {response.status_code}: {response.text}"
    )


def test_create_session_with_empty_default_prompt_template_normalized(
    client: TestClient, test_doc_id: int
) -> None:
    """An empty default prompt template is replaced with the language template."""
    params = _complete_params(test_doc_id, name="strict_empty_default_template")
    params["parameters"]["prompt"] = {
        "component": "DefaultRAGGenerationPrompt",
        "params": {"language": "en", "template": ""},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "An empty default prompt template should be normalised, "
        f"got {response.status_code}: {response.text}"
    )
    template = response.json()["parameters"]["prompt"]["params"]["template"]
    assert template != ""
    assert "{input}" in template
    assert "{chunks}" in template


def test_create_session_with_whitespace_default_prompt_template_normalized(
    client: TestClient, test_doc_id: int
) -> None:
    """A whitespace-only default prompt template is replaced."""
    params = _complete_params(test_doc_id, name="strict_whitespace_default_template")
    params["parameters"]["prompt"] = {
        "component": "DefaultRAGGenerationPrompt",
        "params": {"language": "en", "template": "   "},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "A whitespace-only default prompt template should be normalised, "
        f"got {response.status_code}: {response.text}"
    )
    template = response.json()["parameters"]["prompt"]["params"]["template"]
    assert template != ""
    assert "{input}" in template
    assert "{chunks}" in template


def test_create_session_with_null_default_prompt_template_normalized(
    client: TestClient, test_doc_id: int
) -> None:
    """A ``None`` default prompt template is replaced."""
    params = _complete_params(test_doc_id, name="strict_null_default_template")
    params["parameters"]["prompt"] = {
        "component": "DefaultRAGGenerationPrompt",
        "params": {"language": "en", "template": None},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "A None default prompt template should be normalised, "
        f"got {response.status_code}: {response.text}"
    )
    template = response.json()["parameters"]["prompt"]["params"]["template"]
    assert template != ""
    assert "{input}" in template
    assert "{chunks}" in template


def test_create_session_with_custom_prompt_missing_placeholders_rejected(
    client: TestClient, test_doc_id: int
) -> None:
    """A custom prompt template lacking the required placeholders → 400."""
    params = _complete_params(test_doc_id, name="strict_custom_prompt_no_placeholders")
    params["parameters"]["prompt"] = {
        "component": "CustomRAGGenerationPrompt",
        "params": {"template": "hello"},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 400, (
        "A custom prompt missing required placeholders should be rejected, "
        f"got {response.status_code}: {response.text}"
    )


def test_create_session_with_default_prompt_missing_language_uses_default(
    client: TestClient, test_doc_id: int
) -> None:
    """A default prompt without ``language`` uses the schema default language."""
    params = _complete_params(test_doc_id, name="strict_default_prompt_no_language")
    params["parameters"]["prompt"] = {
        "component": "DefaultRAGGenerationPrompt",
        "params": {},
    }

    response = client.post("/api/v1/generative-session/", json=params)
    assert response.status_code == 201, (
        "A default prompt without language should use the default, "
        f"got {response.status_code}: {response.text}"
    )


# ===================================================================
# PUT  /api/v1/generative-session/{id}/parameters/
# ===================================================================


class TestUpdateStrictValidation:
    """Strict validation on parameter updates via PUT."""

    @staticmethod
    def _create_session(client: TestClient, test_doc_id: int, name: str) -> dict:
        """Create a fully-valid session and return its JSON response."""
        params = _complete_params(test_doc_id, name=name)
        response = client.post("/api/v1/generative-session/", json=params)
        assert response.status_code == 201, (
            f"Session prereq failed: {response.status_code}: {response.text}"
        )
        return response.json()

    def test_update_parameters_accepts_incomplete_vectorizer(
        self, client: TestClient, test_doc_id: int
    ) -> None:
        """PUT with an empty vectorizer params dict is accepted (defaults apply)."""
        session = self._create_session(
            client, test_doc_id, "strict_update_incomplete_vectorizer"
        )

        response = client.put(
            f"/api/v1/generative-session/{session['id']}/parameters",
            json={"retriever_model": _bm25_retriever_ref({})},
        )
        assert response.status_code == 200, (
            "An empty BM25 vectorizer params dict should fall back to defaults "
            f"on update, got {response.status_code}: {response.text}"
        )

    def test_update_parameters_accepts_complete_vectorizer(
        self, client: TestClient, test_doc_id: int
    ) -> None:
        """PUT with a complete vectorizer is accepted and persisted as-is."""
        session = self._create_session(
            client, test_doc_id, "strict_update_complete_vectorizer"
        )

        response = client.put(
            f"/api/v1/generative-session/{session['id']}/parameters",
            json={
                "retriever_model": _bm25_retriever_ref(
                    dict(COMPLETE_BM25_VECTORIZER_PARAMS)
                )
            },
        )
        assert response.status_code == 200, (
            "A complete BM25 vectorizer should be accepted on update, "
            f"got {response.status_code}: {response.text}"
        )
        saved = response.json()["parameters"]["retriever_model"]["params"][
            "BM25Vectorizer"
        ]["params"]
        assert saved == COMPLETE_BM25_VECTORIZER_PARAMS

    def test_update_parameters_normalizes_nested_vectorizer_types(
        self, client: TestClient, test_doc_id: int
    ) -> None:
        """PUT with integer ``max_df``/``min_df`` persists them as floats."""
        session = self._create_session(
            client, test_doc_id, "strict_update_vectorizer_type_normalization"
        )
        vectorizer_params = {
            "strip_accents": None,
            "lowercase": True,
            "stop_words": None,
            "max_df": 1,
            "min_df": 0,
            "max_features": None,
        }

        response = client.put(
            f"/api/v1/generative-session/{session['id']}/parameters",
            json={"retriever_model": _bm25_retriever_ref(vectorizer_params)},
        )
        assert response.status_code == 200, (
            f"Integer max_df/min_df should be accepted, "
            f"got {response.status_code}: {response.text}"
        )
        saved = response.json()["parameters"]["retriever_model"]["params"][
            "BM25Vectorizer"
        ]["params"]
        assert isinstance(saved["max_df"], float)
        assert saved["max_df"] == 1.0
        assert isinstance(saved["min_df"], float)
        assert saved["min_df"] == 0.0

    def test_update_parameters_with_default_prompt_accepts_language_only(
        self, client: TestClient, test_doc_id: int
    ) -> None:
        """PUT with a default prompt language-only body injects the template."""
        session = self._create_session(
            client, test_doc_id, "strict_update_default_prompt_language_only"
        )

        response = client.put(
            f"/api/v1/generative-session/{session['id']}/parameters",
            json={
                "prompt": {
                    "component": "DefaultRAGGenerationPrompt",
                    "params": {"language": "en"},
                }
            },
        )
        assert response.status_code == 200, (
            "A default prompt language-only update should be accepted, "
            f"got {response.status_code}: {response.text}"
        )
        template = response.json()["parameters"]["prompt"]["params"]["template"]
        assert "{input}" in template
        assert "{chunks}" in template

    def test_update_parameters_normalizes_empty_default_prompt_template(
        self, client: TestClient, test_doc_id: int
    ) -> None:
        """PUT with an empty default prompt template replaces it."""
        session = self._create_session(
            client, test_doc_id, "strict_update_empty_default_template"
        )

        response = client.put(
            f"/api/v1/generative-session/{session['id']}/parameters",
            json={
                "prompt": {
                    "component": "DefaultRAGGenerationPrompt",
                    "params": {"language": "en", "template": ""},
                }
            },
        )
        assert response.status_code == 200, (
            "An empty default prompt template should be normalised on update, "
            f"got {response.status_code}: {response.text}"
        )
        template = response.json()["parameters"]["prompt"]["params"]["template"]
        assert template != ""
        assert "{input}" in template
        assert "{chunks}" in template

    def test_update_parameters_rejects_prompt_id_of_schema_invalid_prompt(
        self, client: TestClient, test_doc_id: int
    ) -> None:
        """A ``prompt_id`` whose resolved prompt is schema-invalid → 400.

        The ``POST /api/v1/prompt/`` endpoint stores parameters without
        validating them against the component schema, so a default prompt
        with ``language="de"`` (outside the ``[en, es, pt]`` enum) is
        created with 201.  Resolving it during a session PUT must fail the
        recursive schema validation.
        """
        prompt_payload = {
            "class_name": "DefaultRAGGenerationPrompt",
            "name": "strict_schema_invalid_prompt",
            "parameters": {
                "templates": {"de": "Q: {input}\nContext: {chunks}"},
                "language": "de",
            },
        }
        prompt_resp = client.post("/api/v1/prompt/", json=prompt_payload)
        assert prompt_resp.status_code == 201, (
            f"Prompt prereq failed: {prompt_resp.status_code}: {prompt_resp.text}"
        )
        prompt_id = prompt_resp.json()["id"]

        session = self._create_session(
            client, test_doc_id, "strict_update_schema_invalid_prompt_id"
        )

        response = client.put(
            f"/api/v1/generative-session/{session['id']}/parameters",
            json={"prompt_id": prompt_id},
        )
        assert response.status_code == 400, (
            "A prompt_id resolving to a schema-invalid prompt should be rejected, "
            f"got {response.status_code}: {response.text}"
        )
