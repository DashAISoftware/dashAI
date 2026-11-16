import os
import sys

import pytest
from plugin_helpers import make_plugin, manifest, module

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins import bootstrap, load_check
from DashAI.back.plugins.bootstrap import sync_installed_plugins
from DashAI.back.plugins.disk.storage import Blocked
from DashAI.back.plugins.manifest.manifest import PluginManifest


def _installed(storage, plugin_id, cls="C", code=None, needs=()):
    """A plugin folder as if it were installed; ``needs``: its plugin_dependencies."""
    folder = storage.base_path / plugin_id
    return make_plugin(folder, plugin_id, cls, code, plugin_dependencies=list(needs))


def _touch_later(path):
    """Bump a file's mtime, as reinstalling it does (without sleeping)."""
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))


@pytest.mark.parametrize(
    ("fields", "error"),
    [
        ({"components": [{"class": "mod:Missing", "type": "Converter"}]}, "Missing"),
        ({"min_app_version": "99.0.0"}, "99.0.0"),
    ],
)
def test_a_plugin_that_cannot_load_is_skipped_and_the_others_load(
    storage, fields, error
):
    _installed(storage, "boot-ok", "OkConv")
    make_plugin(storage.base_path / "boot-bad", "boot-bad", **fields)
    registry = ComponentRegistry(initial_components=[])

    assert sync_installed_plugins(storage, registry) == ["boot-ok"]
    assert "OkConv" in registry
    assert error in bootstrap.load_errors["boot-bad"]


@pytest.fixture
def worker(storage):
    _installed(storage, "sync-a", "ConvA")
    registry = ComponentRegistry(initial_components=[])
    sync_installed_plugins(storage, registry)  # what the worker saw at startup
    return registry


def test_sync_loads_a_plugin_installed_after_startup(storage, worker):
    _installed(storage, "sync-b", "ConvB")

    assert sync_installed_plugins(storage, worker) == ["sync-b"]
    assert "ConvB" in worker


def test_sync_unloads_a_plugin_the_store_blocked(storage, worker):
    storage.set_blocked("sync-a", Blocked("2026-10-19"))

    assert sync_installed_plugins(storage, worker) == ["sync-a"]
    assert "ConvA" not in worker


def test_sync_reloads_the_new_code_of_an_updated_plugin(storage, worker):
    assert not hasattr(worker["ConvA"]["class"], "VERSION")

    (storage.base_path / "sync-a" / "mod.py").write_text(
        module("ConvA", body="VERSION = 2"), encoding="utf-8"
    )
    _touch_later(storage.base_path / "sync-a" / "manifest.json")

    assert sync_installed_plugins(storage, worker) == ["sync-a"]
    assert worker["ConvA"]["class"].VERSION == 2


def test_the_workers_load_errors_reach_the_api_until_the_plugin_changes(
    storage, worker
):
    plugin_dir = _installed(storage, "sync-broken", code="raise RuntimeError('boom')")

    sync_installed_plugins(storage, worker, is_worker=True)
    bootstrap.load_errors.clear()  # the API process never saw it

    assert "boom" in bootstrap.worker_load_errors(storage)["sync-broken"]
    _touch_later(plugin_dir / "manifest.json")
    assert bootstrap.worker_load_errors(storage) == {}


def _base(storage, plugin_id="pz-base", body="pass"):
    """A plugin whose Base others subclass."""
    return _installed(storage, plugin_id, "ZConv", module("ZConv", body=body))


def _user(storage, plugin_id="pa-user", needs="pz-base"):
    """A plugin that subclasses ``needs``'s Base."""
    package = "dashai_plugins.p" + needs.replace("-", "_")
    code = f"from {package}.mod import Base\n\nclass UserConv(Base):\n    pass\n"
    return _installed(storage, plugin_id, "UserConv", code, needs=[needs])


