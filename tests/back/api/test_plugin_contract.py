"""The plugin API's contract with the front, a code, status and params each."""

import itertools
import json
from unittest.mock import Mock

import pytest

from DashAI.back.plugins import bootstrap
from DashAI.back.plugins.disk.storage import Blocked
from DashAI.back.plugins.plugin_installer import (
    BUSY_MESSAGE,
    PluginBusyError,
    PluginInstallError,
    PluginRateLimitError,
)
from tests.back.plugins.plugin_helpers import module, plugin_zip

API = "/api/v1/plugin"
SETTINGS = """
from DashAI.back.core.schema_fields import enum_field, int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.plugins.settings import BasePluginSettings

class Settings(BasePluginSettings):
    threads: schema_field(
        int_field(ge=1, le=8), 2, MultilingualString(en="Threads", es="Hilos")
    )
    device: schema_field(enum_field(["cpu", "cuda"]), "cpu", "Device")
"""
_numbers = itertools.count()


@pytest.fixture
def plugin():
    """A fresh (id, class name): the module's registry keeps what tests load."""
    n = next(_numbers)
    return f"contract-{n}", f"ContractConverter{n}"


def _zip(plugin, code=None, **overrides):
    """``plugin`` as a .zip, with all the install popup shows."""
    fields = {
        "name": "Contract Plugin",
        "description": "What the install popup shows.",
        "authors": [
            {"name": "Jane Roe", "email": "jane@example.org", "url": "https://jr.dev"}
        ],
        "project_urls": {"Homepage": "https://example.org/contract"},
        **overrides,
    }
    return plugin_zip(*plugin, code, **fields)


def _with_settings(plugin, **overrides):
    return _zip(
        plugin, module(plugin[1]) + SETTINGS, settings="mod:Settings", **overrides
    )


@pytest.fixture
def base_and_user(client, plugin):
    """``plugin`` installed, and another one (with settings) that needs it."""
    base, user = plugin[0], (f"{plugin[0]}-user", f"{plugin[1]}User")
    assert _upload(client, _zip(plugin)).status_code == 201
    needs_base = _with_settings(user, plugin_dependencies=[base])
    assert _upload(client, needs_base).status_code == 201
    return base, user[0]


def _listed(client):
    return {p["id"]: p for p in client.get(f"{API}/installed").json()}


def _preview(client, zip_bytes):
    response = client.post(
        f"{API}/upload/validate",
        files={"file": ("plugin.zip", zip_bytes, "application/zip")},
    )
    assert response.status_code == 200
    return response.json()


def _upload(client, zip_bytes):
    return client.post(
        f"{API}/", json={"preview": _preview(client, zip_bytes)["preview"]}
    )


def _error(response, status):
    assert response.status_code == status, response.text
    error = response.json()["detail"]
    assert set(error) == {"code", "detail", "params"}
    return error


def test_the_preview_carries_what_the_install_popup_shows(client, plugin):
    body = _preview(client, _zip(plugin))

    assert body["is_valid"], body["errors"]
    assert body["name"] == "Contract Plugin"
    assert body["description"] == "What the install popup shows."
    assert body["dependencies"] == []
    assert body["authors"] == [
        {"name": "Jane Roe", "email": "jane@example.org", "url": "https://jr.dev"}
    ]
    assert body["project_urls"] == {"Homepage": "https://example.org/contract"}
    assert body["sha256"]
    assert plugin[0] not in _listed(client)  # a preview installs nothing


def test_the_installed_list_carries_what_the_detail_view_shows(client, plugin):
    assert _upload(client, _zip(plugin)).status_code == 201

    entry = _listed(client)[plugin[0]]

    assert entry["authors"][0]["url"] == "https://jr.dev"
    assert entry["project_urls"] == {"Homepage": "https://example.org/contract"}
    assert entry["dependencies"] == []
    assert (entry["asset"], entry["workflow"], entry["signed_at"], entry["issuer"]) == (
        None,
        None,
        None,
        None,
    )
    assert (entry["trust_level"], entry["trust_tier"]) == ("local", "local")
    assert entry["problem"] is None


def test_active_is_off_while_a_problem_lasts_and_keeps_the_choice(client, plugin):
    plugin_id = plugin[0]
    assert _upload(client, _zip(plugin)).status_code == 201
    assert (
        _listed(client)[plugin_id]["enabled"],
        _listed(client)[plugin_id]["active"],
    ) == (True, True)

    installer = client.app.container["plugin_installer"]
    installer.pending_restart.add(plugin_id)
    try:
        entry = _listed(client)[plugin_id]
        assert (entry["enabled"], entry["active"]) == (True, False)
    finally:
        installer.pending_restart.discard(plugin_id)
    assert _listed(client)[plugin_id]["active"] is True

    response = client.patch(f"{API}/{plugin_id}", json={"enabled": False})
    assert (response.json()["enabled"], response.json()["active"]) == (False, False)


