"""How tests write and read a session's columns for the x/y family of tasks.

A session stores its columns by role (``ModelSession.column_roles``). Every
task these tests build sessions for maps inputs to outputs, whose roles are
``features`` and ``target`` (``DashAI/back/tasks/xy_roles.py``).
"""

from typing import Iterable, Optional


def _raw_refs(names: Iterable[str]) -> list:
    return [{"kind": "raw", "name": name} for name in names]


def xy_roles(
    inputs: Iterable[str],
    outputs: Iterable[str] = (),
    input_refs: Optional[list] = None,
) -> dict:
    """The ``column_roles`` a session of the x/y family stores.

    Parameters
    ----------
    inputs : iterable of str
        The model's input columns, resolved after any preprocessing.
    outputs : iterable of str
        The model's output columns; none for a task without a target.
    input_refs : list, optional
        The inputs as column refs, when some are converter outputs. Defaults
        to raw refs of ``inputs``.
    """
    inputs, outputs = list(inputs), list(outputs)
    refs = list(input_refs) if input_refs is not None else _raw_refs(inputs)
    roles = {}
    if refs:
        roles["features"] = {"refs": refs, "columns": inputs}
    if outputs:
        roles["target"] = {"refs": _raw_refs(outputs), "columns": outputs}
    return roles


def stored_io(session) -> dict:
    """A stored session's model inputs, outputs and input refs."""
    roles = session.column_roles or {}
    features = roles.get("features", {})
    return {
        "inputs": list(features.get("columns", [])),
        "outputs": list(roles.get("target", {}).get("columns", [])),
        "input_refs": [
            {k: v for k, v in ref.items() if v is not None}
            for ref in features.get("refs", [])
        ],
    }
