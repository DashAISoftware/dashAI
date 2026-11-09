"""Who can do what with datasets, depending on their project role.

The client and its database are shared by the whole module, so every test
creates its own accounts and projects.
"""

import itertools

import pytest
from sqlalchemy import select

from DashAI.back.dependencies.database.models import Dataset, Role, User

PASSWORD = "secret-pass-123"
_counter = itertools.count()


def _register(client):
    n = next(_counter)
    username = f"dsuser{n}"
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "social_name": f"Dataset User {n}",
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


def _create_project(client, name="Project"):
    response = client.post("/api/v1/project/", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_dataset(client, project_id, name):
    return client.post(
        "/api/v1/dataset/", params={"project_id": project_id}, json={"name": name}
    )


def _add(client, project_id, account, role_uid):
    response = client.post(
        f"/api/v1/project/{project_id}/members",
        json={"username": account["username"], "role_uid": role_uid},
    )
    assert response.status_code == 201, response.text


def _listed_names(client, project_id=None):
    params = {"project_id": project_id} if project_id is not None else {}
    response = client.get("/api/v1/dataset/", params=params)
    assert response.status_code == 200, response.text
    return {d["name"] for d in response.json()}


@pytest.fixture
def team(client):
    """An owner with a project and one dataset, plus a user per project role.

    Leaves the client logged in as the owner.
    """
    people = {role: _register(client) for role in ["reader", "collaborator"]}
    people["outsider"] = _register(client)
    owner = _register(client)
    project_id = _create_project(client)
    for role in ["reader", "collaborator"]:
        _add(client, project_id, people[role], role)

    response = _create_dataset(client, project_id, f"data{next(_counter)}")
    assert response.status_code == 201, response.text
    yield {
        **people,
        "owner": owner,
        "project_id": project_id,
        "dataset": response.json(),
    }
    client.cookies.clear()


@pytest.fixture
def universal(client):
    """A dataset without a project, as the ones created before projects."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        dataset = Dataset(name=f"universal{next(_counter)}", file_path="")
        db.add(dataset)
        db.commit()
        return {"id": dataset.id, "name": dataset.name}


# Creating and listing


def test_new_datasets_belong_to_the_project(client, team):
    assert team["dataset"]["project_id"] == team["project_id"]


def test_create_without_a_project_is_rejected(client, team):
    response = client.post("/api/v1/dataset/", json={"name": "orphan"})

    assert response.status_code == 422


def test_names_are_unique_per_project(client, team):
    name = team["dataset"]["name"]
    other_project = _create_project(client, "Other")

    assert _create_dataset(client, team["project_id"], name).status_code == 409
    assert _create_dataset(client, other_project, name).status_code == 201


def test_list_shows_the_project_and_universal_datasets(client, team, universal):
    names = _listed_names(client, team["project_id"])

    assert team["dataset"]["name"] in names
    assert universal["name"] in names


def test_list_without_a_project_shows_only_universal_datasets(client, team, universal):
    names = _listed_names(client)

    assert universal["name"] in names
    assert team["dataset"]["name"] not in names


def test_outsider_cannot_see_the_project_datasets(client, team):
    _login_as(client, team["outsider"])
    dataset_id = team["dataset"]["id"]

    assert client.get(f"/api/v1/dataset/{dataset_id}").status_code == 404
    response = client.get("/api/v1/dataset/", params={"project_id": team["project_id"]})
    assert response.status_code == 404
    assert team["dataset"]["name"] not in _listed_names(client)


def test_routes_need_a_session(client, team):
    client.cookies.clear()

    assert client.get("/api/v1/dataset/").status_code == 401
    assert client.get(f"/api/v1/dataset/{team['dataset']['id']}").status_code == 401


# Project roles


def test_reader_can_only_read(client, team):
    _login_as(client, team["reader"])
    base = f"/api/v1/dataset/{team['dataset']['id']}"

    assert client.get(base).status_code == 200
    assert client.patch(base, json={"name": "renamed"}).status_code == 403
    assert client.delete(base).status_code == 403
    assert _create_dataset(client, team["project_id"], "new").status_code == 403


def test_collaborator_cannot_delete_or_export(client, team):
    _login_as(client, team["collaborator"])
    base = f"/api/v1/dataset/{team['dataset']['id']}"

    assert client.patch(base, json={"name": "renamed"}).status_code == 200
    assert client.delete(base).status_code == 403
    assert client.get(f"{base}/export/csv").status_code == 403


def test_bulk_delete_is_all_or_nothing(client, team, universal):
    # The owner can delete the project dataset but not the universal one
    response = client.request(
        "DELETE",
        "/api/v1/dataset/",
        json={"ids": [team["dataset"]["id"], universal["id"]]},
    )

    assert response.status_code == 403
    assert client.get(f"/api/v1/dataset/{team['dataset']['id']}").status_code == 200


def test_copy_out_of_another_project_needs_export(client, team):
    # The collaborator owns a second project but cannot export from the first
    _login_as(client, team["collaborator"])
    own_project = _create_project(client, "Own")

    response = client.post(
        "/api/v1/dataset/copy",
        params={"project_id": own_project},
        json={"dataset_id": team["dataset"]["id"]},
    )

    assert response.status_code == 403


# Universal datasets


def test_anyone_reads_universal_datasets_but_cannot_change_them(
    client, team, universal
):
    _login_as(client, team["outsider"])
    base = f"/api/v1/dataset/{universal['id']}"

    assert client.get(base).status_code == 200
    assert client.patch(base, json={"name": "renamed"}).status_code == 403
    assert client.delete(base).status_code == 403


def test_admin_changes_universal_datasets(client, team, universal):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        admin = db.execute(select(Role).where(Role.uid == "admin")).scalar_one()
        db.get(User, team["outsider"]["id"]).global_role_id = admin.id
        db.commit()
    _login_as(client, team["outsider"])
    base = f"/api/v1/dataset/{universal['id']}"

    response = client.patch(base, json={"name": f"{universal['name']}_renamed"})

    assert response.status_code == 200
    assert client.delete(base).status_code == 204
