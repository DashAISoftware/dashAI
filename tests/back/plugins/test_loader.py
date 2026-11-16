import re
import sys

import pytest
from plugin_helpers import make_plugin, module

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins.loader import PluginLoader, PluginLoadError
from DashAI.back.plugins.manifest.manifest import PluginManifest


def _load(folder, registry=None):
    manifest = PluginManifest.from_file(folder / "manifest.json")
    registry = registry or ComponentRegistry(initial_components=[])
    return PluginLoader.load(manifest, folder, registry), registry


def test_the_same_module_name_in_two_plugins_does_not_collide(tmp_path):
    for plugin_id in ("plugin-a", "plugin-b"):
        code = module("MyComp", body=f"ORIGIN = {plugin_id!r}")
        make_plugin(tmp_path / plugin_id, plugin_id, "MyComp", code)

    (loaded_a,), registry = _load(tmp_path / "plugin-a")
    (loaded_b,), _ = _load(tmp_path / "plugin-b", registry)

    assert (loaded_a.ORIGIN, loaded_b.ORIGIN) == ("plugin-a", "plugin-b")
    assert registry["plugin-a:MyComp"]["class"] is loaded_a


@pytest.mark.parametrize(
    ("code", "cls", "error"),
    [
        (
            module("Accuracy") + "Renamed = Accuracy\n",
            "Renamed",
            "is the class 'Accuracy'",
        ),
        (
            "from DashAI.back.metrics.classification.accuracy import Accuracy\n",
            "Accuracy",
            "is defined in dashAI",
        ),
        (
            "from dashai_plugins.pabsent_base.base import Base\n",
            "Thing",
            "Module 'mod' imports the plugin 'absent-base', which is not loaded; "
            "declare it in plugin_dependencies",
        ),
        ("class Plain:\n    pass\n", "Plain", "Could not determine the component type"),
    ],
)
def test_a_class_that_is_not_a_component_of_the_plugin_is_refused(
    tmp_path, code, cls, error
):
    make_plugin(tmp_path, cls=cls, code=code)

    with pytest.raises(PluginLoadError, match=re.escape(error)):
        _load(tmp_path)


class BaseRegisterAllComponent:
    TYPE = "Converter"


def test_register_all_restores_the_previous_component_on_partial_failure():
    class OldCompA(BaseRegisterAllComponent):
        pass

    class NewCompA(BaseRegisterAllComponent):
        pass

    class Broken:
        """Does not inherit from any Base* class: register_component() raises."""

    OldCompA.__name__ = NewCompA.__name__ = "CompA"
    registry = ComponentRegistry(initial_components=[])
    registry.register_component(OldCompA)

    with pytest.raises(PluginLoadError, match="Could not register component"):
        PluginLoader._register_all([NewCompA, Broken], registry)

    assert registry["CompA"]["class"] is OldCompA


def _importing_on_use(folder, value):
    """Its class imports ``helper`` only when used."""
    body = "def value(self):\n        from .helper import V\n        return V"
    make_plugin(folder, "on-use", "OnUse", module("OnUse", body=body))
    (folder / "helper.py").write_text(f"V = {value}\n", encoding="utf-8")


def test_relocate_points_the_loaded_plugin_at_its_new_folder(tmp_path):
    _importing_on_use(tmp_path / "fetched", 1)
    (loaded,), _ = _load(tmp_path / "fetched")
    (tmp_path / "fetched").rename(tmp_path / "installed")

    PluginLoader.relocate("on-use", tmp_path / "fetched", tmp_path / "installed")

    assert loaded().value() == 1
    assert sys.modules[loaded.__module__].__file__.startswith(
        str(tmp_path / "installed")
    )
