"""PluginInstaller install, update, toggle, trust, retired and needed plugins."""

import sys
from pathlib import Path

import pytest
from plugin_helpers import URL, module, save_store

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.plugins.loader import PluginLoader
from DashAI.back.plugins.plugin_installer import InstalledPlugin, PluginInstallError
from DashAI.back.plugins.store.store import PluginStore

USER = "from dashai_plugins.pdep_base.mod import Base\n\nclass User(Base):\n    pass\n"


def _release(env, plugin_id="my-plugin", version="2.0.0", **kwargs):
    """The release GitHub serves from now on."""
    env.github.folder = Path(env.plugin(plugin_id, version, **kwargs))


def _break_manifest(env, plugin_id="my-plugin"):
    manifest = env.storage.plugin_dir(plugin_id) / "manifest.json"
    manifest.write_text("{not json", encoding="utf-8")


def _retire(env, *removed):
    """The store's copy, as if just read, retiring ``removed``."""
    env.installer.store = env.installer.store or PluginStore(env.storage)
    save_store(env.storage, removed=removed)
    return env.installer.apply_removed()


@pytest.mark.parametrize(
    ("source", "used_asset", "level"),
    [
        (PluginSource.LOCAL, False, "local"),
        (PluginSource.GIT, True, "github_asset"),
        (PluginSource.GIT, False, "github_source"),  # the repo's code at its commit
    ],
)
def test_install_stores_registers_and_records_its_trust_level(
    env, source, used_asset, level
):
    folder = env.plugin("my-plugin", cls="Mine")
    env.github.folder, env.github.used_asset = Path(folder), used_asset

    installed = env.installer.install(
        source, folder if source is PluginSource.LOCAL else URL
    )

    assert isinstance(installed, InstalledPlugin)
    assert (installed.id, installed.trust_level) == ("my-plugin", level)
    assert [component.__name__ for component in installed.components] == ["Mine"]
    assert "Mine" in env.registry
    assert env.storage.read_source("my-plugin").trust_level == level


def test_a_reinstall_replaces_the_previous_version_and_drops_its_components(env):
    both = [{"class": f"mod:{c}", "type": "Converter"} for c in ("CompA", "CompB")]
    code = module("CompA") + "class CompB(Base):\n    pass\n"
    env.install("multi", module=code, components=both)

    result = env.install("multi", "2.0.0", cls="CompA")

    assert result.version == "2.0.0"
    assert "CompA" in env.registry  # replaced in place by the v2 class
    assert "CompB" not in env.registry  # dropped, not left as an orphan


def test_a_reinstall_with_a_broken_manifest_keeps_the_previous_version(env):
    env.install("my-plugin", cls="Mine")
    broken = env.tmp / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("{ not valid json", encoding="utf-8")

    with pytest.raises(PluginInstallError, match="Invalid manifest"):
        env.installer.install(PluginSource.LOCAL, str(broken))

    assert env.storage.is_installed("my-plugin")
    assert "Mine" in env.registry


@pytest.mark.parametrize("latest", ["1.0.0", "0.9.0"])
def test_update_never_reinstalls_nor_downgrades(env, latest):
    env.install_git()
    _release(env, version=latest)

    with pytest.raises(PluginInstallError, match="No newer version"):
        env.update()

    assert env.installer._manifest_or_none("my-plugin").version == "1.0.0"


def test_update_installs_the_reviewed_copy_even_if_the_release_changed(env):
    env.install_git()
    _release(env, cls="V2")
    preview = env.installer.validate(PluginSource.GIT, URL)
    _release(env, version="3.0.0")  # the author replaces the release after the review

    env.installer.update("my-plugin", preview=preview.preview)

    assert env.installer._manifest_or_none("my-plugin").version == "2.0.0"
    assert "V2" in env.registry


def test_validate_asks_to_acknowledge_going_down_a_tier(env):
    env.github.used_asset = env.github.attested = True
    env.install_git()
    env.github.used_asset = env.github.attested = False  # source code only

    result = env.installer.validate(PluginSource.GIT, URL)

    assert result.trust_level == "github_source"
    assert result.needs_ack  # github_source alone would not ask


def test_install_of_another_plugin_works_with_a_broken_manifest_on_disk(env):
    env.install("my-plugin")
    _break_manifest(env)

    env.install("other-plugin", cls="Other")

    assert env.storage.is_installed("other-plugin")
    assert "Other" in env.registry


def test_reinstall_over_a_manifest_broken_while_loaded(env):
    source = env.plugin("my-plugin")
    env.installer.install(PluginSource.LOCAL, source)
    _break_manifest(env)

    assert env.installer.validate(PluginSource.LOCAL, source).is_valid
    env.installer.install(PluginSource.LOCAL, source)
    assert env.installer._manifest_or_none("my-plugin").version == "1.0.0"


@pytest.mark.parametrize(
    ("operation", "args"),
    [("enable", ()), ("disable", ()), ("uninstall", ()), ("update", ("token",))],
)
def test_an_operation_on_a_plugin_not_installed_is_refused(env, operation, args):
    with pytest.raises(PluginInstallError) as refused:
        getattr(env.installer, operation)("nowhere", *args)

    assert (refused.value.code, refused.value.params) == (
        "not_installed",
        {"id": "nowhere"},
    )


