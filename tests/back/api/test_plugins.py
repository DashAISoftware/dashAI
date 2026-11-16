"""The plugin endpoints against a stubbed installer where installing runs code."""

import json
import shutil
from pathlib import Path

import pytest

from tests.back.plugins.plugin_helpers import manifest, plugin_zip


@pytest.fixture
def plugins_dir(client) -> Path:
    """Storage dir the app reads, emptied before and after each test."""
    base = Path(client.app.container["plugin_storage"].base_path)

    def _empty():
        if base.is_dir():
            for child in base.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)

    base.mkdir(parents=True, exist_ok=True)
    _empty()
    yield base
    _empty()


def _drop_plugin(base: Path, plugin_id: str, manifest_text: str | None = None) -> Path:
    plugin_dir = base / plugin_id
    plugin_dir.mkdir(parents=True, exist_ok=True)
    if manifest_text is None:
        fields = {"name": "Demo Plugin", "version": "1.2.3"}
        manifest_text = json.dumps(manifest(plugin_id, "DemoConverter", **fields))
    (plugin_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
    return plugin_dir


def test_list_installed_lists_dropped_plugin(client, plugins_dir):
    _drop_plugin(plugins_dir, "demo-plugin")

    response = client.get("/api/v1/plugin/installed")

    assert response.status_code == 200
    by_id = {entry["id"]: entry for entry in response.json()}
    assert "demo-plugin" in by_id
    entry = by_id["demo-plugin"]
    assert set(entry) == set(
        "id name version components component_types description"  # noqa: SIM905
        " has_settings enabled active source location ref trust_level trust_tier"
        " verified sha256 commit asset workflow signed_at issuer dependencies"
        " plugin_dependencies plugin_specifiers authors project_urls problem removed"
        " installed_at updated_at can_update web_url owner readme_base"
        " readme_links".split()
    )
    assert entry["name"] == "Demo Plugin"
    assert entry["version"] == "1.2.3"
    assert entry["components"] == ["DemoConverter"]
    assert entry["component_types"] == ["Converter"]
    assert entry["enabled"] is True
    assert entry["active"] is False
    assert entry["source"] is None


def test_a_plugin_readme_is_read_on_its_own(client, plugins_dir):
    folder = _drop_plugin(plugins_dir, "demo-plugin")
    assert client.get("/api/v1/plugin/demo-plugin/readme").json() is None
    (folder / "README.md").write_text("# Demo", encoding="utf-8")

    assert client.get("/api/v1/plugin/demo-plugin/readme").json() == "# Demo"
    assert client.get("/api/v1/plugin/missing/readme").status_code == 404


def test_a_damaged_plugin_keeps_its_origin_so_it_can_be_reinstalled(
    client, plugins_dir
):
    folder = _drop_plugin(plugins_dir, "bad-git", manifest_text="{ not valid json")
    (folder / ".source").write_text(
        json.dumps(
            {
                "source": "git",
                "location": "https://github.com/owner/repo",
                "ref": "v1.0.0",
                "trust_level": "github_attested",
            }
        ),
        encoding="utf-8",
    )

    entries = {e["id"]: e for e in client.get("/api/v1/plugin/installed").json()}

    entry = entries["bad-git"]
    assert entry["problem"]["code"] == "damaged"
    assert (entry["source"], entry["location"], entry["ref"]) == (
        "git",
        "https://github.com/owner/repo",
        "v1.0.0",
    )
    assert entry["trust_level"] == "github_attested"


def test_a_github_plugin_reads_its_readme_files_at_its_commit(client, plugins_dir):
    folder = _drop_plugin(plugins_dir, "demo-plugin")
    origin = {"source": "git", "location": "https://github.com/acme/kit"}
    raw = "https://raw.githubusercontent.com/acme/kit/"
    for marker, base in (
        ({"ref": "v1.0.0", "commit": "c1"}, f"{raw}c1/"),
        ({"ref": "v1.0.0"}, f"{raw}v1.0.0/"),
    ):
        (folder / ".source").write_text(json.dumps({**origin, **marker}), "utf-8")
        entry = client.get("/api/v1/plugin/installed").json()[0]

        assert entry["readme_base"] == base
        assert entry["readme_links"] == base.replace(
            raw, "https://github.com/acme/kit/blob/"
        )


def test_upload_over_the_size_limit_is_413(client, monkeypatch):
    monkeypatch.setattr("DashAI.back.api.api_v1.endpoints.plugins.MAX_PLUGIN_BYTES", 10)

    response = client.post(
        "/api/v1/plugin/upload/validate", files={"file": ("p.zip", plugin_zip())}
    )

    assert response.status_code == 413


@pytest.mark.parametrize(
    "location",
    ["https://gitlab.com/acme/kit", "plugin.zip", "not a url", "", "github.com/acme"],
)
def test_validate_a_location_no_source_takes_is_400(client, location):
    response = client.post("/api/v1/plugin/validate", json={"location": location})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_location"


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/api/v1/plugin/installed", "get"),
        ("/api/v1/plugin/upload/validate", "post"),
        ("/api/v1/plugin/store", "get"),
    ],
)
def test_another_site_cannot_use_the_plugin_api(client, path, method):
    response = getattr(client, method)(path, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden_origin"


@pytest.mark.parametrize(
    ("origin", "host"),
    [
        ("http://localhost:3000", "localhost:8000"),  # front's dev server
        ("http://localhost:8000", "localhost:8000"),  # the app and PyWebView
        ("http://127.0.0.1:8000", "127.0.0.1:8000"),
        ("http://192.168.1.5:8000", "192.168.1.5:8000"),  # opened by IP on a LAN
    ],
)
def test_dashai_own_pages_can_use_the_plugin_api(client, plugins_dir, origin, host):
    response = client.get(
        "/api/v1/plugin/installed", headers={"Origin": origin, "Host": host}
    )

    assert response.status_code == 200


def test_a_rebound_name_on_this_machine_is_not_dashai(client):
    # DNS rebinding, evil.example resolves to this machine, so Host matches.
    response = client.get(
        "/api/v1/plugin/installed",
        headers={"Origin": "http://evil.example:8000", "Host": "evil.example:8000"},
    )

    assert response.status_code == 403


def test_an_uploaded_zip_installs_from_its_preview_without_uploading_it_again(
    client, plugins_dir
):
    root = client.app.container["plugin_storage"].root
    payload = plugin_zip("upload-plugin")
    preview = client.post(
        "/api/v1/plugin/upload/validate",
        files={"file": ("my-plugin.zip", payload, "application/zip")},
    ).json()
    token = preview["preview"]
    assert (root / ".previews" / token).is_dir()
    try:
        installed = client.post("/api/v1/plugin/", json={"preview": token})
        assert installed.status_code == 201, installed.text
        assert installed.json()["version"] == "1.0.0"
        marker = json.loads((plugins_dir / "upload-plugin" / ".source").read_text())
        assert marker["location"] == "my-plugin.zip"  # its name, not a temp file
        assert marker["sha256"] == preview["sha256"]
        assert not (root / ".previews" / token).exists()

        again = client.post("/api/v1/plugin/", json={"preview": token})
        assert again.status_code == 400
        assert again.json()["detail"]["code"] == "preview_expired"
    finally:
        client.delete("/api/v1/plugin/upload-plugin")


def test_without_a_store_the_catalog_is_empty_and_says_why(client):
    container = client.app.container
    store = container["plugin_store"]
    container["plugin_store"] = None
    try:
        response = client.get("/api/v1/plugin/store")
    finally:
        container["plugin_store"] = store
    assert response.status_code == 200
    assert response.json() == {
        "checking": False,
        "checked_at": None,
        "error": "disabled",
        "built_at": None,
        "wrong_versions": {},
        "plugins": [],
    }
