from typing import Type, TypeVar

from pydantic import Field
from typing_extensions import Annotated

T = TypeVar("T")


def schema_field(t: T, placeholder: T, description: str, alias: str = None) -> Type[T]:
    """Function to create a schema field of type T.

    Parameters
    ----------
    description: str
        A string that describes the field.
    placeholder: T
        The value that will be displayed to the user.
    alias: str, optional
        An alternative name for the field when serialized/deserialized.

    Returns
    -------
    type[T]
        A pydantic-like type to represent the schema field.
    """
    field_params = {
        "description": description,
        "json_schema_extra": {"placeholder": placeholder},
    }
    if alias:
        field_params["alias"] = alias
    return Annotated[
        t,
        Field(**field_params),
    ]
