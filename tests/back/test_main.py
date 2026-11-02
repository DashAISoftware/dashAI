from fastapi.testclient import TestClient

from DashAI.back.app import create_app


def test_app_front(tmp_path):
    # Without local_path the app opens, and migrates, the ~/.DashAI of
    # whoever runs the suite.
    client = TestClient(
        create_app(local_path=tmp_path, logging_level="ERROR", enable_seeding=False)
    )

    response = client.get("/app/")
    assert response.status_code == 200
