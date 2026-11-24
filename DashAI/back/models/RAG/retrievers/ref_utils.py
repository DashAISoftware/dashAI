"""Helpers for the ``{component, params}`` reference shape used by RAG configs."""

from __future__ import annotations

from typing import Any, Final

#: Key naming the registered component of a ``{component, params}`` reference.
COMPONENT_KEY: Final[str] = "component"

#: Key holding the parameters of a ``{component, params}`` reference.
PARAMS_KEY: Final[str] = "params"

#: Parameter holding the child retrievers of a composite retriever.
CHILDREN_KEY: Final[str] = "children"


def is_component_ref(value: Any) -> bool:
    """Return whether ``value`` is a ``{component, params}`` reference dict.

    Parameters
    ----------
    value : Any
        Candidate configuration value.

    Returns
    -------
    bool
        ``True`` when ``value`` is a dict carrying a string ``component`` and a
        ``params`` entry.
    """
    return (
        isinstance(value, dict)
        and COMPONENT_KEY in value
        and PARAMS_KEY in value
        and isinstance(value.get(COMPONENT_KEY), str)
    )
