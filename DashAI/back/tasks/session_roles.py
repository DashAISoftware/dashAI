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
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence

from pydantic import BaseModel, Field, RootModel

from DashAI.back.preprocessing.column_ref import (
    ColumnRef,
    RawColumnRef,
    parse_column_refs,
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
    def from_io(
        cls,
        task: "BaseTask",
        input_columns: Sequence[str],
        output_columns: Sequence[str],
        input_refs: Optional[Sequence[Any]] = None,
    ) -> "SessionColumnRoles":
        """Build the roles from a model's inputs and outputs.

        The outputs are always original columns, so they are raw refs. The
        input refs default to the raw refs of the input columns.

        Parameters
        ----------
        task : BaseTask
            The session's task, which translates inputs and outputs to roles.
        input_columns, output_columns : sequence of str
            The model's inputs and outputs, as column names.
        input_refs : sequence, optional
            The model's inputs as column refs, when some are converter outputs.
        """
        if input_refs is None:
            input_refs = [RawColumnRef(name=name) for name in input_columns]
        output_refs = [RawColumnRef(name=name) for name in output_columns]
        refs = task.roles_from_io(list(input_refs), output_refs)
        names = task.roles_from_io(list(input_columns), list(output_columns))
        return cls(
            {
                name: RoleColumns(refs=role_refs, columns=names.get(name, []))
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


def session_roles(model_session: Any, task: "BaseTask") -> SessionColumnRoles:
    """The roles a session stores.

    Transitional: a row written before ``column_roles`` existed, or built
    without it, is read from the old fields through the task. The fallback
    goes with those fields.
    """
    stored = getattr(model_session, "column_roles", None)
    if stored is not None:
        return SessionColumnRoles.from_stored(stored)
    refs = model_session.input_column_refs
    return SessionColumnRoles.from_io(
        task,
        input_columns=list(model_session.input_columns or []),
        output_columns=list(model_session.output_columns or []),
        input_refs=parse_column_refs(refs) if refs is not None else None,
    )


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
