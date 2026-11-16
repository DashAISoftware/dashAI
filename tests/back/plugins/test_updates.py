"""Looking up newer releases of the installed plugins (``updates.py``)."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from plugin_helpers import FakeGitHub, fake_installed

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.disk.trash import write_json
from DashAI.back.plugins.sources.base import RateLimitError
from DashAI.back.plugins.sources.github_source import GitHubRateLimitError
from DashAI.back.plugins.store.updates import UPDATES_FILE, PluginUpdates

REPO = "https://github.com/acme/{}"


def _checked(storage, hours_ago):
    """Pretend the last full lookup was ``hours_ago``."""
    path = storage.root / UPDATES_FILE
    data = json.loads(path.read_text("utf-8"))
    when = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    data["checked_at"] = when.isoformat()
    write_json(path, data)  # as dashAI does, open("w") fails on it hidden


def test_a_newer_release_is_an_update_and_local_plugins_are_not_asked(storage):
    fake_installed(storage, "old")
    fake_installed(storage, "current", ref="v2.0.0")
    fake_installed(storage, "uploaded", source="local")
    github = FakeGitHub(
        tags={REPO.format("old"): "v1.1.0", REPO.format("current"): "v2.0.0"}
    )

    status = PluginUpdates(storage, {PluginSource.GIT: github}).check()

    assert status["updates"] == {"old": "v1.1.0"}
    assert status["errors"] == {}
    assert not status["checking"]
    assert {url for url, _ in github.calls} == {
        REPO.format("old"),
        REPO.format("current"),
    }


def test_looks_again_only_after_12_hours(storage):
    fake_installed(storage, "p")
    github = FakeGitHub(tags={REPO.format("p"): "v1.1.0"})
    updates = PluginUpdates(storage, {PluginSource.GIT: github})
    updates.check()

    _checked(storage, hours_ago=11)
    updates.check()
    assert len(github.calls) == 1

    _checked(storage, hours_ago=13)
    updates.check()
    assert len(github.calls) == 2
    assert github.calls[1] == (REPO.format("p"), "v1.1.0")  # with its ETag


def test_rate_limited_stops_the_lookup_and_the_next_opening_tries_again(storage):
    for plugin_id in ("a", "b", "c", "d", "e", "f", "g", "h"):
        fake_installed(storage, plugin_id)
    github = FakeGitHub(
        tags={REPO.format(p): GitHubRateLimitError("limit") for p in "abcdefgh"}
    )
    updates = PluginUpdates(storage, {PluginSource.GIT: github})

    with pytest.raises(RateLimitError):
        updates.check()

    assert len(github.calls) < 8  # the rest were not sent
    assert updates.status()["checked_at"] is None  # due again at the next opening
