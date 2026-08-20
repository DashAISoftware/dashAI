import subprocess
from abc import ABCMeta
from typing import Final
from unittest.mock import Mock, patch

import pytest
import requests

from DashAI.back.config_object import ConfigObject
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.plugins.utils import (
    _get_all_plugins,
    _is_verified_author,
    execute_pip_command,
    get_plugin_by_name_from_pypi,
    get_plugins_from_pypi,
    uninstall_plugin,
    unregister_plugin_components,
)


class DummyBaseComponent(ConfigObject, metaclass=ABCMeta):
    """Dummy base class representing a component"""

    TYPE: Final[str] = "Component"


class DummyComponent1(DummyBaseComponent):
    pass


class DummyComponent2(DummyBaseComponent):
    pass


def test_get_all_plugins_with_proxy():
    mock_client = Mock()
    mock_client.json.return_value = {
        "meta": {"_last-serial": 0, "api-version": "1.0"},
        "projects": [
            {"_last-serial": 0, "name": "DashAI"},
            {"_last-serial": 1, "name": "dashai-tabular-classification-package"},
            {"_last-serial": 2, "name": "scikit-learn"},
        ],
    }
    mock_client.status_code = 200
    with patch("requests.get") as MockServerProxy:
        MockServerProxy.return_value = mock_client
        packages = _get_all_plugins()

    assert packages == [
        "DashAI",
        "dashai-tabular-classification-package",
        "scikit-learn",
    ]


def test_get_plugin_by_name_from_pypi():
    # Mockear la solicitud HTTP exitosa
    mock_response = Mock()
    json_return = {
        "info": {
            "author": "DashAI Team",
            "version": "0.1.0",
            "keywords": "DashAI,Package,Model,Dataloader",
            "description": "# Description \n",
            "description_content_type": "text/markdown",
            "name": "tabular-classification-package",
            "summary": "Tabular Classification Package",
        },
    }
    mock_response.json.return_value = json_return
    with patch("requests.get", return_value=mock_response):
        plugin_data = get_plugin_by_name_from_pypi("test_plugin")
    print("plugin_data", plugin_data)
    assert plugin_data == {
        "author": "DashAI Team",
        "verified": True,
        "installed_version": "0.1.0",
        "lastest_version": "0.1.0",
        "tags": [
            {"name": "DashAI"},
            {"name": "Package"},
            {"name": "Model"},
            {"name": "Dataloader"},
        ],
        "description": "# Description \n",
        "description_content_type": "text/markdown",
        "name": "tabular-classification-package",
        "summary": "Tabular Classification Package",
    }


def test_get_plugin_by_name_from_pypi_with_other_tags():
    # Mockear la solicitud HTTP exitosa
    mock_response = Mock()
    json_return = {
        "info": {
            "author": "DashAI Team",
            "version": "0.1.0",
            "keywords": "DashAI,Package,Model,Dataloader,Other",
            "description": "# Description \n",
            "description_content_type": "text/markdown",
            "name": "tabular-classification-package",
            "summary": "Tabular Classification Package",
        },
    }
    mock_response.json.return_value = json_return
    with patch("requests.get", return_value=mock_response):
        plugin_data = get_plugin_by_name_from_pypi("test_plugin")

    assert plugin_data == {
        "author": "DashAI Team",
        "verified": True,
        "installed_version": "0.1.0",
        "lastest_version": "0.1.0",
        "tags": [
            {"name": "DashAI"},
            {"name": "Package"},
            {"name": "Model"},
            {"name": "Dataloader"},
        ],
        "description": "# Description \n",
        "description_content_type": "text/markdown",
        "name": "tabular-classification-package",
        "summary": "Tabular Classification Package",
    }


def test_get_plugins_from_pypi():
    # Mock GET /simple/
    server_proxy_mock = Mock()
    server_proxy_mock.json.return_value = {
        "meta": {"_last-serial": 0, "api-version": "1.0"},
        "projects": [
            {"_last-serial": 0, "name": "image-classification-package"},
            {"_last-serial": 1, "name": "dashai-tabular-classification-package"},
            {"_last-serial": 2, "name": "scikit-dashai-learn"},
        ],
    }
    server_proxy_mock.status_code = 200

    # Mock GET /simple/<project>/ (status)
    status_mock = Mock()
    status_mock.status_code = 200
    status_mock.raise_for_status.return_value = None
    status_mock.json.return_value = {"project-status": {"status": "active"}}

    # Mock GET /pypi/<project>/json
    request_mock = Mock()
    request_mock.json.return_value = {
        "info": {
            "author": "DashAI Team",
            "version": "0.1.0",
            "keywords": "DashAI,Package,Model,Dataloader",
            "description": "# Description \n",
            "description_content_type": "text/markdown",
            "name": "dashai-tabular-classification-package",
            "summary": "Tabular Classification Package",
        },
    }

    with patch(
        "requests.get",
        side_effect=[server_proxy_mock, status_mock, request_mock],
    ):
        plugins = get_plugins_from_pypi()

    assert plugins == [
        {
            "author": "DashAI Team",
            "verified": True,
            "installed_version": "0.1.0",
            "lastest_version": "0.1.0",
            "tags": [
                {"name": "DashAI"},
                {"name": "Package"},
                {"name": "Model"},
                {"name": "Dataloader"},
            ],
            "description": "# Description \n",
            "description_content_type": "text/markdown",
            "name": "dashai-tabular-classification-package",
            "summary": "Tabular Classification Package",
        }
    ]


