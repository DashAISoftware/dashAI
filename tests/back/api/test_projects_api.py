import itertools

import pytest
from sqlalchemy import select

from DashAI.back.dependencies.database.models import Permission, Role, User

PASSWORD = "secret-pass-123"

# The client and its database are shared by the whole module, so every test
# registers its own accounts
_counter = itertools.count()


def _register(client):
    n = next(_counter)
    username = f"projuser{n}"
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "social_name": f"Project User {n}",
        },
    )
    assert response.status_code == 201, response.text
    return {"id": response.json()["id"], "username": username}


def _login_as(client, account):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": account["username"], "password": PASSWORD},
    )
    assert response.status_code == 200, response.text


def _make_admin(client, account):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        admin = db.execute(select(Role).where(Role.uid == "admin")).scalar_one()
        db.get(User, account["id"]).global_role_id = admin.id
        db.commit()


@pytest.fixture
def owner(client):
    account = _register(client)
    yield account
    client.cookies.clear()


@pytest.fixture
def outsider(client):
    return _register(client)


@pytest.fixture
def project(client, owner, outsider):
    """A project created by ``owner``, who stays logged in.

    Depends on ``outsider`` so that account is registered first: registering
    logs in, which would otherwise replace the owner's session.
    """
    _login_as(client, owner)
    response = client.post("/api/v1/project/", json={"name": "  Demo  "})
    assert response.status_code == 201, response.text
    return response.json()


def _add(client, project, account, role_uid):
    return client.post(
        f"/api/v1/project/{project['id']}/members",
        json={"username": account["username"], "role_uid": role_uid},
    )


def _members(client, project):
    response = client.get(f"/api/v1/project/{project['id']}/members")
    assert response.status_code == 200, response.text
    return {m["username"]: m["role"]["uid"] for m in response.json()}


# Creating and listing projects


def test_creator_becomes_the_owner(client, owner, project):
    assert project["name"] == "Demo"
    assert project["member_count"] == 1
    assert project["my_role"] == {"uid": "owner", "name": "Dueño"}
    assert "projects.manage" in project["my_permissions"]
    assert _members(client, project) == {owner["username"]: "owner"}


def test_create_requires_a_session(client):
    client.cookies.clear()

    response = client.post("/api/v1/project/", json={"name": "Nope"})

    assert response.status_code == 401


def test_list_shows_only_my_projects(client, owner, project, outsider):
    _login_as(client, outsider)
    client.post("/api/v1/project/", json={"name": "Other"})

    names = [p["name"] for p in client.get("/api/v1/project/").json()]

    assert names == ["Other"]


# Entering a project


def test_outsider_sees_the_project_as_missing(client, project, outsider):
    _login_as(client, outsider)

    for path in ["", "/members"]:
        response = client.get(f"/api/v1/project/{project['id']}{path}")
        assert response.status_code == 404
    # Same answer as a project that does not exist
    assert client.get("/api/v1/project/999999").status_code == 404


def test_admin_enters_any_project_with_every_permission(client, project, outsider):
    _make_admin(client, outsider)
    _login_as(client, outsider)

    response = client.get(f"/api/v1/project/{project['id']}")

    assert response.status_code == 200
    assert response.json()["my_role"] is None
    assert "projects.manage" in response.json()["my_permissions"]


def test_reader_gets_only_read_permissions(client, project, outsider):
    _add(client, project, outsider, "reader")
    _login_as(client, outsider)

    body = client.get(f"/api/v1/project/{project['id']}").json()

    assert body["my_role"]["uid"] == "reader"
    assert all(uid.endswith(".read") for uid in body["my_permissions"])
    # The global "member" role has datasets.write, but it does not count
    # inside the project
    assert "datasets.write" not in body["my_permissions"]


# Managing members


def test_owner_adds_a_member(client, owner, project, outsider):
    response = _add(client, project, outsider, "collaborator")

    assert response.status_code == 201
    assert response.json()["role"]["uid"] == "collaborator"
    assert _members(client, project)[outsider["username"]] == "collaborator"


@pytest.mark.parametrize(
    ("username", "role_uid", "expected"),
    [
        ("nobody-here", "reader", 404),
        (None, "admin", 422),
        (None, "not-a-role", 422),
    ],
)
def test_add_member_validates_user_and_role(
    client, project, outsider, username, role_uid, expected
):
    account = {"username": username or outsider["username"]}

    assert _add(client, project, account, role_uid).status_code == expected


def test_adding_twice_conflicts(client, project, outsider):
    _add(client, project, outsider, "reader")

    assert _add(client, project, outsider, "reader").status_code == 409


def test_reader_cannot_manage_members(client, owner, project, outsider):
    third = _register(client)
    _login_as(client, owner)
    _add(client, project, outsider, "reader")
    _add(client, project, third, "reader")
    _login_as(client, outsider)
    base = f"/api/v1/project/{project['id']}/members"

    assert _add(client, project, {"username": "x"}, "reader").status_code == 403
    assert (
        client.patch(f"{base}/{third['id']}", json={"role_uid": "manager"}).status_code
        == 403
    )
    assert client.delete(f"{base}/{third['id']}").status_code == 403


def test_only_owners_handle_the_owner_role(client, owner, project, outsider):
    # An administrator may give "Gestor" the right to manage members; even
    # then a manager must not be able to make owners or demote them
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        manager = db.execute(select(Role).where(Role.uid == "manager")).scalar_one()
        manager.permissions.append(
            db.execute(
                select(Permission).where(Permission.uid == "projects.manage")
            ).scalar_one()
        )
        db.commit()

    try:
        third = _register(client)
        _login_as(client, owner)
        _add(client, project, outsider, "manager")
        _add(client, project, third, "reader")
        _login_as(client, outsider)
        base = f"/api/v1/project/{project['id']}/members"

        # A manager can now handle other roles
        assert (
            client.patch(
                f"{base}/{third['id']}", json={"role_uid": "collaborator"}
            ).status_code
            == 200
        )
        # But not the owner role, in either direction
        assert (
            client.patch(
                f"{base}/{third['id']}", json={"role_uid": "owner"}
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"{base}/{outsider['id']}", json={"role_uid": "owner"}
            ).status_code
            == 403
        )
        assert (
            client.patch(
                f"{base}/{owner['id']}", json={"role_uid": "reader"}
            ).status_code
            == 403
        )
        assert client.delete(f"{base}/{owner['id']}").status_code == 403
    finally:
        with session_factory() as db:
            manager = db.execute(select(Role).where(Role.uid == "manager")).scalar_one()
            manager.permissions = [
                p for p in manager.permissions if p.uid != "projects.manage"
            ]
            db.commit()


def test_owner_changes_a_role(client, project, outsider):
    _add(client, project, outsider, "reader")

    response = client.patch(
        f"/api/v1/project/{project['id']}/members/{outsider['id']}",
        json={"role_uid": "manager"},
    )

    assert response.status_code == 200
    assert _members(client, project)[outsider["username"]] == "manager"


def test_last_owner_cannot_leave_or_be_demoted(client, owner, project):
    base = f"/api/v1/project/{project['id']}/members/{owner['id']}"

    assert client.patch(base, json={"role_uid": "reader"}).status_code == 409
    assert client.delete(base).status_code == 409


def test_member_can_leave(client, owner, project, outsider):
    _add(client, project, outsider, "reader")
    _login_as(client, outsider)

    response = client.delete(
        f"/api/v1/project/{project['id']}/members/{outsider['id']}"
    )

    assert response.status_code == 204
    _login_as(client, owner)
    assert outsider["username"] not in _members(client, project)
