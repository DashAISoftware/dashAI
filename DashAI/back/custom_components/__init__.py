"""In-app custom component authoring.

Provides utilities to introspect DashAI base classes, validate user-authored
Python source, load it into a fresh namespace, and register the resulting
class into the live ComponentRegistry.
"""

from DashAI.back.custom_components.introspection import (
    describe_base,
    get_supported_base_classes,
    resolve_base_class,
)
from DashAI.back.custom_components.loader import load_user_class
from DashAI.back.custom_components.registry_bridge import (
    register_custom,
    unregister_custom,
)
from DashAI.back.custom_components.validator import (
    ValidationError,
    ValidationResult,
    validate_source,
)

__all__ = [
    "describe_base",
    "get_supported_base_classes",
    "resolve_base_class",
    "load_user_class",
    "register_custom",
    "unregister_custom",
    "ValidationError",
    "ValidationResult",
    "validate_source",
]
