"""``taskColumnCases.json`` matches the registered tasks (#994).

The frontend tests read the file instead of hand-written copies of a task's
metadata, so it has to say what the tasks declare today. A change to a task's
roles fails here until the file is regenerated, and the regenerated file shows
the change in the review.
"""

import json

from tests.back.tasks.task_column_cases import CASES_PATH, REGENERATE, build_cases


def test_the_task_column_cases_are_up_to_date():
    stored = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    assert stored == build_cases(), (
        f"{CASES_PATH.name} is out of date with the registered tasks. "
        f"Regenerate it with `{REGENERATE}` and commit the result."
    )
