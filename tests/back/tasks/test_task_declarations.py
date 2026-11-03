"""What a task declares for the frontend to read, besides its roles.

The task list used to pick each task's icon from a map of task names, and the
session wizard offered session preprocessing to every task that carves
partitions, even one the session API then refuses with a 422. The task
declares both instead.
"""

import pytest

from DashAI.back.initial_components import get_initial_components
from DashAI.back.tasks.base_task import BaseTask

TASKS = {
    component.__name__: component
    for component in get_initial_components()
    if isinstance(component, type) and issubclass(component, BaseTask)
}

# The icons the frontend's name map gave them, so the task list keeps its
# look; forecasting had none and fell back to Science.
ICONS = {
    "TabularClassificationTask": "TableChart",
    "TextClassificationTask": "TextFields",
    "ImageClassificationTask": "ImageSearch",
    "RegressionTask": "ShowChart",
    "TranslationTask": "Translate",
    "ClusteringTask": "Science",
    "SingleSeriesForecastingTask": "Timeline",
}


def test_every_registered_task_is_listed_here():
    assert set(TASKS) == set(ICONS)


@pytest.mark.parametrize(("name", "icon"), ICONS.items())
def test_a_task_declares_its_icon(name, icon):
    assert TASKS[name].get_metadata()["icon"] == icon


@pytest.mark.parametrize("name", sorted(ICONS))
def test_a_task_takes_preprocessing_when_some_role_can_be_transformed(name):
    task = TASKS[name]
    transformable = any(role.transformable for role in task.column_roles())

    assert task.get_metadata()["takes_preprocessing"] is transformable


def test_every_registered_task_takes_preprocessing():
    # Single-series forecasting did not until its exogenous role, the first of
    # its roles the preprocessing may transform (RECONCILING_FORECASTING §7).
    takes = {
        name: task.get_metadata()["takes_preprocessing"] for name, task in TASKS.items()
    }

    assert takes == dict.fromkeys(TASKS, True)
