"""The roles of the x/y family: tasks that map input columns to output columns.

Classification, regression, translation and clustering all feed a model the
columns of one role as ``x`` and, when they have a target, those of another as
``y``. They declare it in the short form every task and plugin has always
used, ``inputs_types`` and ``inputs_cardinality`` beside ``outputs_types`` and
``outputs_cardinality``, and this module reads that form as two roles:

- ``features``: the inputs, which the session's preprocessing may transform;
- ``target``: the outputs, protected from the preprocessing. A task whose
  ``outputs_cardinality`` is 0, like clustering, has no target: it declares
  only the features.

The role names live here and nowhere else. ``BaseTask`` hands a task that
declares the short form to these methods (``BaseTask._role_delegate``); a task
that declares its own ``COLUMN_ROLES`` translates them itself.
"""

from typing import Dict, List, Mapping, Sequence, Tuple

from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.column_roles import ColumnRole, IOColumns, bounds

FEATURES = "features"
TARGET = "target"

FEATURES_LABEL = MultilingualString(
    en="Features",
    es="Características",
    pt="Características",
    de="Merkmale",
    zh="特征",
)
TARGET_LABEL = MultilingualString(
    en="Target",
    es="Objetivo",
    pt="Alvo",
    de="Zielgröße",
    zh="目标",
)


class XYRoles:
    """Declare and translate the roles of a task written in the x/y short form.

    Every method takes the task class, whose ``metadata`` holds the short form.
    """

    @staticmethod
    def column_roles(task_cls: type) -> Tuple[ColumnRole, ...]:
        """The features and, unless the task takes no outputs, the target."""
        metadata = task_cls.metadata
        features = ColumnRole(
            name=FEATURES,
            label=FEATURES_LABEL,
            types=tuple(metadata["inputs_types"]),
            transformable=True,
            **bounds(metadata["inputs_cardinality"]),
        )
        target_bounds = bounds(metadata["outputs_cardinality"])
        if target_bounds["max"] == 0:
            return (features,)
        target = ColumnRole(
            name=TARGET,
            label=TARGET_LABEL,
            types=tuple(metadata["outputs_types"]),
            transformable=False,
            **target_bounds,
        )
        return (features, target)

    @staticmethod
    def io_roles(task_cls: type) -> Dict[str, List[str]]:
        """The features feed the model's inputs and the target its outputs."""
        declared = {role.name for role in XYRoles.column_roles(task_cls)}
        return {
            "inputs": [FEATURES],
            "outputs": [TARGET] if TARGET in declared else [],
        }

    @staticmethod
    def io_columns(task_cls: type, roles: Mapping[str, Sequence]) -> IOColumns:
        """The features as the model's inputs and the target as its outputs."""
        return IOColumns(
            inputs=list(roles.get(FEATURES) or []),
            outputs=list(roles.get(TARGET) or []),
        )

    @staticmethod
    def roles_from_io(
        task_cls: type, inputs: Sequence, outputs: Sequence
    ) -> Dict[str, list]:
        """The roles that a model's inputs and outputs came from."""
        return {FEATURES: list(inputs), TARGET: list(outputs or [])}
