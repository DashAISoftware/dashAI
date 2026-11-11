from typing import Optional, Type, TypeVar, Union

from pydantic import Field
from typing_extensions import Annotated

from DashAI.back.core.utils import MultilingualString

T = TypeVar("T")


def schema_field(
    t: T,
    placeholder: T,
    description: Union[str, MultilingualString],
    alias: Union[str, MultilingualString] = None,
    step: Optional[float] = None,
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
    step: float, optional
        Increment applied by the numeric input's arrow controls. It only
        affects the form and does not constrain the accepted values.

    Returns
    -------
    type[T]
        A pydantic-like type to represent the schema field.
    """
    if isinstance(description, str):
        description = MultilingualString(en=description)

    json_schema_extra = {"placeholder": placeholder, "display_name": alias}
    if step is not None:
        json_schema_extra["step"] = step

    field_params = {
        "description": description,
        "json_schema_extra": json_schema_extra,
    }
    return Annotated[
        t,
        Field(**field_params),
    ]
