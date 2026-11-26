"""Every API route needs a session, except the ones the login screen uses."""

import re

import pytest
from starlette.testclient import WebSocketDenialResponse

# Inside /auth, the routes about the current account check the session
# themselves; /app-config is read before anyone logs in
PUBLIC_ROUTES = {
    ("post", "/auth/register"),
    ("post", "/auth/login"),
    ("post", "/auth/logout"),
    ("get", "/app-config/"),
}


@pytest.fixture
def anonymous(client):
    """Drop the session for one test and restore it afterwards."""
    cookies = dict(client.cookies)
    client.cookies.clear()
    yield client
    client.cookies.clear()
    client.cookies.update(cookies)


def _api_operations(client):
    paths = client.get("/api/v1/openapi.json").json()["paths"]
    return [
        (method, path)
        for path, operations in paths.items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    ]


def test_every_route_but_the_public_ones_needs_a_session(client, anonymous):
    operations = _api_operations(client)
    open_routes = []
    for method, path in operations:
        if (method, path) in PUBLIC_ROUTES:
            continue
        # The session is checked before the parameters, so any value works
        url = "/api/v1" + re.sub(r"\{[^}]+\}", "1", path)
        response = anonymous.request(method.upper(), url)
        if response.status_code != 401:
            open_routes.append(f"{method.upper()} {path}: {response.status_code}")

    assert len(operations) > 100
    assert open_routes == []


def test_public_routes_exist(client):
    # Guards the list above against a renamed route that would silently
    # stop being checked
    assert set(_api_operations(client)) >= PUBLIC_ROUTES


def test_private_routes_work_with_a_session(client):
    assert client.get("/api/v1/component/").status_code == 200


def test_app_config_works_without_a_session(anonymous):
    assert anonymous.get("/api/v1/app-config/").status_code == 200


@pytest.mark.parametrize("path", ["/api/v1/hardware/ws", "/api/v1/metrics/ws/1"])
def test_websockets_are_refused_without_a_session(anonymous, path):
    with (
        pytest.raises(WebSocketDenialResponse) as denied,
        anonymous.websocket_connect(path),
    ):
        pass

    assert denied.value.status_code == 401
