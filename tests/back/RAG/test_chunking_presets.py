"""Tests for the chunking-presets endpoint."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from DashAI.back.services.RAG import chunking_presets


def test_chunking_presets_returns_four_presets(client: TestClient):
    response = client.get("/api/v1/rag/chunking-presets")
    assert response.status_code == 200
    data = response.json()
    assert [p["key"] for p in data] == ["small", "paragraph", "page", "large"]


def test_every_preset_is_a_complete_recipe(client: TestClient):
    data = client.get("/api/v1/rag/chunking-presets").json()
    for preset in data:
        assert preset["component"] == "CharacterChunkModel"
        assert isinstance(preset["params"]["chunk_size"], int)
        assert isinstance(preset["params"]["chunk_overlap"], int)


def test_paragraph_preset_matches_the_session_default(client: TestClient):
    data = client.get("/api/v1/rag/chunking-presets").json()
    paragraph = next(p for p in data if p["key"] == "paragraph")
    assert paragraph["params"]["chunk_size"] == 500
    assert paragraph["params"]["chunk_overlap"] == 50

    defaults = client.get("/api/v1/rag/session-defaults").json()
    assert defaults["chunking_model"]["component"] == paragraph["component"]
    assert defaults["chunking_model"]["params"] == paragraph["params"]


def test_presets_are_localized(client: TestClient):
    english = client.get("/api/v1/rag/chunking-presets").json()
    spanish = client.get(
        "/api/v1/rag/chunking-presets", headers={"Accept-Language": "es"}
    ).json()

    by_key_en = {p["key"]: p for p in english}
    by_key_es = {p["key"]: p for p in spanish}

    assert by_key_en["paragraph"]["display_name"] == "Paragraph length"
    assert by_key_es["paragraph"]["display_name"] == "Largo de un párrafo"
    # Names arrive as plain strings, never as language objects.
    assert isinstance(by_key_es["small"]["display_name"], str)
    assert "caracteres" in by_key_es["small"]["description"]


def test_retriever_presets_are_localized(client: TestClient):
    spanish = client.get(
        "/api/v1/rag/retriever-presets",
        params={"top_k": 10},
        headers={"Accept-Language": "es"},
    ).json()
    by_key = {p["key"]: p for p in spanish}
    assert by_key["hybrid"]["display_name"] == "Híbrido"
    assert by_key["keyword"]["display_name"] == "Palabras clave"


def test_session_defaults_need_no_download(client: TestClient):
    """The defaults must never gate session creation behind a model download.

    Keyword retrieval is chosen precisely because it pulls no weights; if this
    ever changes, creating a session with defaults starts failing with 409.
    """
    defaults = client.get("/api/v1/rag/session-defaults").json()
    assert defaults["retriever_model"]["component"] == "BM25Retriever"

    required = client.post(
        "/api/v1/component/downloads/required",
        json={"model_name": None, "parameters": defaults},
    )
    assert required.status_code == 200
    assert required.json() == []


def test_session_defaults_carry_display_names(client: TestClient):
    defaults = client.get(
        "/api/v1/rag/session-defaults", headers={"Accept-Language": "es"}
    ).json()
    for key in ("chunking_model", "retriever_model", "prompt"):
        display_name = defaults[key]["display_name"]
        assert isinstance(display_name, str)
        assert display_name
        assert display_name != defaults[key]["component"], (
            f"{key} still falls back to its class name"
        )


def test_session_defaults_follow_the_request_language(client: TestClient):
    spanish = client.get(
        "/api/v1/rag/session-defaults", headers={"Accept-Language": "es"}
    ).json()
    assert spanish["prompt"]["params"]["language"] == "es"

    # A language the default prompt has no template for falls back to English.
    german = client.get(
        "/api/v1/rag/session-defaults", headers={"Accept-Language": "de"}
    ).json()
    assert german["prompt"]["params"]["language"] == "en"


# ── Preset matching ──────────────────────────────────────────────────────────


def _registry(client: TestClient):
    """Return the application's component registry."""
    return client.app.container["component_registry"]


def _recipe(client: TestClient, key: str) -> dict[str, Any]:
    """Return one chunking preset recipe resolved against the registry."""
    presets = chunking_presets.get_chunking_presets(_registry(client))
    return next(preset for preset in presets if preset["key"] == key)


def test_every_exact_recipe_matches_its_own_preset(client: TestClient):
    registry = _registry(client)
    for recipe in chunking_presets.get_chunking_presets(registry):
        assert (
            chunking_presets.match_preset_key(
                recipe["component"], recipe["params"], registry
            )
            == recipe["key"]
        )


def test_extra_parameter_makes_the_chunking_config_custom(client: TestClient):
    """A stored chunker with a parameter the recipe lacks no longer matches."""
    recipe = _recipe(client, "paragraph")
    with_extra = {**recipe["params"], "unexpected_parameter": 1}

    assert (
        chunking_presets.match_preset_key(
            recipe["component"], with_extra, _registry(client)
        )
        is None
    )


def test_missing_parameter_makes_the_chunking_config_custom(client: TestClient):
    recipe = _recipe(client, "paragraph")
    missing = {k: v for k, v in recipe["params"].items() if k != "chunk_overlap"}

    assert (
        chunking_presets.match_preset_key(
            recipe["component"], missing, _registry(client)
        )
        is None
    )


def test_changed_chunk_size_is_custom_not_the_neighbouring_preset(client: TestClient):
    recipe = _recipe(client, "paragraph")
    resized = {**recipe["params"], "chunk_size": 501}

    assert (
        chunking_presets.match_preset_key(
            recipe["component"], resized, _registry(client)
        )
        is None
    )


def test_key_order_does_not_change_the_chunking_match(client: TestClient):
    recipe = _recipe(client, "page")
    reordered = dict(reversed(list(recipe["params"].items())))

    assert list(reordered) != list(recipe["params"])
    assert (
        chunking_presets.match_preset_key(
            recipe["component"], reordered, _registry(client)
        )
        == "page"
    )


def test_another_chunker_is_never_a_preset(client: TestClient):
    recipe = _recipe(client, "paragraph")

    assert (
        chunking_presets.match_preset_key(
            "SomeOtherChunker", recipe["params"], _registry(client)
        )
        is None
    )


def test_malformed_params_raise_even_for_another_chunker(client: TestClient):
    """The contract is checked before a non-default component returns early."""
    registry = _registry(client)
    with pytest.raises(TypeError):
        chunking_presets.match_preset_key(
            "SomeOtherChunker", {"chunk_size": (500,)}, registry
        )
    with pytest.raises(ValueError, match="non-finite"):
        chunking_presets.match_preset_key(
            "SomeOtherChunker", {"chunk_size": float("nan")}, registry
        )
