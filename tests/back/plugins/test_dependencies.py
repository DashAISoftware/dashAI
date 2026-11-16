import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from DashAI.back.plugins.dependencies import (
    DependencyError,
    PluginDependencies,
    _resolve_record_entry,
    activate_dependencies,
    dependencies_directory,
    unmet_requirements,
)
from DashAI.back.plugins.disk.storage import plugins_root


def test_the_dependencies_directory_is_importable_after_dashais_own_packages(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    root = plugins_root(tmp_path)

    directory = activate_dependencies(root)
    activate_dependencies(root)

    interpreter = f"py{sys.version_info.major}.{sys.version_info.minor}"
    assert directory == dependencies_directory(root)
    assert directory == tmp_path / "plugins" / interpreter
    assert directory.is_dir()
    assert sys.path[-1] == str(directory)
    assert sys.path.count(str(directory)) == 1
    assert os.environ["PYTHONPATH"] == "/somewhere/else"


def _install(deps, requirements, others=()):
    resolution = deps.resolve(list(requirements), list(others))
    assert resolution.ok, resolution.explanation
    transaction = deps.transaction()
    transaction.install(resolution.distributions)
    transaction.commit()
    return transaction


def test_resolve_fails_with_pip_explanation(env):
    resolution = env.deps.resolve(["pkg>=3"])

    assert not resolution.ok
    assert "ResolutionImpossible" in resolution.explanation


def test_constraint_includes_dashai_lock_and_other_plugins(env, monkeypatch):
    monkeypatch.setattr(
        PluginDependencies, "_dashai_lock", lambda self, d: ["numpy==1.26.4"]
    )

    env.deps.resolve(["a"], other_dependencies=["pkg<2"])

    assert "numpy==1.26.4" in env.pip.constraint_contents[0]
    assert "pkg<2" in env.pip.constraint_contents[0]


def test_closure_stops_at_what_dashai_provides(env, monkeypatch):
    _install(env.deps, ["x"])
    monkeypatch.setattr(PluginDependencies, "_dashai_lock", lambda self, d: ["y==1.0"])

    assert env.deps.closure(["x"]) == {"x"}


def test_failed_pip_install_leaves_everything_as_it_was(env):
    _install(env.deps, ["pkg==1.0"])
    env.pip.fail_install = "network down"

    transaction = env.deps.transaction()
    with pytest.raises(DependencyError, match="network down"):
        transaction.install(env.deps.resolve(["pkg==2.0"]).distributions)
    transaction.rollback()

    assert env.on_disk() == ["pkg-1.0"]


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("dashai_plugin/__init__.py", "dashai_plugin/__init__.py"),
        ("../../bin/plugin-cli.exe", "bin/plugin-cli.exe"),
        (r"..\..\Scripts\plugin.exe", "Scripts/plugin.exe"),
    ],
)
def test_record_entries_stay_inside_the_plugins_directory(tmp_path, relative, expected):
    resolved = _resolve_record_entry(tmp_path, relative)

    assert resolved == (tmp_path / expected).resolve()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows file locking")
def test_removing_a_compiled_module_loaded_by_another_process(env):
    """Windows refuses to delete a loaded .pyd but allows moving it."""
    source = next(Path(__import__("markupsafe").__file__).parent.glob("_speedups*.pyd"))
    deps, directory = env.deps, env.deps_dir
    package = directory / "lockedpkg"
    package.mkdir()
    (package / "__init__.py").write_text("")
    shutil.copy(source, package / source.name)
    info = directory / "lockedpkg-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: lockedpkg\nVersion: 1.0\n"
    )
    (info / "RECORD").write_text(
        f"lockedpkg/__init__.py,,\nlockedpkg/{source.name},,\n"
    )
    module = source.name.split(".", 1)[0]
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, r'{directory}');"
            f" import lockedpkg.{module}; print('ok', flush=True);"
            " sys.stdin.read()",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "ok"
        with pytest.raises(PermissionError):
            (package / source.name).unlink()  # what deleting in place hits

        transaction = deps.transaction()
        transaction.remove({"lockedpkg"})
        transaction.commit()  # the locked file just stays in the trash

        assert env.on_disk() == []
        assert not package.exists()
    finally:
        holder.kill()
        holder.wait()


def test_unmet_requirements_tells_missing_from_conflicting_with_dashai(tmp_path):
    plugins_dir = tmp_path / "py3.x"  # packaging is dashAI's, not in here

    assert unmet_requirements(["packaging>=1"], plugins_dir) == ([], [])
    missing, conflicts = unmet_requirements(["packaging<1"], plugins_dir)
    assert missing == []
    assert conflicts[0].startswith("packaging<1 (found ")
    assert unmet_requirements(["surely-not-installed-pkg>=1"], plugins_dir) == (
        ["surely-not-installed-pkg>=1 (not installed)"],
        [],
    )
    skipped = ["surely-not-installed-pkg; python_version < '3'"]
    assert unmet_requirements(skipped, plugins_dir) == ([], [])


def test_what_an_extra_needs_is_checked_too(tmp_path, monkeypatch):
    dist_info = tmp_path / "site" / "base_pkg-1.0.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: base-pkg\nVersion: 1.0\n"
        "Provides-Extra: fx\nRequires-Dist: needed-by-fx>=2; extra == 'fx'\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path / "site"))

    assert unmet_requirements(["base-pkg"], tmp_path) == ([], [])
    assert unmet_requirements(["base-pkg[fx]"], tmp_path) == (
        ["needed-by-fx>=2 (not installed)"],
        [],
    )