@pytest.fixture
def base_and_user(storage):
    """pz-base and pa-user, which needs it, loaded at startup."""
    _base(storage)
    _user(storage)
    registry = ComponentRegistry(initial_components=[])
    sync_installed_plugins(storage, registry)
    return registry


def test_updating_the_base_reloads_its_dependent_against_the_new_code(
    storage, base_and_user
):
    _base(storage, body="VERSION = 2")
    _touch_later(storage.base_path / "pz-base" / "manifest.json")

    assert sync_installed_plugins(storage, base_and_user) == ["pa-user", "pz-base"]
    new_base = sys.modules["dashai_plugins.ppz_base.mod"].Base
    assert issubclass(base_and_user["pa-user:UserConv"]["class"], new_base)


def test_disabling_the_base_unloads_its_dependent(storage, base_and_user):
    storage.set_enabled("pz-base", False)

    assert sync_installed_plugins(storage, base_and_user) == ["pa-user", "pz-base"]
    assert "pa-user:UserConv" not in base_and_user
    assert storage.is_enabled("pa-user")  # the user's choice is untouched

    storage.set_enabled("pz-base", True)

    assert sync_installed_plugins(storage, base_and_user) == ["pz-base", "pa-user"]
    assert "pa-user:UserConv" in base_and_user


def test_a_dependent_loads_only_with_a_base_version_in_its_range(storage):
    _base(storage)
    _installed(storage, "pa-user", "UserConv", needs=["pz-base>=2"])
    registry = ComponentRegistry(initial_components=[])

    assert sync_installed_plugins(storage, registry) == ["pz-base"]
    manifests = bootstrap.installed_manifests(storage)
    assert bootstrap.wrong_versions(manifests["pa-user"], manifests) == ["pz-base"]

    folder = storage.base_path / "pz-base"
    make_plugin(folder, "pz-base", "ZConv", module("ZConv"), version="2.0.0")
    _touch_later(folder / "manifest.json")

    assert "pa-user" in sync_installed_plugins(storage, registry)
    assert "pa-user:UserConv" in registry


def test_a_chain_loads_in_order_and_a_cycle_loads_nothing(storage):
    _base(storage, "pc-base")
    _user(storage, "pb-mid", needs="pc-base")
    _installed(storage, "pa-top", "Top", needs=["pb-mid"])
    _installed(storage, "cy-a", "CyA", needs=["cy-b"])
    _installed(storage, "cy-b", "CyB", needs=["cy-a"])
    registry = ComponentRegistry(initial_components=[])

    assert sync_installed_plugins(storage, registry) == ["pc-base", "pb-mid", "pa-top"]
    assert "cy-a:CyA" not in registry
    assert "cy-b:CyB" not in registry


def test_dependents_are_found_in_install_order_also_once_the_base_is_gone():
    def parsed(plugin_id, *needs):
        fields = manifest(plugin_id, plugin_dependencies=list(needs))
        return PluginManifest.from_dict(fields)

    manifests = {
        "a": parsed("a", "b", "c"),
        "b": parsed("b", "c"),
        "c": parsed("c"),
        "x": parsed("x"),
    }

    assert bootstrap.install_order(manifests) == ["c", "x", "b", "a"]
    assert bootstrap.dependents(manifests, "c") == ["b", "a"]
    del manifests["c"]  # uninstalled
    assert bootstrap.dependents(manifests, "c") == ["b", "a"]


def test_the_load_check_loads_the_plugins_it_needs_first(tmp_path, storage, capsys):
    _base(storage, "lc-base")
    staging = make_plugin(
        tmp_path / "staging" / "lc-user",
        "lc-user",
        "UserConv",
        "from dashai_plugins.plc_base.mod import Base\n\n"
        "class UserConv(Base):\n    pass\n",
        plugin_dependencies=["lc-base"],
    )

    assert load_check.main(["load_check", str(staging), str(tmp_path)]) == 0, (
        capsys.readouterr().err
    )