@pytest.mark.parametrize(
    ("author", "author_email", "expected"),
    [
        ("DashAI team", "dashaisoftware@gmail.com", True),
        ("Someone else", "DashAI team <dashaisoftware@gmail.com>", True),
        ("dashai team", "", True),
        ("Third party", "other@example.com", False),
        (None, None, False),
        ("DashAI", "info@dashai.org", False),
    ],
)
def test_is_verified_author(author, author_email, expected):
    assert _is_verified_author(author, author_email) is expected


def test_execute_pip_install_command():
    subprocess_mock = Mock()
    subprocess_mock.returncode = 0
    with patch("subprocess.run", return_value=subprocess_mock) as mock_run:
        result = execute_pip_command("dashai-tabular-classification-package", "install")

    assert result == 0
    mock_run.assert_called_once_with(
        ["pip", "install", "--no-cache-dir", "dashai-tabular-classification-package"],
        stderr=subprocess.PIPE,
        text=True,
    )


def test_execute_pip_uninstall_command():
    subprocess_mock = Mock()
    subprocess_mock.returncode = 0
    with patch("subprocess.run", return_value=subprocess_mock) as mock_run:
        result = execute_pip_command(
            "dashai-tabular-classification-package", "uninstall"
        )

    assert result == 0
    mock_run.assert_called_once_with(
        ["pip", "uninstall", "-y", "dashai-tabular-classification-package"],
        stderr=subprocess.PIPE,
        text=True,
    )


def test_error_execute_pip_command():
    subprocess_mock = Mock()
    subprocess_mock.returncode = 1
    subprocess_mock.stderr = "ERROR: ...\nERROR: ..."

    with patch("subprocess.run", return_value=subprocess_mock):  # noqa: SIM117
        with pytest.raises(RuntimeError, match="ERROR: ...\nERROR: ..."):
            execute_pip_command("dashai-tabular-classification-package", "install")


def test_execute_incorrect_pip_command():
    incorrect_pip_action = "incorrect"
    with pytest.raises(
        ValueError, match=f"Pip action {incorrect_pip_action} not supported"
    ):
        execute_pip_command(
            "dashai-tabular-classification-package", incorrect_pip_action
        )


def test_uninstall_plugin():
    entry_points_mock = Mock()
    entry_points_mock.side_effect = [
        [
            Mock(load=lambda: DummyComponent1, name="Plugin1"),
            Mock(load=lambda: DummyComponent2, name="Plugin2"),
        ],
        [Mock(load=lambda: DummyComponent2, name="Plugin2")],
    ]
    execute_pip_command_mock = Mock()
    execute_pip_command_mock.return_value = 0

    with patch("DashAI.back.plugins.utils.entry_points", entry_points_mock):  # noqa: SIM117
        with patch(
            "DashAI.back.plugins.utils.execute_pip_command", execute_pip_command_mock
        ):
            uninsalled_plugins = uninstall_plugin("Plugin1")

    assert uninsalled_plugins == {DummyComponent1}
    assert execute_pip_command_mock.call_count == 1
    assert entry_points_mock.call_count == 2
    execute_pip_command_mock.assert_called_once_with("Plugin1", "uninstall")


def test_unregister_plugin_components():
    component_registry = ComponentRegistry(
        initial_components=[DummyComponent1, DummyComponent2]
    )

    unregistered_components = unregister_plugin_components(
        [DummyComponent1], component_registry
    )
    registry_components = component_registry.registry["Component"]

    assert unregistered_components == [DummyComponent1]
    assert len(registry_components) == 1
    assert "DummyComponent1" not in registry_components
    assert "DummyComponent2" in registry_components


def test_get_all_plugins_sets_a_request_timeout():
    response_mock = Mock()
    response_mock.status_code = 200
    response_mock.json.return_value = {"projects": []}

    with patch("requests.get", return_value=response_mock) as get_mock:
        _get_all_plugins()

    assert get_mock.call_args.kwargs.get("timeout") is not None


def test_get_plugin_by_name_from_pypi_sets_a_request_timeout():
    response_mock = Mock()
    response_mock.json.return_value = {
        "info": {
            "author": "DashAI Team",
            "version": "0.1.0",
            "keywords": "",
            "name": "dashai-test-package",
        },
    }

    with patch("requests.get", return_value=response_mock) as get_mock:
        get_plugin_by_name_from_pypi("dashai-test-package")

    assert get_mock.call_args.kwargs.get("timeout") is not None


def test_get_plugins_from_pypi_skips_a_plugin_when_pypi_does_not_answer():
    """A network failure on one plugin must not abort the whole listing."""
    with (
        patch(
            "DashAI.back.plugins.utils._get_all_plugins",
            return_value=["dashai-first", "dashai-second"],
        ),
        patch(
            "DashAI.back.plugins.utils._get_pypi_project_status",
            return_value="active",
        ),
        patch(
            "DashAI.back.plugins.utils.get_plugin_by_name_from_pypi",
            side_effect=[
                requests.exceptions.ReadTimeout("pypi did not answer"),
                {"name": "dashai-second"},
            ],
        ),
    ):
        plugins = get_plugins_from_pypi()

    assert plugins == [{"name": "dashai-second"}]
