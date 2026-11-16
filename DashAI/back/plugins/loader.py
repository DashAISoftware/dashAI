import contextlib
import sys
import types
from importlib import import_module
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, FrozenSet, List, Optional, Type

from DashAI.back.dependencies.registry.component_registry import (
    _NAMESPACE,
    ComponentRegistry,
    component_id,
    owner_of,
)
from DashAI.back.plugins.errors import CodedError
from DashAI.back.plugins.manifest.manifest import Component, PluginManifest


class PluginLoadError(CodedError):
    """A component class could not be imported or registered."""

    code = "load_failed"


def _package(plugin_id: str) -> str:
    """The package a plugin's code is imported under (ids have no '_')."""
    return f"{_NAMESPACE}.p" + plugin_id.replace("-", "_")


def import_root(plugin_dir: Path) -> Path:
    """Where a plugin's modules are imported from: ``src/`` if it has one."""
    return plugin_dir / "src" if (plugin_dir / "src").is_dir() else plugin_dir


def own_modules(root: Path) -> FrozenSet[str]:
    """Top-level modules and packages under ``root``, other folders are data."""
    return frozenset(
        path.stem if path.suffix == ".py" else path.name
        for path in root.iterdir()
        if (path.suffix == ".py" and path.is_file())
        or (path.is_dir() and any(path.glob("*.py")))
    )


def _modules(package: str) -> List[str]:
    """Names in ``sys.modules`` of ``package`` and its submodules."""
    return [n for n in list(sys.modules) if n == package or n.startswith(package + ".")]


