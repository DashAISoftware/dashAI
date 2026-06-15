from unittest.mock import patch


def test_list_credentials(client):
    response = client.get("/api/v1/credential/")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert "HuggingFaceCredential" in names
    for cred in response.json():
        assert "is_authenticated" in cred
        assert "key" not in cred  # never leak keys


def test_auth_success_marks_authenticated(client):
    with patch(
        "DashAI.back.credentials.huggingface_credential.HuggingFaceCredential.verify",
        return_value=True,
    ):
        response = client.post(
            "/api/v1/credential/HuggingFaceCredential/auth",
            json={"key": "hf_token"},
        )
    assert response.status_code == 200
    assert response.json()["is_authenticated"] is True

    status = client.get("/api/v1/credential/HuggingFaceCredential")
    assert status.json()["is_authenticated"] is True


def test_auth_invalid_key_returns_400(client):
    with patch(
        "DashAI.back.credentials.huggingface_credential.HuggingFaceCredential.verify",
        return_value=False,
    ):
        response = client.post(
            "/api/v1/credential/HuggingFaceCredential/auth",
            json={"key": "bad"},
        )
    assert response.status_code == 400


def test_auth_unknown_credential_returns_404(client):
    response = client.post("/api/v1/credential/NotACredential/auth", json={"key": "x"})
    assert response.status_code == 404


def test_delete_credential(client):
    with patch(
        "DashAI.back.credentials.huggingface_credential.HuggingFaceCredential.verify",
        return_value=True,
    ):
        client.post(
            "/api/v1/credential/HuggingFaceCredential/auth",
            json={"key": "hf_token"},
        )
    response = client.delete("/api/v1/credential/HuggingFaceCredential")
    assert response.status_code == 200
    status = client.get("/api/v1/credential/HuggingFaceCredential")
    assert status.json()["is_authenticated"] is False
