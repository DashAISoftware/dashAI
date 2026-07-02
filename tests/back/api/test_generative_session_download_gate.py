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