class PluginLoader:
    @staticmethod
    @beartype
    def _install_namespace(plugin_id: str, plugin_dir: Path) -> Dict[str, Any]:
        """A fresh package for the plugin; returns the modules it replaced."""
        if _NAMESPACE not in sys.modules:
            container = types.ModuleType(_NAMESPACE)
            container.__path__ = []
            sys.modules[_NAMESPACE] = container

        package = _package(plugin_id)
        replaced = {name: sys.modules.pop(name) for name in _modules(package)}

        module = types.ModuleType(package)
        module.__path__ = [str(import_root(plugin_dir))]
        sys.modules[package] = module
        return replaced

    @staticmethod
    @beartype
    def relocate(plugin_id: str, old_dir: Path, new_dir: Path) -> None:
        """Repoint modules loaded from ``old_dir`` to ``new_dir``."""
        old, new = str(import_root(old_dir)), str(import_root(new_dir))
        for name in _modules(_package(plugin_id)):
            module = sys.modules[name]
            if getattr(module, "__file__", None):
                module.__file__ = module.__file__.replace(old, new, 1)
            if hasattr(module, "__path__"):
                module.__path__ = [
                    path.replace(old, new, 1) for path in module.__path__
                ]

    @staticmethod
    @beartype
    def _resolve_class(package: str, class_ref: str) -> Type:
        module_path, _, class_name = class_ref.rpartition(":")
        module_name = f"{package}.{module_path}"
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name and (
                module_name == error.name or module_name.startswith(error.name + ".")
            ):
                raise PluginLoadError(
                    f"Could not import module '{module_path}' for component "
                    f"'{class_name}' (declared as '{class_ref}')"
                ) from error
            # An absolute import of its own code (e.g. via importlib) can't find it
            missing = (error.name or "").partition(".")[0]
            roots = getattr(sys.modules.get(package), "__path__", [])
            if any(
                missing in own_modules(Path(root))
                for root in roots
                if Path(root).is_dir()
            ):
                raise PluginLoadError(
                    f"Module '{module_path}' (or a module it imports) imports the "
                    f"plugin's own module '{missing}' absolutely; imports between "
                    "the plugin's modules must be relative ('from .' or 'from ..')"
                ) from error
            owner = owner_of(error.name or "")
            if owner not in ("dashai", owner_of(package)):
                raise PluginLoadError(
                    f"Module '{module_path}' imports the plugin '{owner}', which "
                    "is not loaded; declare it in plugin_dependencies"
                ) from error
            advice = (
                "which this dashAI version does not have (see min_app_version)"
                if (error.name or "").split(".")[0] == "DashAI"
                else "which is not installed; declare it in the manifest's dependencies"
            )
            raise PluginLoadError(
                f"Module '{module_path}' imports '{error.name}', {advice}"
            ) from error
        except Exception as error:  # noqa: BLE001
            raise PluginLoadError(
                f"Error importing module '{module_path}': "
                f"{type(error).__name__}: {error}"
            ) from error
        try:
            cls = getattr(module, class_name)
        except AttributeError as error:
            raise PluginLoadError(
                f"Module '{module_path}' does not define class '{class_name}' "
                f"(declared as '{class_ref}')"
            ) from error
        return cls

    @staticmethod
    @beartype
    def _verify_type(
        cls: Type, declared_type: str, registry: ComponentRegistry
    ) -> None:
        try:
            actual = registry.get_base_type(cls)
        except TypeError as error:
            raise PluginLoadError(
                f"Could not determine the component type of '{cls.__name__}': {error}"
            ) from error
        if actual != declared_type:
            raise PluginLoadError(
                f"Component '{cls.__name__}' is declared as '{declared_type}' "
                f"but is actually a '{actual}'"
            )

    @staticmethod
    @beartype
    def _register_all(classes: List[Type], registry: ComponentRegistry) -> None:
        previous = {
            component_id(c): registry[component_id(c)]["class"]
            for c in classes
            if component_id(c) in registry
        }
        for number, component_class in enumerate(classes):
            try:
                registry.register_component(component_class)
            except Exception as error:
                for done in classes[:number]:
                    with contextlib.suppress(Exception):
                        if component_id(done) in previous:
                            registry.register_component(previous[component_id(done)])
                        else:
                            registry.unregister_component(done)
                raise PluginLoadError(
                    f"Could not register component '{component_class.__name__}' "
                    f"in the registry"
                ) from error

    @classmethod
    @beartype
    def _checked_class(
        cls, package: str, component: Component, registry: ComponentRegistry
    ) -> Type:
        component_class = cls._resolve_class(package, component.class_ref)
        # Registry keys by component_id, so an alias or import would mis-register
        if component_class.__name__ != component.name:
            raise PluginLoadError(
                f"'{component.class_ref}' is the class "
                f"'{component_class.__name__}'; declare it by that name"
            )
        owner = owner_of(component_class.__module__)
        if owner != owner_of(package):
            where = "dashAI" if owner == "dashai" else f"the plugin '{owner}'"
            raise PluginLoadError(
                f"'{component.class_ref}' is defined in {where}, not in this plugin"
            )
        cls._verify_type(component_class, component.type, registry)
        return component_class

    @classmethod
    @beartype
    def settings_class(cls, manifest: PluginManifest) -> Optional[Type]:
        """The manifest's ``settings`` class or None, from ``sys.modules`` if loaded."""
        if manifest.settings is None:
            return None
        return cls._resolve_class(_package(manifest.id), manifest.settings)

    @classmethod
    @beartype
    def _check_settings(cls, manifest: PluginManifest, registry: ComponentRegistry):
        # Circular import with plugins/settings.py
        from DashAI.back.plugins.settings import problem

        settings = cls.settings_class(manifest)
        if settings is None:
            return
        reason = problem(settings, manifest.id, registry)
        if reason:
            raise PluginLoadError(f"Settings '{manifest.settings}': {reason}")

    @classmethod
    @beartype
    def load(
        cls, manifest: PluginManifest, plugin_dir: Path, registry: ComponentRegistry
    ) -> List[Type]:
        package = _package(manifest.id)
        replaced = cls._install_namespace(manifest.id, plugin_dir)
        try:
            resolved = [
                cls._checked_class(package, component, registry)
                for component in manifest.components
            ]
            cls._check_settings(manifest, registry)
            cls._register_all(resolved, registry)
        except BaseException:
            for name in _modules(package):
                del sys.modules[name]
            sys.modules.update(replaced)
            raise
        return resolved

    @staticmethod
    @beartype
    def is_loaded(manifest: PluginManifest, registry: ComponentRegistry) -> bool:
        """Whether every component ``manifest`` declares is registered."""
        return all(f"{manifest.id}:{c.name}" in registry for c in manifest.components)

    @staticmethod
    @beartype
    def unload(
        manifest: PluginManifest,
        registry: ComponentRegistry,
        keep: FrozenSet[str] = frozenset(),
    ) -> None:
        """Unregister the plugin's registered components, but ``keep``."""
        for c in manifest.components:
            qualified = f"{manifest.id}:{c.name}"
            if qualified in registry and c.name not in keep:
                registry.unregister_component(registry[qualified]["class"])
