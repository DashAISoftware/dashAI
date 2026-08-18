"""Install and remove plugin distributions in the dashAI plugins directory.

Everything here drives pip through ``sys.executable -m pip`` instead of a bare
``pip`` executable: a uv managed ``.venv`` has no ``pip`` script at all, and in
a frozen build a ``pip`` found on ``PATH`` belongs to some unrelated
interpreter, so the plugin would be installed where dashAI can never import it.

pip's ``--target`` mode always forces ``--ignore-installed``, so installing a
plugin directly into the plugins directory would re-download its whole
dependency tree, torch included. Installation is therefore split in two phases:

1. resolve the requirement against the running environment with
   ``pip install --dry-run --report``, which reports only the distributions
   that are actually missing;
2. install exactly those, pinned to the artifact URLs the resolver picked, with
   ``--target <plugins dir> --no-deps``.

``pip uninstall`` refuses to work on a ``--target`` directory, so removal walks
the ``RECORD`` file of every distribution the plugin brought in and that no
other installed plugin still needs.
"""

import importlib
import importlib.util
import json
import logging
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional

from DashAI.back.plugins.environment import (
    activate_plugins_directory,
    get_plugins_directory,
)

logger = logging.getLogger(__name__)

LEDGER_FILENAME = ".dashai-plugins.json"
LEDGER_VERSION = 1
_PIP_TIMEOUT_SECONDS = 60 * 60


class PluginInstallError(RuntimeError):
    """Raised when a plugin distribution cannot be installed or removed."""


def canonical_name(name: str) -> str:
    """Normalize a distribution name as defined by the packaging specs.

    Parameters
    ----------
    name : str
        Raw distribution or requirement name.

    Returns
    -------
    str
        The lowercase, dash separated canonical form.
    """
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def pip_command() -> List[str]:
    """Build the argv prefix that runs pip for the interpreter hosting dashAI.

    Returns
    -------
    List[str]
        The ``[sys.executable, "-m", "pip"]`` prefix. In a frozen build
        ``sys.executable`` is the dashAI launcher, which the bundled runtime
        hook makes behave like ``python -m ...``.

    Raises
    ------
    PluginInstallError
        If pip is not importable from the current interpreter, in which case
        there is no way to reach the environment dashAI itself runs from.
    """
    if importlib.util.find_spec("pip") is None:
        raise PluginInstallError(
            "pip is not available in the environment running dashAI, so plugins "
            "cannot be installed. Install it with 'uv pip install pip' (or "
            "'python -m ensurepip') and try again."
        )
    return [sys.executable, "-m", "pip"]


def _pip_environment(directory: pathlib.Path) -> Dict[str, str]:
    """Build the environment used for pip subprocesses.

    The plugins directory is exported through ``PYTHONPATH`` so pip counts
    distributions installed by earlier plugins as already satisfied, and the
    user level pip switches that are incompatible with ``--target`` are
    neutralized.

    Parameters
    ----------
    directory : pathlib.Path
        The plugins directory.

    Returns
    -------
    Dict[str, str]
        The environment to hand to :func:`subprocess.run`.
    """
    environment = os.environ.copy()
    entries = [
        entry for entry in environment.get("PYTHONPATH", "").split(os.pathsep) if entry
    ]
    path = str(directory)
    if path not in entries:
        entries.insert(0, path)
    environment["PYTHONPATH"] = os.pathsep.join(entries)
    # --target is rejected together with --user, and pip refuses to install at
    # all when the user has PIP_REQUIRE_VIRTUALENV set while dashAI runs from a
    # bundle, where sys.prefix is not a virtual environment.
    environment["PIP_USER"] = "0"
    environment["PIP_REQUIRE_VIRTUALENV"] = "0"
    environment.pop("PIP_TARGET", None)
    return environment


def _format_pip_error(result: subprocess.CompletedProcess) -> str:
    """Extract a readable error message from a failed pip run.

    Parameters
    ----------
    result : subprocess.CompletedProcess
        The finished pip process.

    Returns
    -------
    str
        The ``ERROR`` lines pip printed, or the tail of its output when pip
        failed without printing any.
    """
    output = f"{result.stdout or ''}\n{result.stderr or ''}"
    errors = [line for line in output.splitlines() if "ERROR" in line]
    if errors:
        return "\n".join(errors)
    tail = "\n".join(output.splitlines()[-10:]).strip()
    return tail or f"pip exited with code {result.returncode}"


def _run_pip(
    arguments: List[str], directory: pathlib.Path
) -> subprocess.CompletedProcess:
    """Run a pip subcommand and raise on failure.

    Parameters
    ----------
    arguments : List[str]
        Arguments appended to the pip argv prefix.
    directory : pathlib.Path
        The plugins directory, used to build the subprocess environment.

    Returns
    -------
    subprocess.CompletedProcess
        The finished process.

    Raises
    ------
    PluginInstallError
        If pip exits with a non zero status.
    """
    command = [*pip_command(), *arguments]
    logger.debug("Running pip: %s", " ".join(command))
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_pip_environment(directory),
        timeout=_PIP_TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode != 0:
        raise PluginInstallError(_format_pip_error(result))
    return result


