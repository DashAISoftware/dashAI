"""Thin adapters between the custom-component feature and the ComponentRegistry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

from DashAI.back.custom_components.loader import unload_user_module
from DashAI.back.custom_components.originals import get_original

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry

logger = logging.getLogger(__name__)


def register_custom(
    cls: Type,
    registry: "ComponentRegistry",
    override: bool = False,
) -> None:
    """Register a user-authored class into the live registry.

    Parameters
    ----------
    cls : Type
        The class to register.
    registry : ComponentRegistry
        The registry to mutate.
    override : bool
        If True and a component with the same name is already registered,
        unregister the existing one first (core/plugin or a previous override)
        and register the new class in its place. If False, a name collision
        raises.
    """
    name = cls.__name__
    if name in registry:
        if not override:
            raise ValueError(f"Component '{name}' is already registered.")
        existing = registry[name]["class"]
        registry.unregister_component(existing)
        logger.info("Replaced existing component: %s", name)
    registry.register_component(cls)
    logger.info("Registered custom component: %s (override=%s)", name, override)


def unregister_custom(
    class_name: str,
    registry: "ComponentRegistry",
    restore_original: bool = False,
) -> None:
    """Remove a custom component from the registry by class name.

    Silently no-ops if the component is not currently registered, so callers
    can always call this before re-registering an edited class.

    When `restore_original` is True and we hold a snapshot of the original
    class (captured at startup before any override was applied), the original
    is re-registered in place. Used by the revert flow for core/plugin
    overrides.
    """
    was_registered = class_name in registry
    if was_registered:
        cls = registry[class_name]["class"]
        registry.unregister_component(cls)
        logger.info("Unregistered custom component: %s", class_name)

    unload_user_module(class_name)

    if restore_original:
        original = get_original(class_name)
        if original is not None and class_name not in registry:
            registry.register_component(original)
            logger.info("Restored original component: %s", class_name)
