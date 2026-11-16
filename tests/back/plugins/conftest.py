import importlib
import sys

import pytest
from plugin_helpers import Env

from DashAI.back.plugins import bootstrap
from DashAI.back.plugins.dependencies import PluginDependencies
from DashAI.back.plugins.disk.storage import PluginStorage

_dashai_packages = []


@pytest.fixture(autouse=True)
def _isolate_plugins():
    """Undo the sys.path, plugin modules and load errors that loading leaves."""
    path, modules = list(sys.path), set(sys.modules)
    yield
    sys.path[:] = path
    importlib.invalidate_caches()
    for name in set(sys.modules) - modules:
        if name.startswith(("dashai_plugins", "libx", "dashaitest")):
            sys.modules.pop(name, None)
    bootstrap.load_errors.clear()


@pytest.fixture(autouse=True)
def _read_dashai_packages_once(monkeypatch):
    """dashAI's own packages don't change during the tests, read them once."""
    read = PluginDependencies._dashai_lock

    def once(self, directory):
        if not _dashai_packages:
            _dashai_packages.extend(read(self, directory))
        return list(_dashai_packages)

    monkeypatch.setattr(PluginDependencies, "_dashai_lock", once)


@pytest.fixture
def storage(tmp_path):
    return PluginStorage(tmp_path / "plugins" / "installed")


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)