def resolve_missing_distributions(
    requirement: str, directory: pathlib.Path
) -> List[Dict[str, str]]:
    """Resolve a requirement against the environment dashAI runs in.

    Parameters
    ----------
    requirement : str
        The plugin requirement, usually a plain PyPI project name.
    directory : pathlib.Path
        The plugins directory.

    Returns
    -------
    List[Dict[str, str]]
        One ``{"name", "version", "url"}`` entry per distribution that is not
        importable yet. Empty when the requirement is already satisfied.

    Raises
    ------
    PluginInstallError
        If pip fails, or writes a report that cannot be parsed.
    """
    with tempfile.TemporaryDirectory() as workdir:
        report_path = pathlib.Path(workdir) / "report.json"
        _run_pip(
            [
                "install",
                "--dry-run",
                "--quiet",
                "--disable-pip-version-check",
                "--report",
                str(report_path),
                requirement,
            ],
            directory,
        )
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise PluginInstallError(
                f"Could not read the pip resolution report for '{requirement}'."
            ) from error

    distributions = []
    for entry in report.get("install", []):
        metadata = entry.get("metadata") or {}
        url = (entry.get("download_info") or {}).get("url")
        if not metadata.get("name") or not url:
            continue
        distributions.append(
            {
                "name": canonical_name(metadata["name"]),
                "version": metadata.get("version", ""),
                "url": url,
            }
        )
    return distributions


def read_ledger(directory: pathlib.Path) -> Dict[str, List[str]]:
    """Read the record of which distributions each plugin brought in.

    Parameters
    ----------
    directory : pathlib.Path
        The plugins directory.

    Returns
    -------
    Dict[str, List[str]]
        Canonical plugin name to the canonical names of the distributions it
        owns. Empty when the ledger is missing or unreadable.
    """
    path = directory / LEDGER_FILENAME
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    plugins = content.get("plugins")
    if not isinstance(plugins, dict):
        return {}
    return {
        canonical_name(name): list(distributions)
        for name, distributions in plugins.items()
    }


def _write_ledger(directory: pathlib.Path, ledger: Dict[str, List[str]]) -> None:
    """Persist the plugin ownership record.

    Parameters
    ----------
    directory : pathlib.Path
        The plugins directory.
    ledger : Dict[str, List[str]]
        Canonical plugin name to the canonical names of the distributions it
        owns.
    """
    path = directory / LEDGER_FILENAME
    payload = {"version": LEDGER_VERSION, "plugins": ledger}
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        logger.exception("Could not write the plugins ledger at %s", path)


def install_requirement(
    requirement: str, local_path: Optional[os.PathLike] = None
) -> List[str]:
    """Install a plugin and its missing dependencies in the plugins directory.

    Parameters
    ----------
    requirement : str
        The plugin requirement, usually a plain PyPI project name.
    local_path : Optional[os.PathLike]
        Base dashAI data directory, forwarded to the plugins directory
        resolution.

    Returns
    -------
    List[str]
        Canonical names of the distributions that were installed. Empty when
        the requirement was already satisfied.

    Raises
    ------
    PluginInstallError
        If pip fails in either phase.
    """
    directory = activate_plugins_directory(local_path)
    distributions = resolve_missing_distributions(requirement, directory)
    if not distributions:
        logger.info("Plugin '%s' is already satisfied, nothing to install", requirement)
        return []

    _run_pip(
        [
            "install",
            "--no-cache-dir",
            "--disable-pip-version-check",
            "--no-deps",
            "--upgrade",
            "--target",
            str(directory),
            *[distribution["url"] for distribution in distributions],
        ],
        directory,
    )

    names = [distribution["name"] for distribution in distributions]
    ledger = read_ledger(directory)
    ledger[canonical_name(requirement)] = names
    _write_ledger(directory, ledger)

    importlib.invalidate_caches()
    logger.info("Installed plugin '%s' with distributions %s", requirement, names)
    return names


def _find_distribution_directory(
    directory: pathlib.Path, distribution: str
) -> Optional[pathlib.Path]:
    """Locate the ``.dist-info`` directory of an installed distribution.

    Parameters
    ----------
    directory : pathlib.Path
        The plugins directory.
    distribution : str
        Canonical distribution name.

    Returns
    -------
    Optional[pathlib.Path]
        The ``.dist-info`` path, or None when the distribution is not installed
        in the plugins directory.
    """
    for candidate in directory.glob("*.dist-info"):
        name = candidate.name[: -len(".dist-info")].rsplit("-", 1)[0]
        if canonical_name(name) == distribution:
            return candidate
    return None


