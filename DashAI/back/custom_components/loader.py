"""Load a user-authored Python class from a source string.

No sandboxing: DashAI runs locally as a trusted desktop/dev tool, same trust
model as pip-installed plugins. The executed source has full interpreter
access.
"""

from __future__ import annotations

import contextlib
import sys
from types import ModuleType
from typing import Type

from pydantic import BaseModel

MODULE_PREFIX = "dashai_custom_"


def _module_name_for(class_name: str) -> str:
    return f"{MODULE_PREFIX}{class_name}"


def load_user_class(
    source: str,
    class_name: str,
    module_name: str | None = None,
) -> Type:
    """Execute `source` in a fresh module namespace and return the named class.

    The module is registered in ``sys.modules`` so that Pydantic (and anything
    else that looks up types via ``sys.modules[cls.__module__]``) can resolve
    references declared inside the user's source. The module entry is replaced
    on every call, which also handles edits and re-registrations cleanly.

    Parameters
    ----------
    source : str
        Python source code that defines the target class at module scope.
    class_name : str
        The class to extract after the source runs.
    module_name : str | None, optional
        Synthetic module name used for the generated module object. Defaults
        to ``dashai_custom_<class_name>``.

    Returns
    -------
    Type
        The class object defined by the user source.

    Raises
    ------
    SyntaxError
        If the source does not compile.
    KeyError
        If `class_name` is not defined in the source.
    TypeError
        If the named symbol is not a class.
    """
    module_name = module_name or _module_name_for(class_name)
    module = ModuleType(module_name)
    module.__dict__["__name__"] = module_name

    # Register BEFORE exec so decorators / pydantic / dataclasses that peek at
    # sys.modules during class creation can find the module.
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        compiled = compile(source, f"<custom:{class_name}>", "exec")
        exec(compiled, module.__dict__)
    except BaseException:
        # Roll back the sys.modules entry on failure so nothing stale lingers.
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
        raise

    if class_name not in module.__dict__:
        # Defined module object OK, but the target class is missing — leave the
        # module registered so the caller can inspect it, mirror the exec path.
        raise KeyError(f"Class '{class_name}' is not defined in the provided source.")
    obj = module.__dict__[class_name]
    if not isinstance(obj, type):
        raise TypeError(f"Symbol '{class_name}' is not a class.")

    _finalize_pydantic_schema(obj, module)
    return obj


def unload_user_module(class_name: str) -> None:
    """Remove a previously-registered user module from ``sys.modules``.

    No-ops if the module is not registered.
    """
    sys.modules.pop(_module_name_for(class_name), None)


def _finalize_pydantic_schema(cls: Type, module: ModuleType) -> None:
    """Force Pydantic schema rebuild for the class's ``SCHEMA`` attribute.

    Pydantic v2 defers core-schema construction; when the schema lives in a
    synthetic module, forward references declared on the fields may not
    resolve until we call ``model_rebuild`` with the full module namespace.
    """
    schema_cls = getattr(cls, "SCHEMA", None)
    if schema_cls is None or not isinstance(schema_cls, type):
        return
    if not issubclass(schema_cls, BaseModel):
        return
    # Best-effort: rebuild failures surface later as a clearer validation
    # error when `get_schema()` is called.
    with contextlib.suppress(Exception):
        schema_cls.model_rebuild(
            _types_namespace=dict(module.__dict__),
            force=True,
        )