def test_a_plugin_whose_dependency_is_off_is_off_and_keeps_the_choice(
    client, base_and_user
):
    base, user = base_and_user
    entry = _listed(client)[user]
    assert (entry["plugin_dependencies"], entry["active"]) == ([base], True)

    client.patch(f"{API}/{base}", json={"enabled": False})

    entry = _listed(client)[user]
    assert (entry["problem"]["code"], entry["active"], entry["enabled"]) == (
        "dependency_unavailable",
        False,
        True,
    )
    enabled = client.patch(f"{API}/{user}", json={"enabled": True}).json()
    assert enabled["problem"]["code"] == "dependency_unavailable"
    refused = client.get(f"{API}/{user}/settings")
    assert _error(refused, 409)["code"] == "settings_unavailable"


def test_a_base_update_out_of_a_dependents_range_warns_and_turns_it_off(client, plugin):
    base, user = plugin[0], (f"{plugin[0]}-user", f"{plugin[1]}User")
    assert _upload(client, _zip(plugin)).status_code == 201
    needs = _zip(user, name="User", plugin_dependencies=[f"{base}<2"])
    assert _upload(client, needs).status_code == 201
    assert _listed(client)[user[0]]["plugin_specifiers"] == {base: "<2"}

    newer = _preview(client, _zip(plugin, version="2.0.0"))
    assert (newer["is_valid"], newer["breaks"]) == (True, ["User"])
    assert client.post(f"{API}/", json={"preview": newer["preview"]}).status_code == 201

    entry = _listed(client)[user[0]]
    assert (entry["problem"]["code"], entry["problem"]["params"]) == (
        "dependency_version",
        {"ids": [base]},
    )
    assert entry["active"] is False
    again = _preview(client, needs)
    assert [(e["code"], e["params"]) for e in again["errors"]] == [
        (
            "plugin_dependency_version",
            {"id": base, "required": "<2", "installed": "2.0.0"},
        )
    ]


@pytest.mark.parametrize("uninstall", [False, True])
def test_a_disabled_plugin_shows_no_problem_for_the_ones_it_needs(
    client, base_and_user, uninstall
):
    base, user = base_and_user
    client.patch(f"{API}/{user}", json={"enabled": False})

    if uninstall:
        assert client.delete(f"{API}/{base}").status_code == 204
    else:
        client.patch(f"{API}/{base}", json={"enabled": False})

    assert _listed(client)[user]["problem"] is None


def test_updating_a_plugin_whose_dependency_is_off_turns_nothing_on(
    client, plugin, base_and_user
):
    """Checked in a fresh interpreter (load_check), so neither turns on in the app."""
    base, user = base_and_user
    cls = f"{plugin[1]}User"
    package = "dashai_plugins.p" + base.replace("-", "_")

    def version(number, imported="Base"):
        code = (
            f"from {package}.mod import {imported} as Base\n\n\n"
            f"class {cls}(Base):\n    pass\n"
        )
        return _zip((user, cls), code, plugin_dependencies=[base], version=number)

    def states():
        listed = _listed(client)
        return [
            (p["version"], p["enabled"], (p["problem"] or {}).get("code"))
            for p in (listed[user], listed[base])
        ]

    client.patch(f"{API}/{user}", json={"enabled": False})
    client.patch(f"{API}/{base}", json={"enabled": False})

    assert _upload(client, version("2.0.0")).status_code == 201
    assert states() == [("2.0.0", False, None), ("1.0.0", False, None)]

    broken = _upload(client, version("3.0.0", imported="Missing"))
    assert _error(broken, 400)["code"] == "load_failed"
    assert states()[0] == ("2.0.0", False, None)

    base_module = client.app.container["plugin_storage"].plugin_dir(base) / "mod.py"
    code = base_module.read_text(encoding="utf-8")
    base_module.write_text("raise ImportError('broken base')\n", encoding="utf-8")
    try:
        failed = _error(_upload(client, version("2.5.0")), 400)
    finally:
        base_module.write_text(code, encoding="utf-8")
    assert (failed["code"], failed["params"]) == (
        "dependency_unavailable",
        {"id": base, "problem": "load_failed"},
    )
    assert states()[0] == ("2.0.0", False, None)

    client.patch(f"{API}/{user}", json={"enabled": True})
    assert _upload(client, version("4.0.0")).status_code == 201
    assert states() == [
        ("4.0.0", True, "dependency_unavailable"),
        ("1.0.0", False, None),
    ]
    client.patch(f"{API}/{base}", json={"enabled": True})
    assert _listed(client)[user]["active"] is True


