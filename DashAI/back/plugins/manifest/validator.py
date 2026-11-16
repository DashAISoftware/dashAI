import ast
import functools
import importlib.metadata
import os
from dataclasses import dataclass, field
from pathlib import Path

from beartype import beartype
from beartype.typing import Dict, List, Optional, Tuple
from packaging.version import Version

from DashAI.back.plugins.errors import PluginError
from DashAI.back.plugins.loader import import_root, own_modules
from DashAI.back.plugins.manifest.manifest import ManifestError, PluginManifest

ALLOWED_COMPONENT_TYPES = frozenset(
    {
        "Model",
        "Converter",
        "Metric",
        "Task",
        "DataLoader",
        "Explorer",
        "GlobalExplainer",
        "LocalExplainer",
        "GenerativeModel",
        "GenerativeTask",
    }
)


@dataclass
class ValidationResult:
    errors: List[PluginError] = field(default_factory=list)
    ref: Optional[str] = None  # GitHub tag, None for local
    id: Optional[str] = None
    version: Optional[str] = None
    name: Optional[str] = None
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    # Transitive plugin dependencies in install order, with their state
    plugin_dependencies: List[Dict[str, Optional[str]]] = field(default_factory=list)
    breaks: List[str] = field(default_factory=list)
    authors: List[Dict[str, str]] = field(default_factory=list)
    project_urls: Dict[str, str] = field(default_factory=dict)
    readme: Optional[str] = None
    installed_version: Optional[str] = None  # None if it is a new install
    # "newer", "same" or "older" than the installed one, None if not installed.
    version_change: Optional[str] = None
    installed_location: Optional[str] = None  # where the installed one came from
    trust_level: Optional[str] = None
    # Asks "I understand the risk" (sources.needs_ack), also if not decided.
    needs_ack: bool = True
    sha256: Optional[str] = None  # of what was reviewed, None for a folder
    verified: bool = False
    removed: Optional[str] = None  # its RemovedEntry.type if the store retired it
    owner: Optional[str] = None  # who publishes it (its source's), None for local
    in_store: bool = False  # the store lists this id from this same origin
    # It replaces an installed plugin with its id from another origin.
    replaces_other: bool = False
    # Token of the copy kept to install it (previews.py), None if invalid.
    preview: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _resolve_module_file(root: Path, module_path: str) -> Path | None:
    base = root / Path(*module_path.split("."))
    # A package wins over a module of the same name, as when Python imports it.
    for candidate in (base / "__init__.py", base.with_suffix(".py")):
        if candidate.is_file():
            return candidate
    return None


def _module_level(nodes):
    """Statements run on import: also inside if/try/with, not inside a def."""
    for node in nodes:
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _module_level(
                child
                for child in ast.iter_child_nodes(node)
                if isinstance(child, (ast.stmt, ast.excepthandler))
            )


