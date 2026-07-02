"""Tests for the generative-session creation download gate."""

from kink import di

_SESSION_PAYLOAD_BASE = {
    "parameters": {},
    "name": "gen-gate-test-session",
    "description": None,
}


class _FakeDownloadableGenerativeModel:
    """Minimal stub: download-required generative model that is not downloaded."""

    REQUIRES_DOWNLOAD = True

    @classmethod
    def is_downloaded(cls):
        return False


class _FakeGenerativeRegistry:
    """Registry wrapper that injects FakeDownloadableGenerativeModel."""

    def __init__(self, real):
        self._real = real

    def __getitem__(self, name):
        if name == "FakeDownloadableGenerativeModel":
            return {
                "class": _FakeDownloadableGenerativeModel,
                "downloaded": False,
            }
        return self._real[name]

    def get_components_by_types(self, select=None, ignore=None):
        return self._real.get_components_by_types(select=select, ignore=ignore)

    def __contains__(self, name):
        return name == "FakeDownloadableGenerativeModel" or name in self._real


def test_upload_generative_session_rejects_undownloaded_model(client):
    """Creating a session for a not-yet-downloaded model must return HTTP 409."""
    old = di["component_registry"]
    di["component_registry"] = _FakeGenerativeRegistry(old)
    try:
        resp = client.post(
            "/api/v1/generative-session/",
            json={
                "model_name": "FakeDownloadableGenerativeModel",
                "task_name": "TextToTextGenerationTask",
                **_SESSION_PAYLOAD_BASE,
            },
        )
    finally:
        di["component_registry"] = old

    assert resp.status_code == 409
    assert "download" in resp.json()["detail"].lower()


def test_upload_generative_session_unknown_model_400(client):
    """POSTing a session with an unregistered model_name must return HTTP 400."""
    resp = client.post(
        "/api/v1/generative-session/",
        json={
            "model_name": "__totally_bogus_generative_model_xyz__",
            "task_name": "TextToTextGenerationTask",
            **_SESSION_PAYLOAD_BASE,
        },
    )
    assert resp.status_code == 400
    assert "is not registered" in resp.json()["detail"]


_SD_PARAMS = {
    "num_inference_steps": 1,
    "model_name": "sd2-community/stable-diffusion-2",
    "guidance_scale": 6.0,
    "device": "CPU",
    "negative_prompt": "",
    "seed": 42,
    "width": 256,
    "height": 256,
    "num_images_per_prompt": 1,
}


def _create_sd_session(client, name):
    return client.post(
        "/api/v1/generative-session/",
        json={
            "model_name": "StableDiffusionV2Model",
            "task_name": "TextToImageGenerationTask",
            "parameters": _SD_PARAMS,
            "name": name,
            "description": None,
        },
    )


def test_change_session_model_to_undownloaded_returns_409(client):
    """Switching a session to a not-downloaded model must return HTTP 409."""
    created = _create_sd_session(client, "gen-switch-409")
    assert created.status_code == 201
    session_id = created.json()["id"]

    resp = client.patch(
        f"/api/v1/generative-session/{session_id}",
        params={"model_name": "Qwen25_15BInstruct"},
    )
    assert resp.status_code == 409
    assert "download" in resp.json()["detail"].lower()

    client.delete(f"/api/v1/generative-session/{session_id}")


def test_change_session_model_unknown_returns_400(client):
    """Switching a session to an unregistered model must return HTTP 400."""
    created = _create_sd_session(client, "gen-switch-400")
    assert created.status_code == 201
    session_id = created.json()["id"]

    resp = client.patch(
        f"/api/v1/generative-session/{session_id}",
        params={"model_name": "__totally_bogus_generative_model_xyz__"},
    )
    assert resp.status_code == 400
    assert "is not registered" in resp.json()["detail"]

    client.delete(f"/api/v1/generative-session/{session_id}")


def test_change_session_model_valid_returns_200(client):
    """Switching a session to a valid (non-download) model must succeed."""
    created = _create_sd_session(client, "gen-switch-200")
    assert created.status_code == 201
    session_id = created.json()["id"]

    resp = client.patch(
        f"/api/v1/generative-session/{session_id}",
        params={"model_name": "StableDiffusionV2Model"},
    )
    assert resp.status_code == 200
    assert resp.json()["model_name"] == "StableDiffusionV2Model"

    client.delete(f"/api/v1/generative-session/{session_id}")