def test_disable_unregisters_keeping_the_files_and_enable_registers_again(env):
    env.install("my-plugin", cls="Mine")

    env.installer.disable("my-plugin")
    assert "Mine" not in env.registry
    assert env.storage.is_installed("my-plugin")
    assert env.storage.is_enabled("my-plugin") is False

    env.installer.enable("my-plugin")
    assert "Mine" in env.registry
    assert env.storage.is_enabled("my-plugin") is True


def test_enable_loads_a_plugin_that_is_enabled_but_not_loaded(env):
    env.install("my-plugin", cls="Mine")
    PluginLoader.unload(env.installer._manifest_or_none("my-plugin"), env.registry)

    env.installer.enable("my-plugin")

    assert "Mine" in env.registry


CRITICAL = {"id": "my-plugin", "repo": "Owner/Repo", "type": "critical"}


@pytest.fixture
def retired(env):
    """my-plugin installed from GitHub, then retired by the store as malicious."""
    env.install_git(cls="Mine")
    assert _retire(env, {**CRITICAL, "date": "d1"})  # it blocked one
    return env


def test_a_plugin_the_store_retires_as_malicious_is_blocked(retired):
    assert "Mine" not in retired.registry
    assert retired.installer.validate(PluginSource.GIT, URL).removed == "critical"
    with pytest.raises(PluginInstallError) as refused:
        retired.installer.enable("my-plugin")
    assert refused.value.code == "blocked"


def test_a_new_retirement_blocks_it_again_and_installing_runs_no_code(retired):
    retired.installer.enable("my-plugin", allow_blocked=True)  # the user confirmed
    assert not retired.installer.apply_removed()  # the same entry, still allowed
    assert "Mine" in retired.registry

    _retire(retired, {**CRITICAL, "date": "d2"})
    assert "Mine" not in retired.registry
    retired.installer.install(PluginSource.GIT, URL)

    assert retired.storage.is_blocked("my-plugin")
    assert "Mine" not in retired.registry


def test_a_plugin_out_of_the_retired_list_comes_back_by_itself(retired):
    assert _retire(retired)

    assert not retired.storage.is_blocked("my-plugin")
    assert "Mine" in retired.registry


def _user(env, version="1.0.0", needs=("dep-base",)):
    return env.install(
        "dep-user", version, module=USER, cls="User", plugin_dependencies=list(needs)
    )


@pytest.fixture
def base_and_user(env):
    """dep-base from GitHub (the store can retire it), dep-user from a folder."""
    env.install_git("dep-base")
    _user(env)
    assert "dep-user:User" in env.registry
    return env


@pytest.mark.parametrize("operation", ["disable", "uninstall", "block"])
def test_a_plugin_stops_with_the_one_it_needs_and_keeps_its_choice(
    base_and_user, operation
):
    env = base_and_user

    if operation == "block":
        retired = {"id": "dep-base", "repo": "owner/repo", "type": "critical"}
        _retire(env, {**retired, "date": "d1"})
    else:
        getattr(env.installer, operation)("dep-base")

    assert "dep-user:User" not in env.registry
    assert env.storage.is_enabled("dep-user")  # its .disabled is the user's alone


def test_updating_the_base_reloads_its_dependent_against_the_new_class(base_and_user):
    env = base_and_user
    _release(env, "dep-base", module=module("C_dep_base") + "V = 2\n")

    env.update("dep-base")

    new_base = sys.modules["dashai_plugins.pdep_base.mod"].Base
    assert issubclass(env.registry["dep-user:User"]["class"], new_base)


def test_installing_a_plugin_whose_dependency_is_off_changes_nothing(env):
    env.install("dep-base")
    env.installer.disable("dep-base")

    with pytest.raises(PluginInstallError) as refused:
        _user(env)

    assert refused.value.code == "dependency_unavailable"
    assert refused.value.params == {"id": "dep-base"}
    assert env.storage.list_installed() == ["dep-base"]


def test_an_update_needing_a_plugin_not_installed_changes_nothing(
    base_and_user, monkeypatch
):
    env = base_and_user
    env.installer.disable("dep-user")
    checked = []
    monkeypatch.setattr(env.installer, "_load_check", checked.append)

    with pytest.raises(PluginInstallError) as refused:
        _user(env, "2.0.0", needs=("dep-base", "dep-new"))

    assert refused.value.code == "missing_plugin_dependency"
    assert refused.value.params == {"id": "dep-new"}
    assert env.installer._manifest_or_none("dep-user").version == "1.0.0"
    assert checked == []


def test_a_base_pending_restart_unloads_its_dependent(base_and_user, monkeypatch):
    env = base_and_user
    monkeypatch.setattr(env.installer, "_uses_stale", lambda m: m.id == "dep-base")
    monkeypatch.setattr(env.installer, "_load_check", lambda plugin_dir: None)
    _release(env, "dep-base")

    env.update("dep-base")

    assert env.installer.pending_restart == {"dep-base"}
    assert "dep-user:User" not in env.registry
