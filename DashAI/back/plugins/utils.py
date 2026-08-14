import importlib
import importlib.util
import json
import logging
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, List

import requests

from DashAI.back.core.enums.plugin_tags import PluginTag

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry

if sys.version_info < (3, 10):
    from importlib_metadata import distributions, entry_points
else:
    from importlib.metadata import distributions, entry_points

logger = logging.getLogger(__name__)

PLUGINS_ENTRY_POINT_GROUP = "dashai.plugins"

_PYPI_SIMPLE_JSON_ACCEPT = "application/vnd.pypi.simple.v1+json"
_PYPI_SIMPLE_URL = "https://pypi.org/simple/"
_REQUEST_TIMEOUT_SECONDS = 15

# Author metadata that identifies a plugin as published by the official
# DashAI account (PyPI user "dashai.nocode"). PyPI does not expose the
# uploader account through its API, so verification is approximated by
# matching the package's declared author metadata.
_VERIFIED_AUTHOR_EMAIL = "dashaisoftware@gmail.com"
_VERIFIED_AUTHOR_NAME = "dashai team"


def _is_verified_author(author: str, author_email: str) -> bool:
    """Check whether a plugin's author metadata matches the official DashAI
    account.

    Parameters
    ----------
    author : str
        The author name declared in the package metadata.
    author_email : str
        The author email declared in the package metadata. PyPI may format
        this as a bare address or as "Name <address>".

    Returns
    -------
    bool
        True if the metadata matches the official DashAI author, else False.
    """
    email = (author_email or "").lower()
    name = (author or "").lower()
    return _VERIFIED_AUTHOR_EMAIL in email or name == _VERIFIED_AUTHOR_NAME


