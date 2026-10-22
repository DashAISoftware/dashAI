"""Column roles: how tasks declare what their columns are for.

A task declares roles (``COLUMN_ROLES``) or, as every task written before
roles did, the x/y short form in its ``metadata``. ``BaseTask._role_delegate``
decides which in one place and hands the short form to ``XYRoles``. These
tests pin the three cases, the roles every built-in task gets, and that the
validation and the flat metadata say exactly what they said before roles,
against a copy of that implementation.
"""

import pandas as pd
import pytest

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.tasks.base_task import BaseTask
from DashAI.back.tasks.classification_task import ClassificationTask
from DashAI.back.tasks.clustering_task import ClusteringTask
from DashAI.back.tasks.column_roles import ColumnRole, IOColumns
from DashAI.back.tasks.forecasting_task import ForecastingTask
from DashAI.back.tasks.image_classification_task import ImageClassificationTask
from DashAI.back.tasks.regression_task import RegressionTask
from DashAI.back.tasks.supervised_task import SupervisedTask
from DashAI.back.tasks.tabular_classification_task import TabularClassificationTask
from DashAI.back.tasks.text_classification_task import TextClassificationTask
from DashAI.back.tasks.translation_task import TranslationTask
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_image import DashAIImage
from DashAI.back.types.dashai_value import DashAIValue
from DashAI.back.types.value_types import Date, Float, Integer, Text

SCHEMA = {
    "date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "other_date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "price": {"type": "Float", "dtype": "float64"},
    "cost": {"type": "Float", "dtype": "float64"},
    "units": {"type": "Integer", "dtype": "int64"},
    "note": {"type": "Text", "dtype": "string"},
    "other_note": {"type": "Text", "dtype": "string"},
    "kind": {"type": "Categorical", "dtype": "string"},
}
VALUES = {
    "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
    "other_date": ["2026-02-01", "2026-02-02", "2026-02-03"],
    "price": [1.0, 2.0, 3.0],
    "cost": [0.5, 1.5, 2.5],
    "units": [1, 2, 3],
    "note": ["a", "b", "c"],
    "other_note": ["x", "y", "z"],
    "kind": ["p", "q", "p"],
}


@pytest.fixture(scope="module", name="dataset")
def fixture_dataset():
    return transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame(VALUES)), SCHEMA
    )


class _FlatTask(BaseTask):
    """A task straight on BaseTask, written in the x/y short form."""

    metadata = {
        "inputs_types": [Float, Integer, Categorical],
        "outputs_types": [Float, Integer],
        "inputs_cardinality": "n",
        "outputs_cardinality": 1,
    }


class _SeriesTask(BaseTask):
    """A task with its own roles, and a short form it must not read for them."""

    COLUMN_ROLES = (
        ColumnRole("index", MultilingualString(en="Index"), (Date,), 1, 1),
        ColumnRole("series", MultilingualString(en="Series"), (Float, Integer), 1, 1),
        ColumnRole(
            "extra",
            MultilingualString(en="Extra"),
            (Float, Integer),
            0,
            "n",
            transformable=True,
        ),
    )
    metadata = {
        "inputs_types": [Text],
        "outputs_types": [Text],
        "inputs_cardinality": 1,
        "outputs_cardinality": 1,
    }

    @classmethod
    def io_roles(cls):
        return {"inputs": ["extra"], "outputs": ["series"]}

    def io_columns(self, roles):
        return IOColumns(
            inputs=list(roles.get("extra") or []),
            outputs=list(roles.get("series") or []),
        )

    def roles_from_io(self, input_columns, output_columns):
        return {"extra": list(input_columns), "series": list(output_columns)}


class _RolesWithoutTranslation(BaseTask):
    COLUMN_ROLES = (ColumnRole("only", MultilingualString(en="Only"), (Float,), 1, 1),)


class _NoDeclaration(BaseTask):
    metadata = {}


class _GroupedTask(BaseTask):
    """The per-group form that existed before roles. It is no longer read."""

    metadata = {
        "inputs": [{"types": [Date], "cardinality": 1}],
        "outputs": [{"types": [Float], "cardinality": 1}],
    }


def _role_summary(task):
    return [
        (
            role.name,
            [t.__name__ for t in role.types],
            role.min,
            role.max,
            role.required,
            role.transformable,
        )
        for role in task.column_roles()
    ]


# --------------------------------------------------------------------------- #
# The three ways a task gets its roles
# --------------------------------------------------------------------------- #


def test_a_base_task_in_the_short_form_gets_features_and_target():
    assert _role_summary(_FlatTask) == [
        ("features", ["Float", "Integer", "Categorical"], 0, "n", False, True),
        ("target", ["Float", "Integer"], 1, 1, True, False),
    ]
    assert _FlatTask.io_roles() == {"inputs": ["features"], "outputs": ["target"]}


