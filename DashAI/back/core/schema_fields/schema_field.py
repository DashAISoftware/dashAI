from typing import Type, TypeVar, Union

from pydantic import Field
from typing_extensions import Annotated

from DashAI.back.core.utils import MultilingualString

T = TypeVar("T")


def schema_field(
    t: T,
    placeholder: T,
    description: Union[str, MultilingualString],
    alias: Union[str, MultilingualString] = None,
) -> Type[T]:
    """Function to create a schema field of type T.

    Parameters
    ----------
    description: Union[str, MultilingualString]
        A string or multilingual string that describes the field.
    placeholder: T
        The value that will be displayed to the user.
    alias: str, optional
        An alternative name for the field when serialized/deserialized.

    Returns
    -------
    type[T]
        A pydantic-like type to represent the schema field.
    """
    # Default to english if a string is provided
    if isinstance(description, str):
        description = MultilingualString(en=description)

    field_params = {
        "description": description,
        "json_schema_extra": {"placeholder": placeholder, "display_name": alias},
    }
    return Annotated[
        t,
        Field(**field_params),
    ]
