import pyarrow as pa

from DashAI.back.types.utils import (
    get_types_from_arrow_metadata,
    save_types_in_arrow_metadata,
)
from DashAI.back.types.value_types import Date, Text


def _table_with_date_type(fmt):
    table = pa.table({"when": pa.array(["2020-01-31", "2020-02-29"])})
    date_type = Date(arrow_type=pa.string(), format=fmt)
    return save_types_in_arrow_metadata(table, {"when": date_type.to_string()})


def test_date_type_survives_the_arrow_metadata_round_trip():
    table = _table_with_date_type("%d/%m/%Y")

    restored = get_types_from_arrow_metadata(table)

    assert isinstance(restored["when"], Date)
    assert restored["when"].format == "%d/%m/%Y"


def test_date_without_a_stored_format_falls_back_to_iso():
    table = pa.table({"when": pa.array(["2020-01-31"])})
    table = save_types_in_arrow_metadata(
        table, {"when": {"type": "Date", "dtype": "string"}}
    )

    restored = get_types_from_arrow_metadata(table)

    assert isinstance(restored["when"], Date)
    assert restored["when"].format == "%Y-%m-%d"


def test_text_columns_are_unaffected():
    table = pa.table({"note": pa.array(["hello"])})
    table = save_types_in_arrow_metadata(
        table, {"note": Text(arrow_type=pa.string()).to_string()}
    )

    restored = get_types_from_arrow_metadata(table)

    assert isinstance(restored["note"], Text)
