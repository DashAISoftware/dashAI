import itertools

import pytest
from sqlalchemy import select

from DashAI.back.auth.cookies import AUTH_COOKIE_NAME
from DashAI.back.dependencies.database.models import User

PASSWORD = "secret-pass-123"

# The client and its database are shared by the whole module, so every test
# registers its own account
_counter = itertools.count()


@pytest.fixture
def account(client):
    """Register a fresh account and leave the client logged in as it."""
    n = next(_counter)
    params = {
        "username": f"user{n}",
        "email": f"User{n}@Example.com",
        "password": PASSWORD,
        "social_name": f"User {n}",
    }
    client.cookies.clear()
    response = client.post("/api/v1/auth/register", json=params)
    assert response.status_code == 201, response.text
    yield {**params, "id": response.json()["id"]}
    client.cookies.clear()


def _session_cookie(client):
    return client.cookies.get(AUTH_COOKIE_NAME)


def _use_cookie(client, token):
    client.cookies.clear()
    client.cookies.set(AUTH_COOKIE_NAME, token)


def _set_user_field(client, user_id, **fields):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        user = db.get(User, user_id)
        for name, value in fields.items():
            setattr(user, name, value)
        db.commit()


# Registration


def test_register_creates_a_member_and_logs_in(client, account):
    me = client.get("/api/v1/auth/me")

    assert me.status_code == 200
    body = me.json()
    assert body["username"] == account["username"]
    # Emails are stored in lowercase
    assert body["email"] == account["email"].lower()
    assert body["global_role"] == {"uid": "member", "name": "Miembro"}
    assert body["permissions"] == ["datasets.read", "models.read"]
    assert "password_hash" not in body
    assert "token_version" not in body


def test_register_stores_a_hash_not_the_password(client, account):
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        stored = db.execute(
            select(User.password_hash).where(User.id == account["id"])
        ).scalar_one()

    assert stored != PASSWORD
    assert stored.startswith("$2b$")


def test_session_cookie_is_http_only(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "cookiecheck",
            "email": "cookie@example.com",
            "password": PASSWORD,
            "social_name": "Cookie",
        },
    )
    set_cookie = response.headers["set-cookie"].lower()

    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    client.cookies.clear()


@pytest.mark.parametrize("field", ["username", "email"])
def test_register_rejects_a_taken_username_or_email(client, account, field):
    params = {
        "username": "brandnew",
        "email": "brandnew@example.com",
        "password": PASSWORD,
        "social_name": "New",
        field: account[field],
    }
    response = client.post("/api/v1/auth/register", json=params)

    assert response.status_code == 409
    assert field in response.json()["detail"]


@pytest.mark.parametrize(
    "changes",
    [
        {"password": "short"},
        {"password": "ñ" * 40},
        {"username": "has spaces"},
        {"username": "ab"},
        {"email": "not-an-email"},
        {"social_name": "   "},
    ],
)
def test_register_validates_its_fields(client, changes):
    params = {
        "username": "valid",
        "email": "valid@example.com",
        "password": PASSWORD,
        "social_name": "Valid",
        **changes,
    }
    response = client.post("/api/v1/auth/register", json=params)

    assert response.status_code == 422


# Login and logout


@pytest.mark.parametrize("by", ["username", "email", "email_other_case"])
def test_login_with_username_or_email(client, account, by):
    identifier = {
        "username": account["username"],
        "email": account["email"].lower(),
        "email_other_case": account["email"].upper(),
    }[by]
    client.cookies.clear()

    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["last_login"] is not None
    assert client.get("/api/v1/auth/me").status_code == 200


def test_wrong_password_and_unknown_user_look_the_same(client, account):
    client.cookies.clear()
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"identifier": account["username"], "password": "not-the-password"},
    )
    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"identifier": "nobody", "password": PASSWORD},
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()
    assert _session_cookie(client) is None


def test_disabled_account_cannot_log_in(client, account):
    _set_user_field(client, account["id"], is_active=False)
    client.cookies.clear()

    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": account["username"], "password": PASSWORD},
    )

    assert response.status_code == 403


def test_logout_ends_the_session(client, account):
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


# Session checks on every request


def test_me_without_a_session_is_unauthorized(client):
    client.cookies.clear()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_a_forged_cookie_is_unauthorized(client):
    _use_cookie(client, "forged.token.value")

    assert client.get("/api/v1/auth/me").status_code == 401


def test_disabling_an_account_ends_its_open_sessions(client, account):
    _set_user_field(client, account["id"], is_active=False)

    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_all_revokes_every_token(client, account):
    old_token = _session_cookie(client)

    response = client.post("/api/v1/auth/logout-all")

    assert response.status_code == 204
    _use_cookie(client, old_token)
    assert client.get("/api/v1/auth/me").status_code == 401


# Profile


def test_update_me_changes_only_the_fields_sent(client, account):
    response = client.patch(
        "/api/v1/auth/me",
        json={"bio": "  Data scientist  ", "phone": "+56 9 1234 5678"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["bio"] == "Data scientist"
    assert body["phone"] == "+56 9 1234 5678"
    assert body["social_name"] == account["social_name"]


def test_update_me_clears_blank_fields(client, account):
    client.patch("/api/v1/auth/me", json={"github": "https://github.com/x"})

    response = client.patch("/api/v1/auth/me", json={"github": ""})

    assert response.json()["github"] is None


@pytest.mark.parametrize("social_name", [None, "  "])
def test_update_me_cannot_clear_the_name(client, account, social_name):
    response = client.patch("/api/v1/auth/me", json={"social_name": social_name})

    assert response.status_code == 422


def test_update_me_ignores_fields_the_user_cannot_edit(client, account):
    response = client.patch(
        "/api/v1/auth/me",
        json={"organization": "Hacked Inc.", "is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["organization"] is None


# Password change


def test_change_password_requires_the_current_one(client, account):
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "new-pass-456"},
    )

    assert response.status_code == 400


def test_change_password_keeps_this_session_and_ends_the_others(client, account):
    other_device = _session_cookie(client)

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "new-pass-456"},
    )

    assert response.status_code == 204
    # This browser received a new token
    assert client.get("/api/v1/auth/me").status_code == 200
    # The token of any other device no longer works
    _use_cookie(client, other_device)
    assert client.get("/api/v1/auth/me").status_code == 401

    client.cookies.clear()
    old = client.post(
        "/api/v1/auth/login",
        json={"identifier": account["username"], "password": PASSWORD},
    )
    new = client.post(
        "/api/v1/auth/login",
        json={"identifier": account["username"], "password": "new-pass-456"},
    )
    assert old.status_code == 401
    assert new.status_code == 200
