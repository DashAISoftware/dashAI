import sys
import types
from abc import ABCMeta
from typing import Final
from unittest.mock import patch

import pytest
from kink import di

from DashAI.back.config_object import ConfigObject
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.job.sync_components_job import SyncComponentsJob
from DashAI.back.plugins.environment import get_plugins_directory


@pytest.fixture(autouse=True)
def _isolated_plugins_directory(tmp_path, monkeypatch):
    """Keep the plugins directory the tests activate out of the real home."""
    monkeypatch.setenv("DASHAI_LOCAL_PATH", str(tmp_path))


class DummyBaseComponent(ConfigObject, metaclass=ABCMeta):
    """Dummy base class representing a component"""

    TYPE: Final[str] = "Component"


def _plugin_class(module_name: str) -> type:
    return type(
        "FakePluginComponent", (DummyBaseComponent,), {"__module__": module_name}
    )


def test_sync_replaces_a_plugin_class_upgraded_by_another_process():
    """The consumer must drop the old plugin code and register the new class."""
    module = types.ModuleType("fake_dashai_plugin.model")
    module.__file__ = str(get_plugins_directory() / "fake_dashai_plugin" / "model.py")
    stale_class = _plugin_class(module.__name__)
    upgraded_class = _plugin_class(module.__name__)
    registry = ComponentRegistry(initial_components=[stale_class])

    def available_plugins():
        # Like a fresh import: only possible once the old module is forgotten.
        assert module.__name__ not in sys.modules
        return [upgraded_class]

    def initial_components():
        # DashAI's initial components include the installed plugins too.
        return available_plugins()

    old_registry = di["component_registry"] if "component_registry" in di else None  # noqa: SIM401
    di["component_registry"] = registry
    try:
        with (
            patch.dict(sys.modules, {module.__name__: module}),
            patch(
                "DashAI.back.initial_components.get_initial_components",
                side_effect=initial_components,
            ),
            patch(
                "DashAI.back.job.sync_components_job.get_available_plugins",
                side_effect=available_plugins,
            ),
        ):
            SyncComponentsJob().run()
    finally:
        if old_registry is None:
            del di["component_registry"]
        else:
            di["component_registry"] = old_registry

    assert registry["FakePluginComponent"]["class"] is upgraded_class