def test_declared_roles_win_over_the_short_form():
    assert _role_summary(_SeriesTask) == [
        ("index", ["Date"], 1, 1, True, False),
        ("series", ["Float", "Integer"], 1, 1, True, False),
        ("extra", ["Float", "Integer"], 0, "n", False, True),
    ]
    metadata = _SeriesTask.get_metadata()
    assert [role["name"] for role in metadata["column_roles"]] == [
        "index",
        "series",
        "extra",
    ]
    assert metadata["inputs_types"] == ["Float", "Integer"]
    assert metadata["outputs_types"] == ["Float", "Integer"]


def test_a_task_that_declares_nothing_says_what_to_declare():
    with pytest.raises(NotImplementedError, match="declares no column roles"):
        _NoDeclaration.column_roles()


def test_the_per_group_form_is_no_longer_read():
    with pytest.raises(NotImplementedError, match="declares no column roles"):
        _GroupedTask.column_roles()


def test_declared_roles_without_a_translation_say_what_to_override():
    assert [role.name for role in _RolesWithoutTranslation.column_roles()] == ["only"]
    with pytest.raises(NotImplementedError, match="override io_roles"):
        _RolesWithoutTranslation.io_roles()
    with pytest.raises(NotImplementedError, match="override io_roles"):
        _RolesWithoutTranslation().io_columns({"only": ["price"]})


def test_a_task_can_translate_its_own_roles_without_touching_supervised(dataset):
    task = _SeriesTask()
    io = task.io_columns({"index": ["date"], "series": ["price"], "extra": ["units"]})
    assert io == IOColumns(inputs=["units"], outputs=["price"])

    # Roles outside the model's inputs and outputs are named after themselves.
    with pytest.raises(ValueError, match=r"Index cardinality \(0\)"):
        task.validate_roles({"series": ["price"]}, dataset._types)
    with pytest.raises(TypeError, match="not an allowed type for index columns"):
        task.validate_roles({"index": ["price"], "series": ["cost"]}, dataset._types)

    # The x/y family is untouched.
    assert RegressionTask().io_columns(
        {"features": ["units"], "target": ["price"]}
    ) == IOColumns(inputs=["units"], outputs=["price"])


def test_an_undeclared_role_is_rejected(dataset):
    with pytest.raises(ValueError, match="has no column role 'index'"):
        RegressionTask().validate_roles(
            {"features": ["units"], "target": ["price"], "index": ["date"]},
            dataset._types,
        )


# --------------------------------------------------------------------------- #
# The roles of the built-in tasks
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("task", "expected"),
    [
        (
            TabularClassificationTask,
            [
                ("features", ["Float", "Integer", "Categorical"], 0, "n", False, True),
                ("target", ["Categorical"], 1, 1, True, False),
            ],
        ),
        (
            ClassificationTask,
            [
                ("features", ["DashAIValue"], 0, "n", False, True),
                ("target", ["Categorical"], 1, 1, True, False),
            ],
        ),
        (
            RegressionTask,
            [
                ("features", ["Float", "Integer", "Categorical"], 0, "n", False, True),
                ("target", ["Float", "Integer"], 1, 1, True, False),
            ],
        ),
        (
            TextClassificationTask,
            [
                ("features", ["Text"], 1, 1, True, True),
                ("target", ["Categorical"], 1, 1, True, False),
            ],
        ),
        (
            ImageClassificationTask,
            [
                ("features", ["DashAIImage"], 1, 1, True, True),
                ("target", ["Categorical"], 1, 1, True, False),
            ],
        ),
        (
            TranslationTask,
            [
                ("features", ["Text"], 1, 1, True, True),
                ("target", ["Text"], 1, 1, True, False),
            ],
        ),
        (
            ClusteringTask,
            [
                ("features", ["Float", "Integer"], 0, "n", False, True),
                ("target", [], 0, 0, False, False),
            ],
        ),
        (
            ForecastingTask,
            [
                ("features", ["Date"], 1, 1, True, True),
                ("target", ["Float", "Integer"], 1, 1, True, False),
            ],
        ),
    ],
)
def test_the_built_in_tasks_get_the_roles_of_their_short_form(task, expected):
    assert _role_summary(task) == expected
    assert task.io_roles() == {"inputs": ["features"], "outputs": ["target"]}


def test_the_role_metadata_names_its_types_and_keeps_its_label():
    roles = RegressionTask.get_metadata()["column_roles"]

    assert roles[0]["name"] == "features"
    assert isinstance(roles[0]["label"], MultilingualString)
    assert roles[0]["label"].es == "Características"
    assert roles[1] == {
        "name": "target",
        "label": roles[1]["label"],
        "types": ["Float", "Integer"],
        "min": 1,
        "max": 1,
        "required": True,
        "transformable": False,
    }
    assert RegressionTask.get_metadata()["io_roles"] == {
        "inputs": ["features"],
        "outputs": ["target"],
    }


# --------------------------------------------------------------------------- #
# The same validation and flat metadata as before roles
# --------------------------------------------------------------------------- #
# A copy of the contract before roles (``base_task.py`` at fc3398a67), reduced
# to the single-group short form every task declares.


