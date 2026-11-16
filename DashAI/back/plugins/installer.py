"""Run pip as ``<interpreter> -m pip``, never a ``pip`` from ``PATH``."""

import functools
import importlib.util
import logging
import os
import pathlib
import subprocess
import sys
from typing import Dict, List

from DashAI.back.plugins.errors import CodedError

logger = logging.getLogger(__name__)

PIP_TIMEOUT_SECONDS = 60 * 60
_PYTHON_PROBE_TIMEOUT_SECONDS = 60
_PYTHON_PROBE_MARKER = "dashai-interpreter-probe"


class PluginInstallError(CodedError):
    """pip cannot be run for the environment hosting dashAI."""

    code = "pip_unavailable"


def _looks_like_python(candidate: str) -> bool:
    """A Python interpreter, not the dashAI launcher."""
    try:
        result = subprocess.run(
            [candidate, "-c", f"print('{_PYTHON_PROBE_MARKER}')"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=_PYTHON_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and _PYTHON_PROBE_MARKER in (result.stdout or "")


def _interpreter_candidates() -> List[str]:
    """dashAI's interpreters, best first, ``sys.executable`` unless an AppImage."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    prefixed = []
    for prefix in (sys.prefix, sys.base_prefix):
        if os.name == "nt":
            prefixed.append(os.path.join(prefix, "python.exe"))
            prefixed.append(os.path.join(prefix, "Scripts", "python.exe"))
        else:
            prefixed.append(os.path.join(prefix, "bin", f"python{version}"))
            prefixed.append(os.path.join(prefix, "bin", "python3"))

    in_appimage = bool(os.environ.get("APPIMAGE") or os.environ.get("APPDIR"))
    ordered = (
        [*prefixed, sys.executable] if in_appimage else [sys.executable, *prefixed]
    )
    ordered.append(getattr(sys, "_base_executable", "") or "")
    return [candidate for candidate in dict.fromkeys(ordered) if candidate]


@functools.lru_cache(maxsize=1)
def python_executable() -> str:
    """The interpreter for pip, in a bundle its launcher (a hook answers ``-m pip``)."""
    if getattr(sys, "frozen", False):
        return sys.executable

    for candidate in _interpreter_candidates():
        if _looks_like_python(candidate):
            logger.debug("Using %s to run pip", candidate)
            return candidate

    raise PluginInstallError(
        "Could not find the Python interpreter of the environment running "
        f"dashAI, so plugins cannot be installed. Candidates tried: "
        f"{', '.join(_interpreter_candidates())}."
    )


def pip_command() -> List[str]:
    """``[<interpreter>, "-m", "pip"]``."""
    if importlib.util.find_spec("pip") is None:
        raise PluginInstallError(
            "pip is not available in the environment running dashAI, so plugins "
            "cannot be installed. Install it with 'uv pip install pip' (or "
            "'python -m ensurepip') and try again."
        )
    return [python_executable(), "-m", "pip"]


def pip_environment(directory: pathlib.Path) -> Dict[str, str]:
    """pip's env, with ``directory`` on ``PYTHONPATH`` so earlier installs count."""
    environment = os.environ.copy()
    entries = [
        entry for entry in environment.get("PYTHONPATH", "").split(os.pathsep) if entry
    ]
    path = str(directory)
    if path not in entries:
        entries.insert(0, path)
    environment["PYTHONPATH"] = os.pathsep.join(entries)
    # --target rejects --user, and PIP_REQUIRE_VIRTUALENV refuses a bundle
    environment["PIP_USER"] = "0"
    environment["PIP_REQUIRE_VIRTUALENV"] = "0"
    environment.pop("PIP_TARGET", None)
    return environment
