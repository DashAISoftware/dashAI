"""A plugin's settings (plugins/settings.py): its class, its saved values."""

import pytest
from kink import di
from plugin_helpers import make_plugin

from DashAI.back.core.schema_fields import (
    component_field,
    enum_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins import bootstrap
from DashAI.back.plugins import settings as plugin_settings
from DashAI.back.plugins.settings import BasePluginSettings

SETTINGS = """
from DashAI.back.core.schema_fields import (
    enum_field, int_field, schema_field, string_field,
)
from DashAI.back.plugins.settings import BasePluginSettings

class Settings(BasePluginSettings):
    url: schema_field(string_field(), "{url}", "Server URL")
    threads: schema_field(int_field(ge=1, le=8), 2, "Threads")
    device: schema_field(enum_field(["cpu", "cuda"]), "cpu", "Device")
"""
MODULE = """
from .settings import Settings

class Base:
    TYPE = "Converter"

class {cls}(Base):
    settings = Settings
"""


class Sample(BasePluginSettings):
    url: schema_field(string_field(), "http://localhost:1", "Server URL")
    threads: schema_field(int_field(ge=1, le=8), 2, "Threads")
    device: schema_field(enum_field(["cpu", "cuda"]), "cpu", "Device")


@pytest.fixture
def env(storage):
    """Installed plugins in a fresh registry, where ``load()`` looks."""
    registry = ComponentRegistry(initial_components=[])
    keys = {"plugin_storage": storage, "component_registry": registry}
    previous = {key: di[key] for key in keys if key in di}
    for key, value in keys.items():
        di[key] = value
    yield storage, registry
    for key in keys:
        if key in previous:
            di[key] = previous[key]
        else:
            del di[key]


def _plugin(storage, plugin_id, cls, settings=None):
    code = MODULE.format(cls=cls)
    folder = storage.base_path / plugin_id
    make_plugin(folder, plugin_id, cls, code, settings="settings:Settings")
    (folder / "settings.py").write_text(
        settings or SETTINGS.format(url=f"http://{plugin_id}"), encoding="utf-8"
    )
    return folder


def _load(storage, registry, plugin_id):
    """Load the installed plugins; the error that kept ``plugin_id`` out."""
    bootstrap.sync_installed_plugins(storage, registry)
    return bootstrap.load_errors.pop(plugin_id, None)


def _settings_of(registry, cls):
    return registry[cls]["class"].settings


def test_two_plugins_can_both_call_their_class_settings(env):
    storage, registry = env
    _plugin(storage, "alpha", "AlphaConverter")
    _plugin(storage, "beta", "BetaConverter")

    assert _load(storage, registry, "alpha") is None
    assert _load(storage, registry, "beta") is None

    alpha = _settings_of(registry, "AlphaConverter")
    beta = _settings_of(registry, "BetaConverter")
    assert alpha is not beta
    assert "Settings" not in registry
    assert alpha.load().threads == 2
    plugin_settings.save(
        plugin_settings.settings_file(storage.root, "alpha"), {"threads": 5}
    )
    assert (alpha.load().url, alpha.load().threads) == ("http://alpha", 5)
    assert (beta.load().url, beta.load().threads) == ("http://beta", 2)


def test_another_plugins_settings_class_fails_the_load(env):
    storage, registry = env
    _plugin(storage, "owner", "OwnerConverter")
    assert _load(storage, registry, "owner") is None
    borrowed = "from dashai_plugins.powner.settings import Settings\n"
    _plugin(storage, "borrower", "BorrowerConverter", settings=borrowed)

    error = _load(storage, registry, "borrower")

    assert error is not None
    assert "the plugin 'owner'" in error


def test_reading_drops_only_what_stopped_validating():
    registry = ComponentRegistry(initial_components=[])
    saved = {"url": "http://elsewhere", "threads": 20, "old": True}

    assert plugin_settings.clean(Sample, saved, registry) == {"url": "http://elsewhere"}


def _my_model(plugin):
    base = type("BaseConverter", (), {"TYPE": "Converter"})
    return type("MyModel", (base,), {"__module__": f"dashai_plugins.p{plugin}.mod"})


class WithModel(BasePluginSettings):
    model: schema_field(
        component_field(parent="BaseConverter"),
        {"component": "MyModel", "params": {}},
        "Model",
    )


WithModel.__module__ = "dashai_plugins.pp.settings"


def test_a_settings_schema_names_its_plugins_component_by_id():
    registry = ComponentRegistry(initial_components=[])

    properties = plugin_settings.schema(WithModel, registry)["properties"]

    assert properties["model"]["placeholder"]["component"] == "p:MyModel"


def test_a_saved_component_survives_another_plugin_with_its_name():
    registry = ComponentRegistry(initial_components=[_my_model("p"), _my_model("q")])
    saved = {"model": {"component": "p:MyModel", "params": {}}}

    assert plugin_settings.clean(WithModel, saved, registry) == saved
