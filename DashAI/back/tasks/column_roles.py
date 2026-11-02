"""Column roles: what each column of a session is for.

A task says which roles its columns can play, for instance the features and
the target of a supervised task, and the session records which columns play
each one. Generic code (jobs, units, the API, the frontend) never names a
role: it reads the task's declaration and asks the task to translate.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from DashAI.back.core.utils import MultilingualString


def bounds(cardinality: Any) -> Dict[str, Any]:
    """Read a declared cardinality as a minimum and a maximum.

    Parameters
    ----------
    cardinality : Any
        An int for an exact count, ``"n"`` for any number, or a mapping with
        ``"min"`` and ``"max"`` for a range whose ``"max"`` may itself be
        ``"n"``.

    Returns
    -------
    dict
        A mapping with keys ``"min"`` and ``"max"``.
    """
    if isinstance(cardinality, dict):
        return {
            "min": cardinality.get("min", 0),
            "max": cardinality.get("max", "n"),
        }
    if cardinality == "n":
        return {"min": 0, "max": "n"}
    return {"min": cardinality, "max": cardinality}


def type_name(dashai_type: type) -> str:
    """Name a type the way the frontend and the columns themselves do.

    A DashAI type reports its own name through ``display_name()``, which
    matches what a column emits via ``to_string()``. Declared types may also
    be foreign classes, for example HuggingFace dataset features or a plugin's
    own types, so those fall back to the class name.

    Parameters
    ----------
    dashai_type : type
        One of the declared type classes.

    Returns
    -------
    str
        The name to show for it.
    """
    getter = getattr(dashai_type, "display_name", None)
    return getter() if callable(getter) else dashai_type.__name__


def _names_with_subtypes(types: Tuple[type, ...]) -> set:
    """The names of these types and of every subclass of theirs."""
    names = set()
    pending = list(types)
    while pending:
        current = pending.pop()
        names.add(type_name(current))
        pending.extend(current.__subclasses__())
    return names


@dataclass(frozen=True)
class ColumnRole:
    """One role a task's columns can play.

    Attributes
    ----------
    name : str
        The key the session stores the role's columns under.
    label : MultilingualString
        What the wizard calls the role.
    types : tuple of type
        The column types the role accepts once the session's preprocessing
        has run. A role that accepts no type takes no columns.
    min, max : int, int or "n"
        How many columns the role takes. The role is required when ``min`` is
        above zero; a ``max`` of zero says the task takes no such columns.
    transformable : bool
        Whether the session's preprocessing may transform the role's columns.
        A role that is not transformable is protected: converters never take
        it in their scope and the model reads its original columns.
    """

    name: str
    label: MultilingualString
    types: Tuple[type, ...]
    min: int = 0
    max: Union[int, Literal["n"]] = "n"
    transformable: bool = False

    @property
    def required(self) -> bool:
        """Whether the session has to give the role at least one column."""
        return self.min > 0

    def accepts_type_name(self, name: Optional[str]) -> bool:
        """Whether a column whose type has this name fits the role.

        The estimated structure of a preprocessing chain only names its
        column types, so this is the check made on it: the declared types and
        every subtype of theirs, as ``isinstance`` would accept. An unknown
        type (None) fits, since only a fit can tell.
        """
        if name is None:
            return True
        return name in _names_with_subtypes(self.types)

    def admits(self, count: int) -> bool:
        """Whether ``count`` columns fit the role's cardinality."""
        return count >= self.min and (self.max == "n" or count <= self.max)

    def cardinality_text(self) -> str:
        """Say the cardinality the way an error message should read it.

        Returns
        -------
        str
            For example ``"1"``, ``"n"``, ``"at least 1"`` or ``"1 to 3"``.
        """
        if self.max == "n":
            return "n" if self.min == 0 else f"at least {self.min}"
        if self.min == self.max:
            return str(self.min)
        return f"{self.min} to {self.max}"

    def to_metadata(self) -> Dict[str, Any]:
        """The role as the frontend reads it, with types as their names."""
        return {
            "name": self.name,
            "label": self.label,
            "types": [type_name(t) for t in self.types],
            "min": self.min,
            "max": self.max,
            "required": self.required,
            "transformable": self.transformable,
        }


@dataclass(frozen=True)
class IOColumns:
    """A session's columns seen as a model's inputs and outputs.

    It is what a task's ``io_columns`` answers: the columns the units feed the
    model as ``x`` and as ``y``. The entries are whatever the roles held,
    column names or column refs.
    """

    inputs: List[Any] = field(default_factory=list)
    outputs: List[Any] = field(default_factory=list)