def _prune_empty_directories(root: pathlib.Path, leaf: pathlib.Path) -> None:
    """Delete leftover empty directories under the plugins directory.

    Parameters
    ----------
    root : pathlib.Path
        Resolved plugins directory, which is never removed.
    leaf : pathlib.Path
        Directory a removed file used to live in.
    """
    cache = leaf / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)

    candidate = leaf
    while candidate != root and root in candidate.parents:
        if not candidate.is_dir() or any(candidate.iterdir()):
            return
        candidate.rmdir()
        candidate = candidate.parent


def _resolve_record_entry(
    directory: pathlib.Path, relative: str
) -> Optional[pathlib.Path]:
    """Map a ``RECORD`` entry onto its location in the plugins directory.

    Wheels record scripts and data files relative to the environment root, as
    in ``../../bin/plugin-cli.exe``. A ``--target`` install puts those inside
    the target directory instead, so the parent references are dropped before
    resolving.

    Parameters
    ----------
    directory : pathlib.Path
        The plugins directory.
    relative : str
        The path as written in ``RECORD``.

    Returns
    -------
    Optional[pathlib.Path]
        The absolute path to delete, or None when the entry cannot be placed
        inside the plugins directory.
    """
    parts = [
        part
        for part in pathlib.PurePosixPath(relative.replace("\\", "/")).parts
        if part not in ("..", ".", "")
    ]
    if not parts:
        return None
    target = directory.joinpath(*parts).resolve()
    if directory.resolve() not in target.parents:
        return None
    return target


def _remove_distribution(directory: pathlib.Path, distribution: str) -> bool:
    """Delete every file a distribution installed in the plugins directory.

    Parameters
    ----------
    directory : pathlib.Path
        The plugins directory.
    distribution : str
        Canonical distribution name.

    Returns
    -------
    bool
        True when the distribution was found in the plugins directory and
        removed, False when it is not installed there.
    """
    dist_info = _find_distribution_directory(directory, distribution)
    if dist_info is None:
        return False

    root = directory.resolve()
    touched_directories = set()
    record = dist_info / "RECORD"
    if record.exists():
        for line in record.read_text(encoding="utf-8").splitlines():
            relative = line.split(",", 1)[0].strip()
            if not relative:
                continue
            target = _resolve_record_entry(directory, relative)
            if target is None:
                continue
            touched_directories.add(target.parent)
            try:
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not delete %s", target)

    shutil.rmtree(dist_info, ignore_errors=True)

    for leaf in sorted(touched_directories, key=lambda path: len(path.parts))[::-1]:
        _prune_empty_directories(root, leaf)
    return True


def _uninstall_from_environment(requirement: str, directory: pathlib.Path) -> None:
    """Remove a legacy plugin installed in the interpreter's environment.

    Parameters
    ----------
    requirement : str
        The plugin requirement to remove.
    directory : pathlib.Path
        The plugins directory, used to build the subprocess environment.
    """
    try:
        _run_pip(
            ["uninstall", "-y", "--disable-pip-version-check", requirement],
            directory,
        )
    except PluginInstallError:
        logger.warning(
            "Plugin '%s' was not found in the dashAI plugins directory and could "
            "not be removed from the environment either.",
            requirement,
        )


def uninstall_requirement(
    requirement: str, local_path: Optional[os.PathLike] = None
) -> List[str]:
    """Remove a plugin and the dependencies no other plugin needs.

    Parameters
    ----------
    requirement : str
        The plugin requirement, usually a plain PyPI project name.
    local_path : Optional[os.PathLike]
        Base dashAI data directory, forwarded to the plugins directory
        resolution.

    Returns
    -------
    List[str]
        Canonical names of the distributions that were removed.
    """
    directory = activate_plugins_directory(local_path)
    plugin = canonical_name(requirement)
    ledger = read_ledger(directory)
    owned = ledger.pop(plugin, [plugin])
    still_needed = {
        distribution
        for distributions in ledger.values()
        for distribution in distributions
    }

    removed = []
    for distribution in owned:
        if distribution in still_needed:
            continue
        if _remove_distribution(directory, distribution):
            removed.append(distribution)

    if not removed:
        # Plugins installed before dashAI moved to a per user plugins directory
        # still live in the environment's site-packages.
        _uninstall_from_environment(requirement, directory)

    _write_ledger(directory, ledger)
    importlib.invalidate_caches()
    logger.info("Uninstalled plugin '%s', removed distributions %s", plugin, removed)
    return removed


def get_installed_plugins_directory(
    local_path: Optional[os.PathLike] = None,
) -> pathlib.Path:
    """Return the plugins directory without creating or activating it.

    Parameters
    ----------
    local_path : Optional[os.PathLike]
        Base dashAI data directory.

    Returns
    -------
    pathlib.Path
        The version scoped plugins directory.
    """
    return get_plugins_directory(local_path)
