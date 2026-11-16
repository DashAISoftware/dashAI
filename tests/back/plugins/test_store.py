"""The plugin store's copy of its index (``store.py``) and how updates use it."""

import hashlib
import json

import httpx
import pytest
from plugin_helpers import (
    COMMIT,
    SHA,
    FakeGitHub,
    entry,
    fake_installed,
    make_plugin,
    release,
)

from DashAI.back.api.api_v1.schemas.plugin_params import StoreResponse
from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.store.store import (
    _MAX_INDEX_BYTES,
    INDEX_FILE,
    INDEX_URL_VARIABLE,
    INVALID_STORE,
    OFFLINE,
    RATE_LIMITED,
    STORE_FILE,
    UNVERIFIED_STORE,
    PluginStore,
    StoreIndex,
    index_url,
    removed_entry,
)
from DashAI.back.plugins.store.updates import PluginUpdates

URL = "https://raw.example/index.json"


def index(*entries):
    return {
        "schema": 1,
        "built_at": "2026-10-13T06:17:00+00:00",
        "plugins": list(entries),
    }


class FakeServer:
    """Answers each request with the next of ``answers`` and records them."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def ok(body, etag='"e1"'):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return httpx.Response(200, content=raw, headers={"etag": etag})


def signed(body):
    """The index and its bundle (the fake one ``fake_verify`` reads)."""
    raw = json.dumps(body).encode()
    return ok(raw), httpx.Response(200, json={"signs": hashlib.sha256(raw).hexdigest()})


def fake_verify(bundle, *signer):
    fake_verify.signer = signer
    return json.dumps({"subject": [{"digest": {"sha256": bundle["signs"]}}]}).encode()


def make_store(storage, *answers, url=URL):
    server = FakeServer(*answers)
    client = httpx.Client(transport=httpx.MockTransport(server))
    return PluginStore(storage, url=url, client=client, verify=fake_verify), server


def saved(storage):
    return json.loads((storage.root / STORE_FILE).read_text("utf-8"))


def test_a_new_index_is_kept_with_its_etag(storage):
    store, _ = make_store(storage, ok({**index(entry("echo")), "newer_bot": 1}))
    assert store.read() is None  # no copy yet

    assert store.refresh() is None
    assert [e.id for e in store.read().plugins] == ["echo"]
    data = saved(storage)
    kept = json.loads((storage.root / INDEX_FILE).read_text("utf-8"))
    assert kept["newer_bot"] == 1  # kept as written, a newer dashAI reads it
    assert "index" not in data  # each check rewrites only these few fields
    assert data["etag"] == '"e1"'
    assert data["checked_at"]
    assert data["error"] is None


def test_an_unchanged_index_is_not_rewritten_and_a_lost_one_is_fetched(storage):
    answers = ok(index(entry("echo"))), httpx.Response(304), ok(index(entry("echo")))
    store, server = make_store(storage, *answers)
    store.refresh()
    written = (storage.root / INDEX_FILE).stat().st_mtime_ns

    assert store.refresh() is None
    assert server.requests[1].headers["if-none-match"] == '"e1"'
    assert (storage.root / INDEX_FILE).stat().st_mtime_ns == written
    (storage.root / INDEX_FILE).unlink()
    assert store.refresh() is None
    assert "if-none-match" not in server.requests[2].headers  # no copy to keep
    assert [e.id for e in store.read().plugins] == ["echo"]


@pytest.mark.parametrize(
    ("answer", "code"),
    [
        (httpx.ConnectError("no network"), OFFLINE),
        (httpx.Response(429), RATE_LIMITED),
        (ok(b"not json"), INVALID_STORE),
        (ok({"schema": 2, "built_at": "x", "plugins": []}), INVALID_STORE),
        (ok(b" " * (_MAX_INDEX_BYTES + 1)), INVALID_STORE),
    ],
)
def test_a_failed_reading_keeps_the_copy_and_says_why(storage, answer, code):
    store, _ = make_store(storage, ok(index(entry("echo"))), answer)
    store.refresh()
    before = saved(storage)

    assert store.refresh() == code
    after = saved(storage)
    assert [e.id for e in store.read().plugins] == ["echo"]
    assert after["checked_at"] == before["checked_at"]  # not fresh
    assert after["etag"] == before["etag"]
    assert after["error"] == code
    assert store.status() == {"checked_at": before["checked_at"], "error": code}


@pytest.mark.parametrize(
    "bundle",
    [
        httpx.Response(404),
        httpx.Response(200, json={}),  # not the bot's signature
        httpx.Response(200, json={"signs": SHA}),  # of other bytes
    ],
)
def test_a_github_index_counts_only_signed_by_its_build_workflow(storage, bundle):
    url = "https://raw.githubusercontent.com/acme/plugins/main/index.json"
    store, server = make_store(
        storage,
        *signed(index(entry("echo"))),
        ok(index(entry("other")), etag='"e2"'),
        bundle,
        httpx.Response(304),
        url=url,
    )
    assert store.refresh() is None
    assert server.requests[1].url == url + ".sigstore.json"
    assert fake_verify.signer == (
        "https://github.com/acme/plugins",
        "refs/heads/main",
        "https://github.com/acme/plugins/.github/workflows/build.yml@refs/heads/main",
    )

    assert store.refresh() == UNVERIFIED_STORE
    assert [e.id for e in store.read().plugins] == ["echo"]
    assert saved(storage)["etag"] == '"e1"'  # asked for again in full
    assert store.refresh() is None  # a 304, no signature asked for
    assert len(server.requests) == 5


@pytest.mark.parametrize(("value", "url"), [(None, None), ("", None), (URL, URL)])
def test_without_an_index_url_there_is_no_store(monkeypatch, value, url):
    monkeypatch.delenv(INDEX_URL_VARIABLE, raising=False)
    if value is not None:
        monkeypatch.setenv(INDEX_URL_VARIABLE, value)
    assert index_url() == url


def test_an_index_older_than_the_copy_of_its_url_is_refused(storage):
    older = {**index(entry("other")), "built_at": "2026-10-12T00:00:00+00:00"}
    store, _ = make_store(storage, ok(index(entry("echo"))), ok(older))
    store.refresh()

    assert store.refresh() == INVALID_STORE
    assert [e.id for e in store.read().plugins] == ["echo"]
    other, server = make_store(storage, ok(older), url="https://raw.example/b.json")
    assert other.refresh() is None
    assert "if-none-match" not in server.requests[0].headers
    assert [e.id for e in other.read().plugins] == ["other"]


def test_a_bad_entry_is_left_out_and_the_rest_kept():
    parsed = StoreIndex.model_validate(
        index(
            entry("good"),
            entry("not-github", location="https://gitlab.com/acme/x"),
            entry("bad-link", project_urls={"Home": "javascript:alert(1)"}),
            entry("bad-author", authors=[{"name": "x", "url": "file:///etc"}]),
            entry("no-commit", releases=[{**release("v1"), "commit": "abc"}]),
            entry("no-releases", releases=[]),
            {"id": "Not_An_Id", "source": "git"},
            entry("good", repo="other/good"),  # a repeated id, the first wins
        )
    )
    assert [e.id for e in parsed.plugins] == ["good"]
    assert parsed.plugins[0].location == "https://github.com/acme/good"


def test_a_retired_plugin_matches_by_id_and_repo():
    parsed = StoreIndex.model_validate(
        {
            **index(),
            "removed": [
                {"id": "echo", "repo": "Acme/echo", "type": "critical", "date": "d"},
                {"id": "echo", "repo": "acme/echo", "type": "banned", "date": "d"},
            ],
        }
    )
    assert len(parsed.removed) == 1  # an unknown type is left out
    assert removed_entry(parsed, "echo", "git", "https://github.com/acme/echo.git")
    assert not removed_entry(parsed, "echo", "git", "https://github.com/fork/echo")
    assert not removed_entry(parsed, "echo", "local", "echo.zip")


@pytest.mark.parametrize(
    "bad",
    [
        {"source": "local", "location": "echo.zip"},  # can't be installed from it
        {"source": "gitlab", "location": "https://gitlab.com/acme/echo"},
        {"source": "git", "location": "https://gitlab.com/acme/echo"},
    ],
)
def test_an_entry_of_a_source_that_cant_install_it_is_left_out(bad):
    parsed = StoreIndex.model_validate(index(entry("echo") | bad, entry("kit")))
    assert [e.id for e in parsed.plugins] == ["kit"]


def test_the_catalog_is_what_the_response_model_serves(storage):
    store, _ = make_store(
        storage,
        ok(
            index(
                entry("echo"),
                entry("kit", repo="DashAISoftware/kit"),
                entry("geo"),
                entry("new", releases=[release("v1", app="999.0.0")]),
                entry(
                    "plot",
                    releases=[release("v1.0.0") | {"plugin_dependencies": ["echo>=2"]}],
                ),
                entry(
                    "map",
                    releases=[
                        release("v1.0.0")
                        | {"plugin_dependencies": ["plot>=2", "echo>=1"]}
                    ],
                ),
            )
        ),
    )
    store.refresh()
    fake_installed(storage, "echo", "https://github.com/Acme/echo")  # same repo
    make_plugin(storage.plugin_dir("echo"), "echo")
    fake_installed(storage, "geo", source="local")  # a .zip with the store's id
    fake_installed(storage, "kit", "https://github.com/fork/kit")  # another repo
    served = json.loads(store.catalog())

    assert StoreResponse.model_validate(served).model_dump(mode="json") == served
    assert served["built_at"] == "2026-10-13T06:17:00+00:00"
    catalog = {p["id"]: p for p in served["plugins"]}
    fields = ("installed", "installed_other", "offered", "official")
    assert {i: tuple(p[f] for f in fields) for i, p in catalog.items()} == {
        "echo": (True, False, "v1.0.0", False),
        "geo": (False, True, "v1.0.0", False),
        "kit": (False, True, "v1.0.0", True),
        "new": (False, False, None, False),  # every release needs a newer dashAI
        "plot": (False, False, "v1.0.0", False),
        "map": (False, False, "v1.0.0", False),
    }
    assert served["wrong_versions"] == {"plot": ["echo"], "map": ["plot"]}
    echo = catalog["echo"]  # the front reads no location
    assert (echo["owner"], echo["web_url"]) == ("acme", "https://github.com/acme/echo")
    assert echo["readme_base"] == (
        f"https://raw.githubusercontent.com/acme/echo/{COMMIT}/"
    )
    assert echo["readme_links"] == f"https://github.com/acme/echo/blob/{COMMIT}/"


def updates_with(storage, *answers):
    store, server = make_store(storage, *answers)
    github = FakeGitHub(tags={"https://github.com/acme/outside": "v9.0.0"})
    return PluginUpdates(storage, {PluginSource.GIT: github}, store), github, server


def test_a_store_plugin_updates_from_the_index_without_asking_github(storage):
    fake_installed(storage, "echo", ref="v1.0.0")
    # installed by URL, not in the store
    fake_installed(storage, "outside", ref="v1.0.0")
    updates, github, _ = updates_with(
        storage,
        ok(index(entry("echo", releases=[release("v2.0.0"), release("v1.0.0")]))),
    )
    status = updates.check()
    assert github.calls == [("https://github.com/acme/outside", None)]
    assert status["updates"] == {"echo": "v2.0.0", "outside": "v9.0.0"}
    assert status["needs_newer_dashai"] == {}
    assert status["store_error"] is None


def test_lookups_that_blocked_or_unblocked_a_plugin_are_counted(storage):
    updates, _, _ = updates_with(storage, ok(index()), ok(index()), ok(index()))
    assert updates.check()["blocked_changes"] == 0
    updates.apply_removed = lambda: True  # PluginInstaller's, it blocked one
    assert updates.check()["blocked_changes"] == 1
    updates.apply_removed = lambda: False
    assert updates.check()["blocked_changes"] == 1  # kept for a window yet to read


def test_a_newer_release_that_needs_a_newer_dashai_is_not_an_update(storage):
    fake_installed(storage, "echo", ref="v1.0.0")
    fake_installed(storage, "kit", ref="v1.0.0")
    updates, _, _ = updates_with(
        storage,
        ok(
            index(
                entry(
                    "echo",
                    releases=[
                        release("v3.0.0", app="999.0.0"),
                        release("v2.0.0"),
                        release("v1.0.0"),
                    ],
                ),
                entry("kit", releases=[release("v2.0.0", app="999.0.0")]),
            )
        ),
    )
    status = updates.check()
    assert status["updates"] == {"echo": "v2.0.0"}
    assert status["needs_newer_dashai"] == {"echo": "v3.0.0", "kit": "v2.0.0"}
