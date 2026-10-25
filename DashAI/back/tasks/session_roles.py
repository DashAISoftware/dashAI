"""The column roles a model session stores.

For every role the session records two lists:

- ``refs``, the choice: column refs over the original columns or over the
  outputs of the session's preprocessing steps. A raw ref is an original
  column; a group ref is what a converter produces. This is the only source of
  truth.
- ``columns``, the refs resolved to column names once the preprocessing has
  been fitted. It is derived: at creation it holds the names of the raw refs,
  and ``PreprocessingJob`` overwrites it with the resolved names.

A role with no columns is left out. Generic code never names a role: it reads
the session's roles through ``session_io``, which asks the task to translate
them into a model's inputs and outputs.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Sequence

from pydantic import BaseModel, Field, RootModel

from DashAI.back.preprocessing.column_ref import (
    ColumnRef,
)

if TYPE_CHECKING:
    from DashAI.back.tasks.base_task import BaseTask


class RoleColumns(BaseModel):
    """What a session stores for one role."""

    refs: List[ColumnRef] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)


class SessionColumnRoles(RootModel[Dict[str, RoleColumns]]):
    """A session's roles, keyed by role name, in the task's order."""

    @classmethod
    def from_stored(cls, stored: Mapping[str, Any]) -> "SessionColumnRoles":
        """Read the JSON a session row holds."""
        return cls.model_validate(dict(stored or {}))

    def to_stored(self) -> Dict[str, Any]:
        """The JSON a session row holds."""
        return self.model_dump(mode="json")

    def refs(self) -> Dict[str, List[Any]]:
        """Role name to the role's column refs."""
        return {name: list(role.refs) for name, role in self.root.items()}

    def columns(self) -> Dict[str, List[str]]:
        """Role name to the role's resolved column names."""
        return {name: list(role.columns) for name, role in self.root.items()}

    def with_columns(
        self, columns: Mapping[str, Sequence[str]]
    ) -> "SessionColumnRoles":
        """A copy whose roles hold these resolved columns.

        Parameters
        ----------
        columns : mapping
            Role name to the role's resolved column names. Roles it leaves out
            keep the columns they had.
        """
        return SessionColumnRoles(
            {
                name: RoleColumns(
                    refs=role.refs,
                    columns=list(columns.get(name, role.columns)),
                )
                for name, role in self.root.items()
            }
        )

    @classmethod
    def from_refs(cls, refs: Mapping[str, Sequence[Any]]) -> "SessionColumnRoles":
        """Build the roles a session is created with, from the refs chosen.

        Before the preprocessing is fitted, a role's columns are the names of
        its raw refs. Roles given no refs are left out.

        Parameters
        ----------
        refs : mapping
            Role name to the role's column refs.
        """
        return cls(
            {
                name: RoleColumns(
                    refs=list(role_refs),
                    columns=[ref.name for ref in role_refs if ref.kind == "raw"],
                )
                for name, role_refs in refs.items()
                if role_refs
            }
        )


@dataclass(frozen=True)
class SessionIO:
    """A session's columns as a model's inputs and outputs.

    Attributes
    ----------
    inputs : list of str
        The model's input columns, resolved after the preprocessing.
    outputs : list of str
        The model's output columns.
    input_refs : list of ColumnRef
        The model's inputs as column refs.
    raw_inputs : list of str
        The original columns among the inputs: the names of the raw refs.
    """

    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    input_refs: List[Any] = field(default_factory=list)
    raw_inputs: List[str] = field(default_factory=list)


def session_raw_columns(model_session: Any, io: SessionIO) -> List[str]:
    """The dataset columns the session's model reads, through its preprocessing.

    A session that preprocesses has among its inputs columns that only its
    fitted converters produce, which no dataset has. What a dataset needs to
    be predicted or explained on is what the fitted preprocessor reads
    (``ConverterSequence.raw_columns_read``). Without steps, the inputs are
    dataset columns themselves.
    """
    from DashAI.back.preprocessing.column_ref import ConverterSequence

    preprocessing = model_session.preprocessing or {}
    if not preprocessing.get("steps"):
        return list(io.inputs)
    sequence = ConverterSequence.model_validate(preprocessing)
    return sequence.raw_columns_read(io.input_refs)


def session_roles(model_session: Any, task: "BaseTask") -> SessionColumnRoles:
    """The roles a session stores.

    ``task`` is the session's task. It is not needed to read the stored roles,
    and is kept so that every reader goes through the task, as ``session_io``
    does.
    """
    return SessionColumnRoles.from_stored(model_session.column_roles)


def session_io(model_session: Any, task: "BaseTask") -> SessionIO:
    """A session's columns translated by its task into inputs and outputs."""
    roles = session_roles(model_session, task)
    names = task.io_columns(roles.columns())
    refs = task.io_columns(roles.refs())
    return SessionIO(
        inputs=list(names.inputs),
        outputs=list(names.outputs),
        input_refs=list(refs.inputs),
        raw_inputs=[ref.name for ref in refs.inputs if ref.kind == "raw"],
    )
