"""Each component id has one owner, dashAI or one plugin, at every moment."""

from plugin_helpers import make_plugin

from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.metrics.classification.accuracy import Accuracy
from DashAI.back.plugins import bootstrap


def test_two_plugins_with_the_same_name_load_at_startup(storage):
    make_plugin(storage.base_path / "a", "a", "Twin")
    make_plugin(storage.base_path / "b", "b", "Twin")
    registry = ComponentRegistry(initial_components=[])

    loaded = bootstrap.sync_installed_plugins(storage, registry)

    assert set(loaded) == {"a", "b"}
    assert "a:Twin" in registry
    assert "b:Twin" in registry


def test_a_plugin_never_replaces_a_dashai_component(storage):
    code = (
        "from DashAI.back.metrics.classification.accuracy import Accuracy as _A\n"
        "class Accuracy(_A):\n    pass\n"
    )
    metric = [{"class": "mod:Accuracy", "type": "Metric"}]
    make_plugin(storage.base_path / "shadow", "shadow", code=code, components=metric)
    registry = ComponentRegistry(initial_components=[Accuracy])

    assert list(bootstrap.sync_installed_plugins(storage, registry)) == ["shadow"]
    assert registry["Accuracy"]["class"] is Accuracy
    assert registry["shadow:Accuracy"]["class"] is not Accuracy
