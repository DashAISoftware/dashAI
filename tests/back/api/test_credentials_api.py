from unittest.mock import patch


def test_get_credential_status_shape(client):
    # the catalog (display name, description) comes from the components
    # endpoint; this endpoint only reports auth state plus the stored key
    response = client.get("/api/v1/credential/HuggingFaceCredential")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "HuggingFaceCredential"
    assert "is_authenticated" in body
    assert "key" in body


def test_credential_components_listed_by_components_endpoint(client):
    response = client.get("/api/v1/component?select_types=Credential")
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert "HuggingFaceCredential" in names
    for component in response.json():
        # description is served here, not by the credential endpoint
        assert "description" in component


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
            json={"key": "bad-secret-key"},
        )
    assert response.status_code == 400
    # the error must never echo the submitted key
    assert "bad-secret-key" not in response.text


def test_auth_unknown_credential_returns_404(client):
    response = client.post("/api/v1/credential/NotACredential/auth", json={"key": "x"})
    assert response.status_code == 404


def test_get_unknown_credential_returns_404(client):
    response = client.get("/api/v1/credential/NotACredential")
    assert response.status_code == 404


def test_delete_unknown_credential_returns_404(client):
    response = client.delete("/api/v1/credential/NotACredential")
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
