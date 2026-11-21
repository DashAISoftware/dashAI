"""Credential endpoints: every user stores and sees only their own keys."""

import itertools
from unittest.mock import patch

import pytest

PASSWORD = "secret-pass-123"
VERIFY = "DashAI.back.credentials.huggingface_credential.HuggingFaceCredential.verify"
_counter = itertools.count()


def _register(client):
    """Register a new account, which leaves the client logged in as it."""
    n = next(_counter)
    username = f"creduser{n}"
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "social_name": f"Credential User {n}",
        },
    )
    assert response.status_code == 201, response.text
    return username


def _login_as(client, username):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text


def _store_hf_token(client, key="hf_token"):
    with patch(VERIFY, return_value=True):
        response = client.post(
            "/api/v1/credential/HuggingFaceCredential/auth", json={"key": key}
        )
    assert response.status_code == 200, response.text


def _hf_status(client):
    return client.get("/api/v1/credential/HuggingFaceCredential").json()


@pytest.fixture
def user(client):
    username = _register(client)
    yield username
    client.cookies.clear()


def test_list_credentials(client, user):
    response = client.get("/api/v1/credential/")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert "HuggingFaceCredential" in names
    for cred in response.json():
        assert "is_authenticated" in cred
        # catalog + status returned together in one request
        assert "display_name" in cred
        assert "description" in cred
        assert "key" in cred


def test_auth_success_marks_authenticated(client, user):
    _store_hf_token(client)

    status = _hf_status(client)
    assert status["is_authenticated"] is True
    assert status["key"] == "hf_token"


def test_auth_invalid_key_returns_400(client, user):
    with patch(VERIFY, return_value=False):
        response = client.post(
            "/api/v1/credential/HuggingFaceCredential/auth",
            json={"key": "bad-secret-key"},
        )
    assert response.status_code == 400
    # the error must never echo the submitted key
    assert "bad-secret-key" not in response.text


def test_auth_unknown_credential_returns_404(client, user):
    response = client.post("/api/v1/credential/NotACredential/auth", json={"key": "x"})
    assert response.status_code == 404


def test_get_unknown_credential_returns_404(client, user):
    response = client.get("/api/v1/credential/NotACredential")
    assert response.status_code == 404


def test_delete_unknown_credential_returns_404(client, user):
    response = client.delete("/api/v1/credential/NotACredential")
    assert response.status_code == 404


def test_delete_credential(client, user):
    _store_hf_token(client)

    response = client.delete("/api/v1/credential/HuggingFaceCredential")
    assert response.status_code == 200
    assert _hf_status(client)["is_authenticated"] is False


def test_routes_need_a_session(client):
    client.cookies.clear()

    assert client.get("/api/v1/credential/").status_code == 401
    assert client.get("/api/v1/credential/HuggingFaceCredential").status_code == 401
    assert (
        client.post(
            "/api/v1/credential/HuggingFaceCredential/auth", json={"key": "x"}
        ).status_code
        == 401
    )
    assert client.delete("/api/v1/credential/HuggingFaceCredential").status_code == 401


def test_users_only_see_their_own_credentials(client):
    owner = _register(client)
    _store_hf_token(client, key="hf_owner_token")
    _register(client)

    status = _hf_status(client)
    assert status["is_authenticated"] is False
    assert status["key"] is None

    # Each user keeps their own key for the same platform
    _store_hf_token(client, key="hf_other_token")
    assert _hf_status(client)["key"] == "hf_other_token"
    _login_as(client, owner)
    assert _hf_status(client)["key"] == "hf_owner_token"
    client.cookies.clear()


def test_deleting_only_removes_the_users_own_credential(client):
    owner = _register(client)
    _store_hf_token(client, key="hf_owner_token")
    _register(client)
    _store_hf_token(client, key="hf_other_token")

    client.delete("/api/v1/credential/HuggingFaceCredential")

    _login_as(client, owner)
    assert _hf_status(client)["key"] == "hf_owner_token"
    client.cookies.clear()


def test_components_report_the_users_credentials(client):
    def satisfied():
        response = client.get("/api/v1/component/SAM3SegmentConverter/")
        assert response.status_code == 200, response.text
        return response.json()["credentials_satisfied"]

    owner = _register(client)
    assert satisfied() is False
    _store_hf_token(client)
    assert satisfied() is True

    _register(client)
    assert satisfied() is False

    _login_as(client, owner)
    assert satisfied() is True
    client.cookies.clear()
