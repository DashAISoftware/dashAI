from abc import ABCMeta
from typing import Final
from unittest.mock import patch

from kink import di

from DashAI.back.config_object import ConfigObject
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.initial_components import get_initial_components
from DashAI.back.job.sync_components_job import SyncComponentsJob


class DummyBaseComponent(ConfigObject, metaclass=ABCMeta):
    """Dummy base class representing a component"""

    TYPE: Final[str] = "Component"


class DummyPluginComponent(DummyBaseComponent):
    """Stands in for a component that an installed plugin brings in"""


def _run_job(registry, available_plugins):
    """
    Run the job treating ``available_plugins`` as the installed plugins

    Both modules that call ``get_available_plugins`` are patched, which leaves
    the real ``get_initial_components`` in play. The basic and plugin split
    lives there.
    """
    with (
        patch.dict(di._services, {"component_registry": registry}, clear=False),
        patch(
            "DashAI.back.initial_components.get_available_plugins",
            return_value=available_plugins,
        ),
        patch(
            "DashAI.back.job.sync_components_job.get_available_plugins",
            return_value=available_plugins,
        ),
    ):
        return SyncComponentsJob().run()


def test_sync_registers_a_plugin_missing_from_the_registry():
    registry = ComponentRegistry(
        initial_components=get_initial_components(include_plugins=False)
    )

    result = _run_job(registry, available_plugins=[DummyPluginComponent])

    assert result["added"] == ["DummyPluginComponent"]
    assert "DummyPluginComponent" in registry


def test_sync_does_not_readd_an_already_registered_plugin():
    """Plugins counted as basic components make each sync register all of them
    again and announce them as newly added."""
    registry = ComponentRegistry(
        initial_components=[
            *get_initial_components(include_plugins=False),
            DummyPluginComponent,
        ]
    )

    result = _run_job(registry, available_plugins=[DummyPluginComponent])

    assert result["added"] == []
    assert result["removed"] == []


def test_sync_unregisters_a_plugin_that_is_no_longer_installed():
    registry = ComponentRegistry(
        initial_components=[
            *get_initial_components(include_plugins=False),
            DummyPluginComponent,
        ]
    )

    result = _run_job(registry, available_plugins=[])

    assert result["removed"] == ["DummyPluginComponent"]
    assert "DummyPluginComponent" not in registry
    assert "Accuracy" in registry