def _get_pypi_project_status(plugin_name: str) -> str:
    """
    Retrieve PyPI project status marker using the Simple API project endpoint.

    Returns
    -------
    str
        One of: "active", "archived", "quarantined" (or other future values).
        Defaults to "active" on missing marker.
        Returns "unknown" on request/parse errors.
    """
    try:
        response = requests.get(
            f"{_PYPI_SIMPLE_URL}{plugin_name}/",
            headers={"Accept": _PYPI_SIMPLE_JSON_ACCEPT},
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        project_status = data.get("project-status") or {}
        return (project_status.get("status") or "active").lower()
    except Exception:
        return "unknown"


def _get_all_plugins() -> List[str]:
    """
    Make a request to PyPI server to get all package names.

    Returns
    ----------
    List[str]
        A list with the names of all PyPI packages
    """

    # Define the URL for PyPI Simple API
    url = "https://pypi.org/simple/"

    # Set the appropriate headers to request JSON format
    headers = {"Accept": "application/vnd.pypi.simple.v1+json"}

    # Send a GET request to the API
    response = requests.get(url, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS)

    # Check for a successful response
    if response.status_code == 200:
        data = response.json()
        projects = data.get("projects", [])
        packages = [project["name"] for project in projects]

    else:
        print(f"Failed to retrieve packages. Status code: {response.status_code}")
        packages = []

    return packages


def get_plugin_by_name_from_pypi(plugin_name: str) -> dict:
    """
    Get a plugin json data from PyPI by its name.

    Parameters
    ----------
    plugin_name : str
        The name of the plugin to get from PyPI

    Returns
    -------
    dict
        A dictionary with the plugin data

    Raises
    ------
    ValueError
        When the plugin is not found or the response is invalid
    """
    response: requests.Response = requests.get(
        f"https://pypi.org/pypi/{plugin_name}/json",
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )

    response_data = response.json()
    try:
        raw_plugin: json = response_data["info"]
    except KeyError as err:
        raise ValueError(
            f"No se pudo obtener la información del plugin '{plugin_name}'."
            f"Respuesta del servidor: {str(response_data)}."
        ) from err

    try:
        keywords: list = raw_plugin.pop("keywords", "").split(",")
        keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
    except AttributeError:
        keywords = []

    # remove keywords that are not tags
    posible_tags = [tag.value for tag in PluginTag]
    keywords = [keyword for keyword in keywords if keyword in posible_tags]

    raw_plugin["tags"] = [{"name": keyword} for keyword in keywords]

    raw_plugin["verified"] = _is_verified_author(
        raw_plugin.get("author"), raw_plugin.get("author_email")
    )

    if raw_plugin["author"] is None or raw_plugin["author"] == "":
        raw_plugin["author"] = "Unknown author"

    raw_plugin["installed_version"] = raw_plugin["version"]
    raw_plugin["lastest_version"] = raw_plugin["version"]

    del raw_plugin["version"]

    return raw_plugin


def get_plugins_from_pypi() -> List[dict]:
    """
    Get all DashAI plugins from PyPI.

    Returns
    -------
    List[dict]
        A list with the information of all DashAI plugins, extracted from PyPI.
    """
    plugins = []
    plugins_names = [
        plugin_name.lower()
        for plugin_name in _get_all_plugins()
        if plugin_name.lower().startswith("dashai") and plugin_name.lower() != "dashai"
    ]

    for plugin_name in plugins_names:
        try:
            status = _get_pypi_project_status(plugin_name)
            if status == "archived":
                continue

            plugin_info = get_plugin_by_name_from_pypi(plugin_name)
            plugins.append(plugin_info)
        except (ValueError, requests.RequestException) as e:
            print(f"Error al obtener información del plugin {plugin_name}: {str(e)}")
            continue

    return plugins


def _load_entry_points(entry_points_list: List) -> List[type]:
    """
    Resolve entry points into their component classes

    An entry point is skipped and logged when its import fails, for example
    because the plugin declares a dependency that is not installed, and also
    when what it points at is not a class. Skipping keeps one damaged plugin
    from hiding the rest.

    Parameters
    ----------
    entry_points_list : List
        Entry points to resolve.

    Returns
    -------
    List[type]
        Component classes that were resolved without error.
    """
    components: List[type] = []
    for entry_point in entry_points_list:
        try:
            component = entry_point.load()
        except Exception:
            logger.exception(
                "Plugin entry point '%s' (%s) could not be loaded and was skipped.",
                entry_point.name,
                getattr(entry_point, "value", "unknown target"),
            )
            continue

        if not isinstance(component, type):
            logger.error(
                "Plugin entry point '%s' (%s) does not point to a class and was "
                "skipped.",
                entry_point.name,
                getattr(entry_point, "value", "unknown target"),
            )
            continue

        components.append(component)

    return components


def get_available_plugins() -> List[type]:
    """
    Get available DashAI plugins entrypoints

    Returns
    ----------
    List[type]
        A list of plugins' classes
    """
    # importlib keeps directory caches in its finders, so a plugin installed
    # after this process started stays invisible until they are dropped.
    importlib.invalidate_caches()

    # Retrieve plugins groups (DashAI components)
    plugins = entry_points(group=PLUGINS_ENTRY_POINT_GROUP)

    return _load_entry_points(list(plugins))


def _get_distribution_plugins(distribution_name: str) -> List[type]:
    """
    Get the DashAI components that one installed distribution declares

    Parameters
    ----------
    distribution_name : str
        Name of the plugin distribution in PyPI.

    Returns
    -------
    List[type]
        Component classes declared by that distribution under the
        ``dashai.plugins`` group. The list is empty when the distribution is
        not installed for the interpreter in use.
    """
    importlib.invalidate_caches()

    normalized_name = distribution_name.lower().replace("-", "_")
    matching_entry_points = []
    for distribution in distributions():
        name = distribution.metadata["Name"] or ""
        if name.lower().replace("-", "_") != normalized_name:
            continue
        matching_entry_points.extend(
            distribution.entry_points.select(group=PLUGINS_ENTRY_POINT_GROUP)
        )

    return _load_entry_points(matching_entry_points)


def _build_pip_args(pypi_plugin_name: str, pip_action: str) -> List[str]:
    """
    Build the package manager command aimed at the interpreter in use

    PATH decides which ``pip`` a bare call reaches, and that pip may belong to
    another Python installation. The plugin then lands somewhere dashAI cannot
    import from while pip still exits 0, so the command always goes through
    ``sys.executable``.

    uv creates environments that contain no pip. uv itself covers that case,
    pointed at the right interpreter through ``--python``.

    Parameters
    ----------
    pypi_plugin_name : str
        Name of the plugin in PyPI.
    pip_action : str
        Either "install" or "uninstall".

    Returns
    -------
    List[str]
        Command to run, argument by argument.

    Raises
    ------
    RuntimeError
        When the interpreter in use has access to neither pip nor uv.
    """
    if getattr(sys, "frozen", False):
        # sys.executable is the app itself inside a bundled launcher, where
        # "-m pip" would start dashAI again rather than pip.
        args = ["pip", pip_action]
        args += ["-y"] if pip_action == "uninstall" else ["--no-cache-dir"]
        return [*args, pypi_plugin_name]

    if importlib.util.find_spec("pip") is not None:
        args = [sys.executable, "-m", "pip", pip_action]
        args += ["-y"] if pip_action == "uninstall" else ["--no-cache-dir"]
        return [*args, pypi_plugin_name]

    uv_executable = shutil.which("uv")
    if uv_executable is not None:
        args = [uv_executable, "pip", pip_action, "--python", sys.executable]
        if pip_action == "install":
            args.append("--no-cache")
        return [*args, pypi_plugin_name]

    raise RuntimeError(
        "Neither pip nor uv is available for the interpreter running dashAI "
        f"({sys.executable}), so plugins cannot be installed. Install pip in "
        "that environment (python -m ensurepip --upgrade) or make uv reachable "
        "on the PATH."
    )


def execute_pip_command(pypi_plugin_name: str, pip_action: str) -> int:
    """
    Execute a pip command to install or uninstall a plugin

    Parameters
    ----------
    pypi_plugin_name : str
        A string with the name of the plugin in pypi to install or uninstall

    pip_action : str
        A string with the action to perform. It can be "install" or "uninstall"

    Returns
    ----------
    int
        The return code of the pip command

    Raises
    ----------
    ValueError
        If the pip action is not supported
    RuntimeError
        If the pip command returns an error
    """
    if pip_action not in ["install", "uninstall"]:
        raise ValueError(f"Pip action {pip_action} not supported")

    args = _build_pip_args(pypi_plugin_name, pip_action)
    res = subprocess.run(
        args,
        stderr=subprocess.PIPE,
        text=True,
    )

    if res.returncode != 0:
        stderr = res.stderr or ""
        errors = [line for line in stderr.split("\n") if "ERROR" in line]
        # Failures from uv, or a missing pip module, print no ERROR marker at
        # all. Use the raw output there so the message is not empty.
        error_string = "\n".join(errors) if errors else stderr.strip()
        raise RuntimeError(
            error_string or f"'{' '.join(args)}' failed with code {res.returncode}"
        )

    return res.returncode


def install_plugin(plugin_name: str) -> List[type]:
    """
    Install a plugin and return the components it brings in

    Parameters
    ----------
    plugin_name : str
        A string with the name of the plugin in pypi to install

    Returns
    -------
    List[type]
        Component classes that the installed distribution declares.

    Raises
    ------
    RuntimeError
        When pip succeeded yet no dashAI component turned up, meaning the
        distribution went somewhere other than where dashAI runs, or its
        ``dashai.plugins`` entry point is unusable.
    """
    pre_installed_plugins: List[type] = get_available_plugins()
    execute_pip_command(plugin_name, "install")

    installed_plugins = _get_distribution_plugins(plugin_name)
    if not installed_plugins:
        # The PyPI name and the metadata name of what gets installed are not
        # always equal, so compare entry points before and after instead.
        installed_plugins = [
            plugin
            for plugin in get_available_plugins()
            if plugin not in pre_installed_plugins
        ]

    if not installed_plugins:
        raise RuntimeError(
            f"The plugin '{plugin_name}' was installed but no dashAI component "
            f"could be loaded from it. Check that it is installed for the "
            f"interpreter running dashAI ({sys.executable}), that it declares a "
            f"'{PLUGINS_ENTRY_POINT_GROUP}' entry point, and that its "
            f"dependencies are importable."
        )

    return installed_plugins


def register_plugin_components(
    plugins: List[type], component_registry: "ComponentRegistry"
):
    """
    Register the plugins in the component registry

    Whatever the registry rejects, a class that extends no dashAI base for
    instance, is logged and left out. The other components of that same plugin
    still make it into the registry.

    Parameters
    ----------
    plugins : List[type]
        A list of plugins' classes wanted to be registered in the component
        registry
    component_registry : ComponentRegistry
        The current app component registry
    """
    for plugin in plugins:
        try:
            component_registry.register_component(plugin)
        except Exception:
            logger.exception(
                "Plugin component '%s' could not be registered and was skipped.",
                getattr(plugin, "__name__", plugin),
            )


def uninstall_plugin(
    plugin_name: str,
) -> List[type]:
    """
    Uninstall an existing plugin and delete it from component registry

    Parameters
    ----------
    plugin_name : str
        A string with the name of the plugin in pypi to install

    component_registry : ComponentRegistry
        The current app component registry

    """
    available_plugins: List[type] = get_available_plugins()
    execute_pip_command(plugin_name, "uninstall")
    uninstalled_components: List[type] = set(available_plugins) - set(
        get_available_plugins()
    )
    return uninstalled_components


def unregister_plugin_components(
    plugins: List[type],
    component_registry: "ComponentRegistry",
) -> List[type]:
    """
    Remove from component registry uninstalled plugins

    Parameters
    ----------
    plugins : List[type]
        A list of plugins' classes wanted to be removed from the component registry

    component_registry : ComponentRegistry
        The current app component registry

    Returns
    ----------
    List[type]
        A list of plugins' classes wanted to be removed from the component registry
    """
    for plugin in plugins:
        component_registry.unregister_component(plugin)
    return list(plugins)
