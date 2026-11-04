from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from DashAI.back.auth.dependencies import get_current_user, require_permission


def _user_with(*permission_uids):
    permissions = [SimpleNamespace(uid=uid) for uid in permission_uids]
    return SimpleNamespace(id=1, global_role=SimpleNamespace(permissions=permissions))


def _client_for(user):
    app = FastAPI()

    @app.get("/protected")
    def protected(current=Depends(require_permission("users.manage"))):
        return {"id": current.id}

    # The user lookup is tested through the auth API; here only the
    # permission check runs
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_user_with_the_permission_gets_through():
    response = _client_for(_user_with("users.manage")).get("/protected")

    assert response.status_code == 200
    assert response.json() == {"id": 1}


def test_user_without_the_permission_is_forbidden():
    response = _client_for(_user_with("datasets.read")).get("/protected")

    assert response.status_code == 403