def _old_bounds(cardinality):
    if isinstance(cardinality, dict):
        return {"min": cardinality.get("min", 0), "max": cardinality.get("max", "n")}
    if cardinality == "n":
        return {"min": 0, "max": "n"}
    return {"min": cardinality, "max": cardinality}


def _old_groups(cls, side):
    metadata = cls.metadata
    return [
        {
            "types": tuple(metadata[f"{side}_types"]),
            **_old_bounds(metadata[f"{side}_cardinality"]),
        }
    ]


def _old_type_name(dashai_type):
    getter = getattr(dashai_type, "display_name", None)
    return getter() if callable(getter) else dashai_type.__name__


def _old_cardinality_text(group):
    minimum, maximum = group["min"], group["max"]
    if maximum == "n":
        return "n" if minimum == 0 else f"at least {minimum}"
    if minimum == maximum:
        return str(minimum)
    return f"{minimum} to {maximum}"


def _old_validate_side(cls, columns, types, side):
    groups = _old_groups(cls, side)
    counts = [0] * len(groups)
    label = "Input" if side == "inputs" else "Output"
    for column in columns:
        column_type = types[column]
        matching = [
            index
            for index, group in enumerate(groups)
            if isinstance(column_type, group["types"])
        ]
        if not matching:
            raise TypeError(
                f"{column_type} is not an allowed type for {side[:-1]} columns."
            )
        with_room = [
            index
            for index in matching
            if groups[index]["max"] == "n" or counts[index] < groups[index]["max"]
        ]
        counts[(with_room or matching)[0]] += 1
    for group, count in zip(groups, counts, strict=True):
        if count < group["min"] or (group["max"] != "n" and count > group["max"]):
            raise ValueError(
                f"{label} cardinality ({count}) does not match task "
                f"cardinality ({_old_cardinality_text(group)})"
            )


def _old_validate(cls, types, inputs, outputs):
    outputs = outputs or []
    _old_validate_side(cls, inputs, types, "inputs")
    _old_validate_side(cls, outputs, types, "outputs")


def _old_flat_metadata(cls):
    parsed = {}
    for side in ("inputs", "outputs"):
        groups = _old_groups(cls, side)
        names = []
        for group in groups:
            for dashai_type in group["types"]:
                name = _old_type_name(dashai_type)
                if name not in names:
                    names.append(name)
        parsed[f"{side}_types"] = names
        parsed[f"{side}_cardinality"] = (
            sum(g["min"] for g in groups)
            if all(g["min"] == g["max"] for g in groups)
            else "n"
        )
        parsed[side] = [
            {
                "types": [_old_type_name(t) for t in g["types"]],
                "min": g["min"],
                "max": g["max"],
            }
            for g in groups
        ]
    parsed["requires_target"] = cls.REQUIRES_TARGET
    return parsed


def _outcome(call):
    try:
        call()
    except (TypeError, ValueError) as error:
        return type(error).__name__, str(error)
    return "ok"


TASKS = [
    TabularClassificationTask,
    ClassificationTask,
    RegressionTask,
    TextClassificationTask,
    ImageClassificationTask,
    TranslationTask,
    ClusteringTask,
    ForecastingTask,
    _FlatTask,
]
COLUMN_CHOICES = [
    [],
    ["price"],
    ["units"],
    ["kind"],
    ["note"],
    ["date"],
    ["price", "units"],
    ["price", "kind", "units"],
    ["note", "other_note"],
    ["date", "other_date"],
    ["date", "price"],
    ["price", "note"],
]
OUTPUT_CHOICES = [None, [], ["price"], ["kind"], ["note"], ["price", "cost"]]


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.__name__)
def test_validation_says_exactly_what_it_said_before_roles(dataset, task):
    differences = []
    for inputs in COLUMN_CHOICES:
        for outputs in OUTPUT_CHOICES:
            before = _outcome(
                lambda inputs=inputs, outputs=outputs: _old_validate(
                    task, dataset._types, inputs, outputs
                )
            )
            after = _outcome(
                lambda inputs=inputs, outputs=outputs: task().validate_dataset_for_task(
                    dataset, "dataset", inputs, outputs
                )
            )
            if before != after:
                differences.append((inputs, outputs, before, after))
    assert differences == []


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.__name__)
def test_the_flat_metadata_is_what_it_was_before_roles(task):
    metadata = task.get_metadata()
    old = _old_flat_metadata(task)

    assert {key: metadata[key] for key in old} == old


def test_the_supervised_base_needs_no_declaration_of_its_own():
    """Supervised tasks get their roles from the short form, through BaseTask."""
    assert "column_roles" not in SupervisedTask.__dict__
    assert TextClassificationTask.column_roles()[0].types == (Text,)
    assert ImageClassificationTask.column_roles()[0].types == (DashAIImage,)
    assert ClassificationTask.column_roles()[0].types == (DashAIValue,)
