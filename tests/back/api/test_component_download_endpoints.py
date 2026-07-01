"""Tests for the component download/delete/status endpoints."""


def test_get_download_status_nondownloadable(client):
    # Any component that does NOT require download should return the status dict.
    models = client.get("/api/v1/component/", params={"select_types": ["Model"]}).json()
    non_downloadable = [m for m in models if not m["metadata"]["requires_download"]]
    if not non_downloadable:
        return  # skip if all models require download (unlikely)
    name = non_downloadable[0]["name"]
    resp = client.get(f"/api/v1/component/{name}/download")
    assert resp.status_code == 200
    body = resp.json()
    assert "downloaded" in body
    assert "requires_download" in body
    assert body["requires_download"] is False


def test_get_download_status(client):
    # Pick any downloadable Model from the list.
    models = client.get("/api/v1/component/", params={"select_types": ["Model"]}).json()
    downloadable = [m for m in models if m["metadata"]["requires_download"]]
    if not downloadable:
        return  # no downloadable component registered in this environment
    name = downloadable[0]["name"]
    resp = client.get(f"/api/v1/component/{name}/download")
    assert resp.status_code == 200
    assert "downloaded" in resp.json()


def test_get_download_status_unknown_404(client):
    resp = client.get("/api/v1/component/NopeComponent/download")
    assert resp.status_code == 404


def test_download_nonexistent_component_404(client):
    resp = client.post("/api/v1/component/NopeComponent/download")
    assert resp.status_code == 404


def test_post_download_non_downloadable_409(client):
    # A component that does not require download should yield 409.
    models = client.get("/api/v1/component/", params={"select_types": ["Model"]}).json()
    non_downloadable = [m for m in models if not m["metadata"]["requires_download"]]
    if not non_downloadable:
        return
    name = non_downloadable[0]["name"]
    resp = client.post(f"/api/v1/component/{name}/download")
    assert resp.status_code == 409


def test_delete_download_unknown_404(client):
    resp = client.delete("/api/v1/component/NopeComponent/download")
    assert resp.status_code == 404