def _bound_names(tree: ast.Module) -> set:
    """Names a module defines on import (classes, imports, assignments)."""
    names = set()
    for node in _module_level(tree.body):
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(a.asname or a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _relative(target: str, package: str) -> str:
    """``target`` relative to ``package``, e.g. ``..utils`` from ``mypkg.sub``."""
    t = target.split(".") if target else []
    p = package.split(".") if package else []
    common = len(os.path.commonprefix([t, p]))
    return "." * (len(p) - common + 1) + ".".join(t[common:])


def _imports(tree: ast.Module, package: str):
    """Each module ``package`` imports, absolute, with its relative form or None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                parent, _, last = a.name.rpartition(".")
                alias = f" as {a.asname}" if a.asname else ""
                yield a.name, f"from {_relative(parent, package)} import {last}{alias}"
        elif isinstance(node, ast.ImportFrom):
            base = package.split(".") if package else []
            if node.level - 1 > len(base):
                continue  # above the plugin's root
            if node.level:
                base = base[: len(base) - node.level + 1]
                module, relative = ".".join([*base, *filter(None, [node.module])]), None
            else:
                names = ", ".join(
                    a.name + (f" as {a.asname}" if a.asname else "") for a in node.names
                )
                module = node.module
                relative = f"from {_relative(module, package)} import {names}"
            if module:
                yield module, relative
            for a in node.names:
                yield f"{module}.{a.name}".lstrip("."), None


def _check_modules(root: Path, modules: Dict[str, List[str]]) -> List[PluginError]:
    """Check ``module:Class`` and absolute imports of the plugin's own modules."""
    own = own_modules(root)
    errors: List[PluginError] = []
    pending, seen, reported = list(modules), set(), set()
    while pending:
        module = pending.pop(0)
        if module in seen:
            continue
        seen.add(module)
        class_names = modules.get(module, [])
        module_file = _resolve_module_file(root, module)
        if module_file is None:
            errors.extend(
                PluginError(
                    "module_not_found",
                    f"Module '{module}' not found for component '{class_name}'",
                    {"module": module, "component": class_name},
                )
                for class_name in class_names
            )
            continue
        try:
            # Bytes, like Python reads a module, for BOM and coding declarations.
            tree = ast.parse(module_file.read_bytes())
        except (SyntaxError, ValueError) as error:
            if class_names:  # another module, loading it reports it
                errors.append(
                    PluginError(
                        "syntax_error",
                        f"Syntax error in {module}: {error}",
                        {"module": module, "line": getattr(error, "lineno", None)},
                    )
                )
            continue
        if class_names:
            bound = _bound_names(tree)
            errors.extend(
                PluginError(
                    "class_not_defined",
                    f"Class '{class_name}' not defined in {module}",
                    {"class": class_name, "module": module},
                )
                for class_name in class_names
                if class_name not in bound
            )
        parts = module.split(".")
        # Importing a module also runs the __init__ of each package it is in.
        pending += [".".join(parts[:n]) for n in range(1, len(parts))]
        package = module if module_file.name == "__init__.py" else ".".join(parts[:-1])
        for name, relative in _imports(tree, package):
            if name.partition(".")[0] not in own:
                continue  # a third-party import
            pending.append(name)
            if relative and (module, name) not in reported:
                reported.add((module, name))
                errors.append(
                    PluginError(
                        "absolute_own_import",
                        f"{module} imports its own module '{name}' absolutely; "
                        f"use a relative import: '{relative}'",
                        {"module": module, "name": name, "suggestion": relative},
                    )
                )
    return errors


@functools.cache
def _app_version() -> str:
    """dashAI's version, cached as the store asks it per plugin (~3 ms each)."""
    return importlib.metadata.version("dashAI")


class PluginValidator:
    @staticmethod
    @beartype
    def check_app_version(min_app_version: str, app_version=None) -> str | None:
        if app_version is None:
            app_version = _app_version()
        if Version(app_version) < Version(min_app_version):
            return f"needs dashAI {min_app_version} or newer (this is {app_version})"

    @classmethod
    @beartype
    def validate(
        cls, path: str | Path
    ) -> Tuple[Optional[PluginManifest], ValidationResult]:
        """The manifest (None if unreadable) and its problems, without running it."""
        try:
            manifest = PluginManifest.from_file(Path(path) / "manifest.json")
        except FileNotFoundError:
            return None, ValidationResult(
                errors=[PluginError("manifest_not_found", "manifest.json not found")]
            )
        except ManifestError as error:
            return None, ValidationResult(
                errors=[
                    PluginError(error.code, f"Invalid manifest: {error}", error.params)
                ]
            )

        errors: List[PluginError] = []
        too_old = cls.check_app_version(manifest.min_app_version)
        if too_old is not None:
            errors.append(
                PluginError(
                    "needs_newer_dashai",
                    too_old,
                    {"required": manifest.min_app_version, "current": _app_version()},
                )
            )
        errors.extend(
            PluginError(
                "type_not_allowed",
                f"Component type '{c.type}' is not allowed ({c.class_ref})",
                {"component": c.name, "type": c.type},
            )
            for c in manifest.components
            if c.type not in ALLOWED_COMPONENT_TYPES
        )
        modules: Dict[str, List[str]] = {}
        refs = [c.class_ref for c in manifest.components]
        if manifest.settings is not None:
            refs.append(manifest.settings)
        for ref in refs:
            module_path, _, class_name = ref.rpartition(":")
            modules.setdefault(module_path, []).append(class_name)
        errors.extend(_check_modules(import_root(Path(path)), modules))

        return manifest, ValidationResult(errors=errors)
