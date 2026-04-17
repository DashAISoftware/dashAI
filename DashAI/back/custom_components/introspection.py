"""Introspection of DashAI base classes for the custom component editor.

Surfaces abstract methods (with their docstrings) and key class attributes so
the frontend can display exactly what a user must implement when writing a
custom component.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Type

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.models.base_model import BaseModel

# Allow-list of base classes the user can extend.
# MVP: only `BaseModel` is enabled. Flip an entry's "enabled" flag to roll
# out more base types without any schema change.
_SUPPORTED_BASES: Dict[str, Dict[str, Any]] = {
    "BaseModel": {
        "class": BaseModel,
        "type": "Model",
        "import_path": "DashAI.back.models.base_model",
        "enabled": True,
    },
    "BaseConverter": {
        "class": BaseConverter,
        "type": "Converter",
        "import_path": "DashAI.back.converters.base_converter",
        "enabled": False,
    },
}


def get_supported_base_classes() -> List[Dict[str, Any]]:
    """Return metadata for every base class known to the editor.

    Disabled entries are included so the UI can render them as "coming soon".
    """
    return [
        {
            "name": name,
            "type": info["type"],
            "import_path": info["import_path"],
            "enabled": info["enabled"],
        }
        for name, info in _SUPPORTED_BASES.items()
    ]


def resolve_base_class(name: str) -> Type:
    """Look up a base class by name, enforcing the allow-list.

    Raises
    ------
    ValueError
        If the name is unknown or the class is not yet enabled.
    """
    if name not in _SUPPORTED_BASES:
        raise ValueError(f"Base class '{name}' is not supported.")
    entry = _SUPPORTED_BASES[name]
    if not entry["enabled"]:
        raise ValueError(f"Base class '{name}' is not enabled yet.")
    return entry["class"]


def _format_signature(method: Any) -> str:
    try:
        return str(inspect.signature(method))
    except (TypeError, ValueError):
        return "(...)"


def _collect_abstract_methods(base_cls: Type) -> List[Dict[str, Any]]:
    abstract_names = getattr(base_cls, "__abstractmethods__", frozenset())
    methods = []
    for name in sorted(abstract_names):
        method = getattr(base_cls, name, None)
        if method is None:
            continue
        methods.append(
            {
                "name": name,
                "signature": _format_signature(method),
                "docstring": inspect.getdoc(method) or "",
            }
        )
    return methods


def _collect_class_attrs(base_cls: Type) -> List[Dict[str, Any]]:
    """Return the UI-facing class attributes users typically override."""
    candidate_names = [
        "DISPLAY_NAME",
        "DESCRIPTION",
        "SHORT_DESCRIPTION",
        "CATEGORY",
        "COLOR",
        "ICON",
        "IMAGE_PREVIEW",
    ]
    attrs: List[Dict[str, Any]] = []
    for attr in candidate_names:
        if not hasattr(base_cls, attr):
            continue
        default = getattr(base_cls, attr)
        attrs.append(
            {
                "name": attr,
                "type": type(default).__name__,
                "default": default
                if isinstance(default, (str, int, float, bool))
                else str(default),
            }
        )
    return attrs


def _build_skeleton(base_name: str, base_cls: Type) -> str:
    """Render a minimal compileable scaffold the user can fill in."""
    class_name = f"My{base_name.removeprefix('Base')}"
    type_value = _SUPPORTED_BASES.get(base_name, {}).get("type", "")
    lines = [
        f"from {_SUPPORTED_BASES[base_name]['import_path']} import {base_name}",
        "",
        "",
        f"class {class_name}({base_name}):",
        f'    """Custom {type_value} component."""',
        "",
        f'    DISPLAY_NAME = "{class_name}"',
        '    DESCRIPTION = "Describe what this component does."',
        "",
    ]
    for name in sorted(getattr(base_cls, "__abstractmethods__", frozenset())):
        method = getattr(base_cls, name, None)
        sig = _format_signature(method) if method is not None else "(self)"
        lines.append(f"    def {name}{sig}:")
        lines.append(f'        """TODO: implement {name}."""')
        lines.append("        raise NotImplementedError")
        lines.append("")
    return "\n".join(lines)


def describe_base(name: str) -> Dict[str, Any]:
    """Describe a base class: abstract methods, attrs, and a starter skeleton."""
    base_cls = resolve_base_class(name)
    return {
        "name": name,
        "type": _SUPPORTED_BASES[name]["type"],
        "import_path": _SUPPORTED_BASES[name]["import_path"],
        "docstring": inspect.getdoc(base_cls) or "",
        "abstract_methods": _collect_abstract_methods(base_cls),
        "class_attributes": _collect_class_attrs(base_cls),
        "skeleton": _build_skeleton(name, base_cls),
    }