def test_a_dependency_failing_only_in_jobs_leaves_the_plugin_off(client, base_and_user):
    base, user = base_and_user
    storage = client.app.container["plugin_storage"]
    errors = storage.root / bootstrap.WORKER_LOAD_ERRORS
    fingerprint = bootstrap._fingerprint(storage, base)
    errors.write_text(json.dumps({base: [fingerprint, "boom"]}), encoding="utf-8")
    try:
        listed = _listed(client)
        assert listed[base]["problem"]["code"] == "load_failed"
        assert (listed[user]["problem"]["code"], listed[user]["active"]) == (
            "dependency_unavailable",
            False,
        )
        refused = client.get(f"{API}/{user}/settings")
        assert _error(refused, 409)["code"] == "settings_unavailable"
    finally:
        errors.unlink()


def test_a_blocked_plugin_is_off_and_asks_to_be_allowed(client, plugin):
    plugin_id = plugin[0]
    assert _upload(client, _zip(plugin)).status_code == 201
    client.app.container["plugin_storage"].set_blocked(plugin_id, Blocked("d"))

    entry = _listed(client)[plugin_id]
    assert (entry["problem"]["code"], entry["active"]) == ("blocked", False)
    refused = client.patch(f"{API}/{plugin_id}", json={"enabled": True})
    assert _error(refused, 400)["code"] == "blocked"

    allowed = client.patch(
        f"{API}/{plugin_id}", json={"enabled": True, "allow_blocked": True}
    )
    assert (allowed.json()["problem"], allowed.json()["active"]) == (None, True)


@pytest.mark.parametrize(
    ("overrides", "code", "params"),
    [
        ({"id": "My_Plugin"}, "invalid_id", {"id": "My_Plugin"}),
        (
            {"authors": [{"name": "X", "url": "javascript:alert(1)"}]},
            "invalid_manifest",
            {"fields": ["authors.0.url"]},
        ),
        (
            {"plugin_dependencies": ["nowhere"]},  # neither installed nor in the store
            "missing_plugin_dependency",
            {"id": "nowhere", "store_read": False},
        ),
        ({"min_app_version": "99.0.0"}, "needs_newer_dashai", {"required": "99.0.0"}),
    ],
)
def test_a_preview_error_has_its_code_and_params(
    client, plugin, overrides, code, params
):
    body = _preview(client, _zip(plugin, **overrides))

    (error,) = body["errors"]
    assert error["code"] == code
    assert error["params"].items() >= params.items()
    assert body["preview"] is None


def test_without_a_store_a_missing_plugin_is_not_blamed_on_reading_it(
    client, plugin, monkeypatch
):
    monkeypatch.setattr(client.app.container["plugin_installer"], "store", None)
    body = _preview(client, _zip(plugin, plugin_dependencies=["nowhere"]))

    (error,) = body["errors"]
    assert error["params"] == {"id": "nowhere", "store_read": True}


def test_the_preview_lists_what_it_needs_and_why_one_is_unavailable(
    client, base_and_user
):
    base, user = base_and_user
    newcomer = (f"{base}-new", "NewConverter")

    body = _preview(client, _zip(newcomer, plugin_dependencies=[user]))
    assert [(p["id"], p["state"]) for p in body["plugin_dependencies"]] == [
        (base, "active"),
        (user, "active"),
    ]

    client.patch(f"{API}/{base}", json={"enabled": False})
    client.app.container["plugin_storage"].set_blocked(base, Blocked("d"))
    body = _preview(client, _zip(newcomer, plugin_dependencies=[user]))
    (error,) = body["errors"]
    assert (error["code"], error["params"]) == (
        "dependency_unavailable",
        {"id": base, "problem": "blocked"},
    )
    assert body["preview"] is None


def test_plugins_that_need_each_other_are_named(client, base_and_user):
    base, _ = base_and_user
    newcomer = (f"{base}-new", "NewConverter")
    storage = client.app.container["plugin_storage"]
    manifest = storage.plugin_dir(base) / storage.MANIFEST_FILENAME
    data = json.loads(manifest.read_text("utf-8"))
    data["plugin_dependencies"] = [newcomer[0]]
    manifest.write_text(json.dumps(data), encoding="utf-8")

    body = _preview(client, _zip(newcomer, plugin_dependencies=[base]))

    (error,) = body["errors"]
    assert (error["code"], error["params"]) == (
        "dependency_cycle",
        {"ids": sorted([base, newcomer[0]])},
    )


