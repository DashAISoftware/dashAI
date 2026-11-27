"""The administration account and the routes that change the instance."""

import pytest

INSTANCE_ROUTES = [
    ("post", "/api/v1/plugin/"),
    ("post", "/api/v1/plugin/index"),
    ("patch", "/api/v1/plugin/1"),
    ("patch", "/api/v1/plugin/1/upgrade"),
    ("delete", "/api/v1/plugin/1"),
    ("post", "/api/v1/system/update/download"),
    ("post", "/api/v1/system/update/install"),
]


@pytest.mark.parametrize(("method", "path"), INSTANCE_ROUTES)
def test_members_cannot_change_the_instance(client, method, path):
    # The client starts logged in as a member
    response = client.request(method.upper(), path)

    assert response.status_code == 403


def test_members_can_still_list_plugins(client):
    assert client.get("/api/v1/plugin/").status_code == 200


def test_the_administration_account_exists_from_the_start(client, system_admin):
    me = client.get("/api/v1/auth/me").json()

    assert me["username"] == "admin"
    assert me["global_role"]["uid"] == "admin"


def test_the_administration_account_can_change_plugins(client, system_admin):
    response = client.post("/api/v1/plugin/", json=[])

    assert response.status_code == 201


def test_changing_its_password_deletes_the_generated_one(client, system_admin):
    config = client.app.container["config"]
    password_path = config["ADMIN_PASSWORD_PATH"]
    password = password_path.read_text(encoding="utf-8").strip()

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": password, "new_password": "new-secret-123"},
    )

    assert response.status_code == 204, response.text
    assert not password_path.exists()
