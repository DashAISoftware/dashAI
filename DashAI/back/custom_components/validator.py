"""Validate user-authored component source before persisting or registering."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import List, Optional, Type

from DashAI.back.custom_components.introspection import resolve_base_class
from DashAI.back.custom_components.loader import load_user_class


class ValidationError(Exception):
    """Raised by `validate_source` when validation fails hard."""


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cls: Optional[Type] = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_source(
    source: str,
    class_name: str,
    base_class_name: str,
) -> ValidationResult:
    """Run syntax + inheritance + abstract method checks on the source.

    The class is imported in an isolated namespace; it is NOT registered into
    the ComponentRegistry. Returns a `ValidationResult` whose `cls` attribute
    holds the loaded class when `ok` is True.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        base_cls = resolve_base_class(base_class_name)
    except ValueError as e:
        return ValidationResult(ok=False, errors=[str(e)])

    try:
        cls = load_user_class(source, class_name)
    except SyntaxError as e:
        return ValidationResult(
            ok=False,
            errors=[f"SyntaxError: {e.msg} (line {e.lineno})"],
        )
    except KeyError as e:
        return ValidationResult(ok=False, errors=[str(e).strip("'\"")])
    except TypeError as e:
        return ValidationResult(ok=False, errors=[str(e)])
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc(limit=3)
        return ValidationResult(
            ok=False,
            errors=[f"Error while loading source: {e}", tb],
        )

    if not issubclass(cls, base_cls):
        errors.append(f"Class '{class_name}' must inherit from '{base_class_name}'.")

    remaining_abstract = getattr(cls, "__abstractmethods__", frozenset())
    if remaining_abstract:
        errors.append(
            "Missing implementation for abstract methods: "
            + ", ".join(sorted(remaining_abstract))
        )

    if cls.__name__ != class_name:
        errors.append(
            f"Declared class name '{cls.__name__}' does not match requested "
            f"'{class_name}'."
        )

    if errors:
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    return ValidationResult(ok=True, warnings=warnings, cls=cls)
