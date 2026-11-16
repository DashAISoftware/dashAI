"""Plugin dependencies across install, update, uninstall, failure and restart."""

import json
import shutil
import threading
import time
from pathlib import Path

import pytest
from plugin_helpers import BASE, BROKEN, Env

from DashAI.back.core.enums.plugin_source import PluginSource
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins import bootstrap
from DashAI.back.plugins.dependencies import DependencyTransaction, PluginDependencies
from DashAI.back.plugins.plugin_installer import PluginBusyError, PluginInstallError


def test_update_to_a_version_incompatible_with_the_old_one(tmp_path):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["pkg<2"])

    updated = env.install("p", "2.0.0", ["pkg>=2"])

    assert updated.version == "2.0.0"
    assert env.on_disk() == ["pkg-2.0"]


def test_a_dependency_the_new_version_dropped_is_removed(tmp_path):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["a", "b"])

    env.install("p", "2.0.0", ["a"])

    assert env.on_disk() == ["a-1.0"]
    assert env.deps.read_ledger().plugins == {"p": ["a"]}
    assert env.deps.read_ledger().pending == []


def test_uninstall_keeps_transitive_dependencies_another_plugin_needs(tmp_path):
    env = Env(tmp_path)
    env.install("plugin-a", "1.0.0", ["x"])  # x needs y
    env.install("plugin-b", "1.0.0", ["x"])

    env.installer.uninstall("plugin-a")

    assert env.on_disk() == ["x-1.0", "y-1.0"]
    env.installer.uninstall("plugin-b")
    assert env.on_disk() == []


def test_keeps_what_an_extra_of_a_package_dashai_ships_added(tmp_path):
    env = Env(tmp_path)
    env.pip.index["trimesh"] = {"1.0": {}}  # what datasets[mesh] adds
    env.install("p", "1.0.0", ["datasets[mesh]"])  # datasets ships with dashAI
    env.install("q", "1.0.0", ["trimesh"])

    env.installer.uninstall("q")

    assert env.on_disk() == ["trimesh-1.0"]


def _failing_remove(self, names):
    raise OSError("file in use")


def _closed(*args, **kwargs):
    raise KeyboardInterrupt  # dashAI closed right there


@pytest.mark.parametrize("change", ["uninstall", "update", "closed_before_forget"])
def test_a_prune_that_fails_is_retried_at_startup(tmp_path, monkeypatch, change):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["a", "b"])
    monkeypatch.setattr(DependencyTransaction, "remove", _failing_remove)
    if change == "update":
        env.install("p", "2.0.0", ["a"])
    elif change == "uninstall":
        env.installer.uninstall("p")
    else:
        monkeypatch.setattr(PluginDependencies, "forget", _closed)
        with pytest.raises(KeyboardInterrupt):
            env.installer.uninstall("p")
    env.reopen()  # fails again, still pending
    monkeypatch.undo()
    assert env.on_disk() == ["a-1.0", "b-1.0"]

    env.reopen()

    assert env.on_disk() == (["a-1.0"] if change == "update" else [])
    assert env.deps.read_ledger().pending == []


def test_startup_never_prunes_a_package_the_ledger_does_not_know(tmp_path):
    env = Env(tmp_path)
    info = env.deps_dir / "old-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: old\nVersion: 1.0\n")
    (info / "RECORD").write_text("old.py,,\nold-1.0.dist-info/METADATA,,\n")
    (env.deps_dir / "old.py").write_text("")

    env.installer.startup_maintenance()

    assert env.on_disk() == ["old-1.0"]


def test_an_unreadable_manifest_keeps_its_ledger_entry(tmp_path):
    env = Env(tmp_path)
    env.install("d", "1.0.0", ["a"])
    env.install("e", "1.0.0", ["a"])
    (env.storage.plugin_dir("d") / "manifest.json").write_text("{not json")

    env.installer.uninstall("e")
    env.reopen()

    assert env.on_disk() == ["a-1.0"]


def test_failed_update_restores_the_old_dependency_versions(tmp_path):
    env = Env(tmp_path)
    first = env.plugin("p", "1.0.0", ["pkg<2"], cls="C1")
    env.installer.install(PluginSource.LOCAL, first)

    with pytest.raises(PluginInstallError, match="Load failed"):
        env.install("p", "2.0.0", ["pkg>=2"], module=BROKEN.format(cls="C2"), cls="C2")

    assert env.on_disk() == ["pkg-1.0"]
    assert (env.deps_dir / "pkg.py").read_text() == "VERSION = '1.0'\n"
    manifest = json.loads((env.storage.plugin_dir("p") / "manifest.json").read_text())
    assert manifest["version"] == "1.0.0"
    assert "C1" in env.registry
    assert env.deps.read_ledger().plugins == {"p": ["pkg"]}
    assert env.storage.read_source("p").location == first


def test_failed_fresh_install_leaves_no_dependency_behind(tmp_path):
    env = Env(tmp_path)

    with pytest.raises(PluginInstallError, match="Load failed"):
        env.install("p", "1.0.0", ["x"], module=BROKEN.format(cls="C_p"))

    assert env.on_disk() == []
    assert not env.storage.is_installed("p")


LIBX_V1 = f"import libx\n{BASE}class C(Base):\n    LIB = libx.VERSION\n"
LIBX_V2 = f"from libx import algo_nuevo\n{BASE}class C(Base):\n    LIB = 'v2'\n"