def test_two_plugins_can_share_a_component_name(client, plugin):
    assert _upload(client, _zip(plugin)).status_code == 201

    other = (f"{plugin[0]}-other", plugin[1])  # same class name, another plugin
    assert _preview(client, _zip(other))["errors"] == []
    assert _upload(client, _zip(other)).status_code == 201

    names = {c["name"] for c in client.get("/api/v1/component/").json()}
    assert {f"{plugin[0]}:{plugin[1]}", f"{other[0]}:{plugin[1]}"} <= names


def test_installing_a_preview_that_is_gone(client, plugin):
    token = _preview(client, _zip(plugin))["preview"]
    client.delete(f"{API}/previews/{token}")  # the dialog was closed

    error = _error(client.post(f"{API}/", json={"preview": token}), 400)

    assert error["code"] == "preview_expired"


@pytest.mark.parametrize(
    ("raised", "status", "code"),
    [
        (PluginBusyError(BUSY_MESSAGE), 409, "job_running"),
        (
            PluginRateLimitError("limit", resets_at=1, authenticated=False),
            429,
            "rate_limited",
        ),
        (
            PluginInstallError(
                "No newer", "no_newer_version", installed="1", latest="1"
            ),
            400,
            "no_newer_version",
        ),
    ],
)
def test_operation_errors_keep_their_code(
    client, restore_installer, raised, status, code
):
    restore_installer["plugin_installer"] = Mock(
        pending_restart=set(),
        repair_errors={},
        **{"install_preview.side_effect": raised},
    )

    response = client.post(f"{API}/", json={"preview": "aaaaaaaaaaaaaaaaaaaaaa"})

    error = _error(response, status)
    assert (error["code"], error["detail"]) == (code, str(raised))
    assert error["params"] == raised.params


@pytest.fixture
def with_settings(client, plugin):
    """``plugin``, with settings, installed and active: its id."""
    assert _upload(client, _with_settings(plugin)).status_code == 201
    yield plugin[0]
    client.app.container["plugin_installer"].pending_restart.discard(plugin[0])


def _settings_file(client, plugin_id):
    storage = client.app.container["plugin_storage"]
    return storage.root / "settings" / f"{plugin_id}.json"


def test_the_settings_form_is_the_schema_and_what_is_saved(client, with_settings):
    response = client.get(f"{API}/{with_settings}/settings")

    assert response.status_code == 200
    body = response.json()
    assert set(body["schema"]["properties"]) == {"threads", "device"}
    assert body["schema"]["properties"]["threads"]["placeholder"] == 2
    assert body["values"] == {}  # nothing saved, the form shows its defaults
    assert not _settings_file(client, with_settings).exists()  # a read never writes


def test_a_settings_save_keeps_what_differs_and_the_form_gets_it_back(
    client, with_settings
):
    url = f"{API}/{with_settings}/settings"

    response = client.put(url, json={"values": {"threads": 4, "device": "cpu", "x": 1}})

    assert response.status_code == 200
    assert response.json() == {"values": {"threads": 4}}
    saved = json.loads(_settings_file(client, with_settings).read_text())
    assert saved == {"threads": 4}
    assert client.get(url).json()["values"] == {"threads": 4}


def test_a_setting_that_does_not_validate_is_refused(client, with_settings):
    url = f"{API}/{with_settings}/settings"

    response = client.put(url, json={"values": {"threads": 99}})

    error = _error(response, 422)
    assert (error["code"], error["params"]) == (
        "invalid_settings",
        {"fields": ["threads"]},
    )
    assert not _settings_file(client, with_settings).exists()


def test_settings_only_while_active_and_the_saved_values_stay(client, with_settings):
    url = f"{API}/{with_settings}/settings"
    client.put(url, json={"values": {"device": "cuda"}})
    client.patch(f"{API}/{with_settings}", json={"enabled": False})

    assert _error(client.get(url), 409)["code"] == "settings_unavailable"
    response = client.put(url, json={"values": {}})
    assert _error(response, 409)["code"] == "settings_unavailable"

    client.patch(f"{API}/{with_settings}", json={"enabled": True})
    assert client.get(url).json()["values"] == {"device": "cuda"}
