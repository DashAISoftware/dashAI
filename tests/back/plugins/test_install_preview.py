"""One download from reviewing to installing, and the plugins a preview plans."""

from pathlib import Path

import pytest
from plugin_helpers import URL, entry, make_plugin, release, save_store

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.disk import previews
from DashAI.back.plugins.plugin_installer import PluginInstallError
from DashAI.back.plugins.store.store import PluginStore


def _kept(env):
    folder = env.storage.root / previews.PREVIEWS_DIR
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def test_installing_a_preview_does_not_fetch_it_again(env):
    env.github.used_asset = env.github.attested = True
    env.github.folder = Path(env.plugin("my-plugin", cls="Mine"))
    preview = env.installer.validate(PluginSource.GIT, URL)
    assert _kept(env) == [preview.preview]

    installed = env.installer.install_preview(preview.preview)

    assert env.github.calls == [URL]  # the preview's download only
    assert "Mine" in env.registry
    source = env.storage.read_source("my-plugin")
    assert (source.location, source.ref, source.trust_level) == (
        URL,
        "v1.0.0-fake-latest",
        "github_attested",
    )
    assert (source.sha256, source.asset, source.workflow) == (
        "f" * 64,
        "plugin.zip",
        ".github/workflows/release.yml",
    )
    assert installed.sha256 == preview.sha256
    assert _kept(env) == []  # used up


def test_a_failed_install_keeps_the_preview_to_retry(env):
    env.github.folder = Path(env.plugin("my-plugin", deps=["a"]))
    token = env.installer.validate(PluginSource.GIT, URL).preview
    env.running = True  # its dependencies must wait

    with pytest.raises(PluginInstallError) as error:
        env.installer.install_preview(token)
    assert error.value.code == "job_running"
    assert _kept(env) == [token]

    env.running = False
    env.installer.install_preview(token)

    assert env.storage.is_installed("my-plugin")
    assert env.github.calls == [URL]  # retried without downloading again
    assert sum("--report" in cmd for cmd in env.pip.calls) == 3


def test_an_update_takes_only_a_preview_of_its_own_origin(env):
    env.install_git()
    env.github.folder = Path(env.plugin("my-plugin", "2.0.0"))
    token = env.installer.validate(
        PluginSource.GIT, "https://github.com/fork/repo"
    ).preview

    with pytest.raises(PluginInstallError) as error:
        env.installer.update("my-plugin", preview=token)

    assert error.value.code == "preview_mismatch"
    assert env.installer._manifest_or_none("my-plugin").version == "1.0.0"
    assert _kept(env) == [token]  # still usable to replace it on purpose


def _store(env, *entries, revoked=(), **reviewed):
    """The store's copy, entries as (id, needs), ``reviewed`` per release."""
    env.installer.store = PluginStore(env.storage)
    plugins = [
        entry(
            i, [{**release("v1.0.0"), "plugin_dependencies": list(needs), **reviewed}]
        )
        for i, needs in entries
    ]
    save_store(env.storage, plugins, revoked=revoked)


@pytest.mark.parametrize(
    ("folder_id", "attested", "reviewed", "code", "params"),
    [
        ("my-plugin", True, {"sha256": "a" * 64}, "digest_mismatch", {}),
        ("other-plugin", True, {}, "store_mismatch", {"field": "id"}),
        (
            "my-plugin",
            True,
            {"version": "2.0.0"},
            "store_mismatch",
            {"field": "version"},
        ),
        ("my-plugin", False, {}, "store_mismatch", {"field": "trust_level"}),
        ("my-plugin", True, {"revoked": True}, "revoked", {}),
    ],
)
def test_a_listed_release_is_the_one_the_store_reviewed(
    env, folder_id, attested, reviewed, code, params
):
    env.github.used_asset, env.github.attested = True, attested
    env.github.folder = Path(env.plugin(folder_id))
    revoked = [{"id": "my-plugin", "sha256": "f" * 64, "date": "2026-11-01"}]
    _store(
        env,
        ("my-plugin", []),
        revoked=revoked if reviewed.pop("revoked", False) else (),
        **{"sha256": "f" * 64, **reviewed},
    )

    with pytest.raises(PluginInstallError) as error:
        env.installer.validate(
            PluginSource.GIT, "https://github.com/acme/my-plugin", "v1.0.0"
        )

    assert error.value.code == code
    assert error.value.params.items() >= params.items()
    assert _kept(env) == []


def _validate(env, plugin_id, *needs):
    folder = env.plugin(plugin_id, plugin_dependencies=list(needs))
    return env.installer.validate(PluginSource.LOCAL, folder)


def test_the_preview_plans_what_it_needs_in_install_order(env):
    env.install("dep-c")
    env.install("dep-b", plugin_dependencies=["dep-c"])
    env.installer.disable("dep-b")
    _store(env, ("dep-s", ["dep-b"]))

    result = _validate(env, "plugin-a", "dep-s")

    assert result.is_valid, result.errors
    assert result.preview
    local = {"location": None, "ref": None}
    assert result.plugin_dependencies == [
        {"id": "dep-c", "name": "dep-c", "state": "active", **local},
        {"id": "dep-b", "name": "dep-b", "state": "disabled", **local},
        {
            "id": "dep-s",
            "name": "Dep-S",
            "state": "store",
            "location": "https://github.com/acme/dep-s",
            "ref": "v1.0.0",
            "latest": None,
        },
    ]


def test_the_store_offers_the_newest_release_this_dashai_runs(env):
    env.installer.store = PluginStore(env.storage)
    newer = release("v2.0.0", app="99.0.0")
    ranged = [release("v3.0.0"), release("v2.0.0"), release("v1.0.0")]
    save_store(
        env.storage,
        [
            entry("dep-old", [newer, release("v1.0.0")]),
            entry("dep-new", [newer]),
            entry("dep-ranged", ranged),
        ],
    )
    env.install("dep-c")

    result = _validate(
        env, "plugin-a", "dep-old", "dep-new", "dep-ranged<3", "dep-c>=2", "dep-x>9"
    )

    assert [
        (d["id"], d["ref"], d["latest"]) for d in result.plugin_dependencies if d["ref"]
    ] == [
        ("dep-old", "v1.0.0", "v2.0.0"),
        ("dep-ranged", "v2.0.0", None),
    ]
    assert [(e.code, e.params) for e in result.errors] == [
        ("incompatible_plugin_dependency", {"id": "dep-new"}),
        ("missing_plugin_dependency", {"id": "dep-x", "store_read": True}),
        (
            "plugin_dependency_version",
            {"id": "dep-c", "required": ">=2", "installed": "1.0.0"},
        ),
    ]


def test_the_preview_names_the_installed_plugins_a_new_version_breaks(env):
    env.install("plugin-a")
    env.install("dep-u", plugin_dependencies=["plugin-a<2"])

    folder = env.plugin("plugin-a", version="2.0.0")
    result = env.installer.validate(PluginSource.LOCAL, folder)

    assert result.is_valid, result.errors
    assert result.breaks == ["dep-u"]


def test_a_cycle_through_what_is_installed_and_the_store_is_refused(env):
    make_plugin(env.storage.plugin_dir("cy-x"), "cy-x", plugin_dependencies=["cy-s"])
    _store(env, ("cy-s", ["cy-x"]))

    result = _validate(env, "plugin-a", "cy-x")

    assert not result.is_valid
    assert [(e.code, e.params) for e in result.errors] == [
        ("dependency_cycle", {"ids": ["cy-s", "cy-x"]})  # not plugin-a, behind it
    ]
