"""Thin adapters between the custom-component feature and the ComponentRegistry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

from DashAI.back.custom_components.loader import unload_user_module

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry

logger = logging.getLogger(__name__)


def register_custom(cls: Type, registry: "ComponentRegistry") -> None:
    """Register a loaded user class into the live registry.

    Raises
    ------
    ValueError
        If a component with the same name is already registered.
    """
    if cls.__name__ in registry:
        raise ValueError(f"Component '{cls.__name__}' is already registered.")
    registry.register_component(cls)
    logger.info("Registered custom component: %s", cls.__name__)


def unregister_custom(class_name: str, registry: "ComponentRegistry") -> None:
    """Remove a custom component from the registry by class name.

    Silently no-ops if the component is not currently registered, so callers
    can always call this before re-registering an edited class.
    """
    if class_name not in registry:
        unload_user_module(class_name)
        return
    cls = registry[class_name]["class"]
    registry.unregister_component(cls)
    unload_user_module(class_name)
    logger.info("Unregistered custom component: %s", class_name)