def test_update_replacing_a_loaded_library_is_accepted_and_pending(tmp_path):
    checked = []
    env = Env(tmp_path, load_check=checked.append)
    env.install("p", "1.0.0", ["libx<2"], module=LIBX_V1, cls="C")
    assert env.registry["C"]["class"].LIB == "1.0"  # libx 1.0 now in memory

    updated = env.install("p", "2.0.0", ["libx>=2"], module=LIBX_V2, cls="C")

    assert updated.pending_restart
    assert checked  # validated in a fresh process, not against the old libx
    assert env.installer.pending_restart == {"p"}
    assert "C" not in env.registry  # nothing offered that jobs wouldn't run
    assert env.on_disk() == ["libx-2.0"]
    assert env.marker().exists()  # the job worker restarts before its next job


def test_concurrent_operations_run_one_after_the_other(tmp_path):
    env = Env(tmp_path)
    active, overlaps = [0], []
    original = env.pip.__call__

    def slow_pip(cmd, **kwargs):
        active[0] += 1
        overlaps.append(active[0])
        time.sleep(0.05)
        try:
            return original(cmd, **kwargs)
        finally:
            active[0] -= 1

    env.deps.runner = slow_pip
    sources = [env.plugin("p1", "1.0.0", ["a"]), env.plugin("p2", "1.0.0", ["b"])]
    threads = [
        threading.Thread(
            target=env.installer.install, args=(PluginSource.LOCAL, source)
        )
        for source in sources
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert max(overlaps) == 1
    assert env.on_disk() == ["a-1.0", "b-1.0"]


def test_changing_dependencies_waits_for_running_jobs(tmp_path):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["a"])
    env.running = True

    with pytest.raises(PluginBusyError, match="A job is running"):
        env.install("q", "1.0.0", ["b"])
    with pytest.raises(PluginBusyError):
        env.installer.uninstall("p")

    env.install("r", "1.0.0")
    env.installer.disable("p")
    env.installer.enable("p")
    assert env.on_disk() == ["a-1.0"]


def test_dependency_changes_ask_the_worker_to_restart(tmp_path):
    env = Env(tmp_path)
    env.install("p", "1.0.0")
    assert not env.marker().exists()  # no dependency changed

    env.install("q", "1.0.0", ["a"])
    first = env.marker().stat().st_mtime_ns
    time.sleep(0.02)
    env.installer.uninstall("q")

    assert env.marker().stat().st_mtime_ns > first


def _reopen_on_another_python(env):
    """dashAI reopened on another Python: its py3.x folder starts empty."""
    env.deps_dir.rename(env.deps_dir.with_name("py-previous"))
    registry = ComponentRegistry(initial_components=[])
    installer = env.reopen(registry)
    bootstrap.sync_installed_plugins(env.storage, registry)
    return installer, registry


def test_startup_installs_again_what_the_plugins_miss(tmp_path):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["x"], cls="C1")  # x needs y
    marker = env.storage.plugin_dir("p") / env.storage.SOURCE_MARKER
    origin = {**json.loads(marker.read_text()), "trust_level": "github_attested"}
    marker.write_text(json.dumps(origin))
    installer, registry = _reopen_on_another_python(env)
    assert "C1" not in registry
    assert "installs them when it starts" in bootstrap.load_errors["p"]

    installer.repair_missing()  # what dashAI runs at startup

    assert "C1" in registry
    assert env.on_disk() == ["x-1.0", "y-1.0"]
    assert env.storage.read_source("p").trust_level == "github_attested"  # kept


def test_offline_the_repair_does_not_run_pip(tmp_path):
    env = Env(tmp_path)
    env.install("p", "1.0.0", ["x"], cls="C1")
    installer, registry = _reopen_on_another_python(env)
    env.deps.index_reachable = lambda: False
    calls = len(env.pip.calls)

    installer.repair_missing()

    assert len(env.pip.calls) == calls
    assert "C1" not in registry
    assert "no internet connection" in installer.repair_errors["p"]


def test_code_imported_on_use_is_found_after_installing_from_a_zip(tmp_path):
    env = Env(tmp_path)
    module = BASE + "class OnUse(Base):\n    def value(self):\n"
    module += "        from .helper import VALUE\n        return VALUE\n"
    folder = Path(env.plugin("on-use", "1.0.0", module=module, cls="OnUse"))
    (folder / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
    upload = shutil.make_archive(str(tmp_path / "on-use"), "zip", folder)

    env.installer.install(PluginSource.LOCAL, upload)  # extracted to a temp dir

    assert env.registry["OnUse"]["class"]().value() == 42


def test_a_package_that_would_overwrite_another_ones_files_is_refused(tmp_path):
    env = Env(tmp_path)
    env.pip.index["cvfull"] = {"1.0": {"files": {"cv/__init__.py": "B = 'f'\n"}}}
    env.pip.index["cvheadless"] = {"1.0": {"files": {"cv/__init__.py": "B = 'h'\n"}}}
    env.install("gui", "1.0.0", ["cvfull"], cls="Gui")

    with pytest.raises(PluginInstallError, match="overwrite files of cvfull"):
        env.install("server", "1.0.0", ["cvheadless"], cls="Server")

    assert (env.deps_dir / "cv" / "__init__.py").read_text() == "B = 'f'\n"
    assert not env.storage.is_installed("server")


def test_pruning_keeps_an_identical_file_another_package_ships(tmp_path):
    env = Env(tmp_path)
    shared = "__path__ = __import__('pkgutil').extend_path(__path__, __name__)\n"
    for name in ("a", "b"):
        files = {"ns/__init__.py": shared, f"ns/{name}.py": ""}
        env.pip.index[f"ns-{name}"] = {"1.0": {"files": files}}
    env.install("pa", "1.0.0", ["ns-a"], cls="Pa")
    env.install("pb", "1.0.0", ["ns-b"], cls="Pb")

    env.installer.uninstall("pa")

    assert env.on_disk() == ["ns-b-1.0"]
    assert (env.deps_dir / "ns" / "__init__.py").exists()
    assert not (env.deps_dir / "ns" / "a.py").exists()
