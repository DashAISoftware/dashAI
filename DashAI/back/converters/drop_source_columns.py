"""Option to drop a column-adding converter's source columns.

Converters whose ``COLUMN_OPERATION`` is ``"add"`` keep the columns they read
and append new ones. Their schemas inherit ``AddColumnsConverterSchema``, which
declares ``drop_source_columns``: when on, the orchestration layer removes the
converter's scope columns after the transform. The converter itself never sees
the option; ``split_converter_params`` takes it out of the params before the
converter class is instantiated.
"""

from typing import Any, Dict, List, Optional, Tuple

from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString

DROP_SOURCE_COLUMNS = "drop_source_columns"


class AddColumnsConverterSchema(BaseSchema):
    """Base schema for converters that add columns next to the ones they read."""

    # A real default, unlike the other schema fields: params saved before this
    # option existed have no key and must keep validating, as off.
    drop_source_columns: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en="Remove the columns this converter reads once it has created its "
            "new ones.",
            es="Elimina las columnas que lee este converter una vez que crea las "
            "nuevas.",
            pt="Remove as colunas que este conversor lê depois de criar as novas.",
            de="Entfernt die Spalten, die dieser Konverter liest, sobald er die "
            "neuen erstellt hat.",
            zh="在创建新列后删除此转换器读取的列。",
        ),
        alias=MultilingualString(
            en="Drop original columns",
            es="Eliminar columnas originales",
            pt="Remover colunas originais",
            de="Ursprüngliche Spalten entfernen",
            zh="删除原始列",
        ),
    ) = False  # type: ignore


def split_converter_params(
    params: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], bool]:
    """Separate the drop option from the params a converter is built with.

    Parameters
    ----------
    params : Optional[Dict[str, Any]]
        The converter params as saved, possibly holding the option.

    Returns
    -------
    Tuple[Dict[str, Any], bool]
        A new dict without the option (the input is not modified) and whether
        the option is on. A missing key means off.
    """
    clean = dict(params or {})
    drop = bool(clean.pop(DROP_SOURCE_COLUMNS, False))
    return clean, drop


def drops_source_columns(converter_class: Any, drop_source_columns: bool) -> bool:
    """Whether a step really drops its scope columns.

    Only a column-adding converter keeps its scope columns; the other
    operations already decide what happens to them, so the option is
    ignored for those.
    """
    return (
        drop_source_columns
        and getattr(converter_class, "COLUMN_OPERATION", None) == "add"
    )


def reject_output_named_like_scope(output_name: str, scope_columns: List[str]) -> None:
    """Refuse a new column named like one of the columns it is computed from.

    A column-adding converter keeps its scope columns, so an output with a
    scope column's name could not be told apart from the source: it would
    overwrite it, and with the drop option on it would be deleted with it.

    Raises
    ------
    ValueError
        If ``output_name`` is one of ``scope_columns``.
    """
    if output_name in scope_columns:
        raise ValueError(
            f"The output column name '{output_name}' is one of the selected "
            "columns. Choose a different name."
        )
