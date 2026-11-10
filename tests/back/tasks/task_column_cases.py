"""Build ``taskColumnCases.json``: every registered task's roles, with verdicts.

The session wizard decides from a task's metadata whether a selection of
columns is ready. Its tests used hand-written copies of that metadata, which
drifted from the real tasks: #987 gave forecasting an optional input role, the
copies kept the old shape, and the wizard started blocking univariate series
with every test green (#994).

This module writes, for every registered task, the metadata the wizard reads
and a few selections with the backend's verdict on each. The frontend tests
read the file (``taskColumnCases.test.js``) and pytest checks that it is up to
date (``test_task_column_cases.py``), so a change to a task's roles shows up
in the review as a change to this file.

Regenerate it with::

    uv run python -m tests.back.tasks.task_column_cases
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from DashAI.back.initial_components import get_initial_components
from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.tasks.column_roles import ColumnRole

CASES_PATH = (
    Path(__file__).parents[3]
    / "DashAI"
    / "front"
    / "src"
    / "components"
    / "models"
    / "modelSession"
    / "__fixtures__"
    / "taskColumnCases.json"
)

REGENERATE = "uv run python -m tests.back.tasks.task_column_cases"


def _tasks() -> List[type]:
    tasks = [
        component
        for component in get_initial_components()
        if isinstance(component, type) and issubclass(component, BaseTask)
    ]
    return sorted(tasks, key=lambda task: task.__name__)


def _english(text: Any) -> Any:
    """A multilingual text as the API sends it to an English client."""
    return text.get("en") if hasattr(text, "get") else text


def _role_metadata(role: ColumnRole) -> Dict[str, Any]:
    """The role as the wizard reads it, with its texts in English: the API
    localizes them before they reach the frontend."""
    metadata = role.to_metadata()
    for key in ("label", "description"):
        if key in metadata:
            metadata[key] = _english(metadata[key])
    return metadata


def _columns(role: ColumnRole, count: int) -> List[str]:
    return [f"{role.name}_{i}" for i in range(count)]


def _one_or_more(role: ColumnRole) -> int:
    """The smallest number of columns, at least one, the role admits."""
    return max(role.min, 1) if role.max == "n" or role.max > 0 else 0


def _selections(task: type) -> List[Dict[str, Any]]:
    """The selections every task is checked on, by name."""
    roles = task.column_roles()
    inputs = set(task.io_roles()["inputs"])
    selections = [
        {
            "name": "the required roles at their minimum, the others empty",
            "selection": {role.name: _columns(role, role.min) for role in roles},
        },
        {
            "name": "one column in every role",
            "selection": {
                role.name: _columns(role, _one_or_more(role)) for role in roles
            },
        },
        {
            "name": "no input column",
            "selection": {
                role.name: [] if role.name in inputs else _columns(role, role.min)
                for role in roles
            },
        },
    ]
    required = [role for role in roles if role.required]
    if required:
        first = required[0]
        selections.append(
            {
                "name": f"the required role {first.name!r} left empty",
                "selection": {
                    role.name: []
                    if role.name == first.name
                    else _columns(role, _one_or_more(role))
                    for role in roles
                },
            }
        )
    return selections


def _verdict(task: type, selection: Mapping[str, List[str]]) -> Dict[str, Any]:
    """The backend's answer, with each column of the first type its role
    accepts, checked by type name as the estimated structure is."""
    instance = task()
    try:
        instance.check_role_names(selection)
        for role in task.column_roles():
            type_name = role.to_metadata()["types"][0] if role.types else None
            instance.validate_estimated_role(
                role.name, [(type_name, 1) for _ in selection.get(role.name, [])]
            )
        instance.validate_inputs_given(selection)
    except (TypeError, ValueError) as e:
        return {"valid": False, "error": str(e)}
    return {"valid": True}


def build_cases() -> Dict[str, Any]:
    """Every registered task's metadata for the wizard, and its cases."""
    tasks = []
    for task in _tasks():
        metadata = task.get_metadata()
        tasks.append(
            {
                "task": task.__name__,
                "metadata": {
                    "column_roles": [
                        _role_metadata(role) for role in task.column_roles()
                    ],
                    "io_roles": metadata["io_roles"],
                    "requires_input_columns": metadata["requires_input_columns"],
                },
                "cases": [
                    case | _verdict(task, case["selection"])
                    for case in _selections(task)
                ],
            }
        )
    return {
        "_generated_by": f"tests/back/tasks/task_column_cases.py; run `{REGENERATE}`",
        "tasks": tasks,
    }


def main() -> None:
    CASES_PATH.write_text(
        json.dumps(build_cases(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {CASES_PATH}")


if __name__ == "__main__":
    main()
