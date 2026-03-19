from fastapi.testclient import TestClient


class TestGetHardwareStats:
    def test_get_snapshot(self, client: TestClient):
        response = client.get("/api/v1/hardware/")
        assert response.status_code == 200
        data = response.json()

        assert "cpu" in data
        assert "ram" in data
        assert "gpus" in data

        assert isinstance(data["cpu"]["percent"], (int, float))
        assert isinstance(data["cpu"]["per_cpu"], list)
        assert isinstance(data["cpu"]["cores_logical"], int)

        assert isinstance(data["ram"]["percent"], (int, float))
        assert isinstance(data["ram"]["used"], int)
        assert isinstance(data["ram"]["total"], int)

        assert isinstance(data["gpus"], list)

    def test_websocket_connection(self, client: TestClient):
        with client.websocket_connect("/api/v1/hardware/ws") as ws:
            data = ws.receive_json()

            assert "cpu" in data
            assert "ram" in data
            assert "gpus" in data

            assert isinstance(data["cpu"]["percent"], (int, float))
            assert isinstance(data["ram"]["percent"], (int, float))
