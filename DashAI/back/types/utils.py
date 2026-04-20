import json
import re
from typing import Any, Dict

from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import (
    Binary,
    DashAIValue,
    Date,
    Decimal,
    Duration,
    Float,
    Integer,
    Text,
    Time,
    Timestamp,
)


def _get_dtype_arrow_map() -> Dict[str, Any]:
    """Create dtype to pyarrow DataType mapping lazily."""
    import pyarrow as pa  # local import

    return {
        "int8": pa.int8(),
        "int16": pa.int16(),
        "int32": pa.int32(),
        "int64": pa.int64(),
        "uint8": pa.uint8(),
        "uint16": pa.uint16(),
        "uint32": pa.uint32(),
        "uint64": pa.uint64(),
        "float16": pa.float16(),
        "float32": pa.float32(),
        "float64": pa.float64(),
        "string": pa.string(),
        "large_string": pa.large_string(),
        "bool": pa.bool_(),
        "time32(s)": pa.time32("s"),
        "time32(ms)": pa.time32("ms"),
        "time64(us)": pa.time64("us"),
        "time64(ns)": pa.time64("ns"),
        "timestamp(s)": pa.timestamp("s"),
        "timestamp(ms)": pa.timestamp("ms"),
        "timestamp(us)": pa.timestamp("us"),
        "timestamp(ns)": pa.timestamp("ns"),
        "duration(s)": pa.duration("s"),
        "duration(ms)": pa.duration("ms"),
        "duration(us)": pa.duration("us"),
        "duration(ns)": pa.duration("ns"),
        "date32": pa.date32(),
        "date64": pa.date64(),
        "decimal128(8, 0)": pa.decimal128(8, 0),
        "decimal128(16, 0)": pa.decimal128(16, 0),
        "decimal256(38, 0)": pa.decimal256(38, 0),
        "decimal256(38, 10)": pa.decimal256(38, 10),
        "binary": pa.binary(),
        "large_binary": pa.large_binary(),
    }


PTYPE_TO_DASHAI = {
    "integer": {"type": "Integer", "dtype": "int64"},
    "float": {"type": "Float", "dtype": "float64"},
    "string": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    # For simplicity, we use categorical for booleans.
    "boolean": {"type": "Categorical", "dtype": "string"},
    "categorical": {"type": "Categorical", "dtype": "string"},
    # Date types mapped to Text until date support is implemented
    "date-iso-8601": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    "date-eu": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    "date-non-std": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    "date-non-std-subtype": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    "time": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    "float_comma": {"type": "Float", "dtype": "float64"},
}

value_types = [
    "Integer",
    "Float",
    "Text",
    "Boolean",
    # "Time",
    # "Timestamp",
    # "Duration",
    # "Date",
    "Decimal",
    "Binary",
]


def arrow_to_dashai_types(arrow_type, format: str = None) -> DashAIValue:
    """Convert an Arrow type to a DashAI value."""
    import pyarrow as pa  # local import

    if format is not None:
        if arrow_type == "Date":
            return Date(arrow_type=pa.string(), format=format)
        elif arrow_type == "Time":
            return Time(arrow_type=pa.string(), format=format)
        elif arrow_type == "Timestamp":
            return Timestamp(arrow_type=pa.string(), format=format)
    else:
        if pa.types.is_integer(arrow_type):
            return Integer(arrow_type)
        elif pa.types.is_floating(arrow_type):
            return Float(arrow_type)
        elif pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
            return Text(arrow_type)
        elif pa.types.is_boolean(arrow_type):
            return Categorical(values=["True", "False"])
        elif pa.types.is_dictionary(arrow_type):
            # Dictionary types (often produced by categorical columns in pandas)
            # don't carry the actual category values at the schema level, so
            # we return a Categorical placeholder with an empty categories list.
            return Categorical(values=[])
        elif pa.types.is_timestamp(arrow_type):
            return Timestamp(arrow_type)
        elif pa.types.is_date(arrow_type):
            return Date(arrow_type)
        elif pa.types.is_time(arrow_type):
            return Time(arrow_type)
        elif pa.types.is_duration(arrow_type):
            return Duration(arrow_type)
        elif pa.types.is_decimal(arrow_type):
            return Decimal(arrow_type)
        elif pa.types.is_binary(arrow_type) or pa.types.is_large_binary(arrow_type):
            return Binary(arrow_type)

    # Fallback: if we couldn't map the type explicitly, treat it as text/string
    # to avoid returning None and causing AttributeError in callers.
    return Text(pa.string())


def arrow_to_dashai_schema(arrow_tbl):
    """Iterates arrow table and asigns corresponding DashAI value type."""
    schema = {}
    for field in arrow_tbl.schema:
        column_name = field.name
        column_type = field.type
        schema[column_name] = arrow_to_dashai_types(column_type).to_string()
    return schema


def to_arrow_types(dashai_type) -> Any:
    """Convert a DashAI type to an Arrow type lazily."""
    return _get_dtype_arrow_map().get(dashai_type)


def save_types_in_arrow_metadata(pa_table: Any, datatypes: Dict[str, Dict]) -> Any:
    """
    Save DashAI types in Arrow metadata.
    This doesn't modify the Arrow schema, but adds metadata to the table.

    Parameters:
    ----------
    pa_table : pa.Table
        The Arrow table to which the metadata will be added.
    types : dict[str, DashAIValue]
        A dictionary mapping column names to DashAIValue types.
    Returns:
    -------
    pa.Table
        The Arrow table with updated metadata containing DashAI types.

    """

    # We serialize the data
    metadata_serialized = json.dumps(datatypes).encode("utf-8")

    # We obtain the current metadata
    metadata = pa_table.schema.metadata or {}

    # We add the serialized metadata to the Arrow table
    new_metadata = dict(metadata)
    new_metadata[b"dashai_types"] = metadata_serialized
    return pa_table.replace_schema_metadata(new_metadata)


def get_types_from_arrow_metadata(
    pa_table: Any,
) -> Dict[str, DashAIDataType]:
    """
    Get DashAI types from Arrow metadata.

    Parameters:
    ----------
    pa_table : pa.Table
        The Arrow table from which the metadata will be extracted.

    Returns:
    -------
    dict[str, DashAIDataType]
        A dictionary mapping column names to DashAIDataType types.

    Raises:
    ------
    ValueError
        If the metadata does not contain DashAI types.
    """
    from pyarrow.lib import Schema

    if isinstance(pa_table, Schema):
        metadata = pa_table.metadata or {}
    else:
        metadata = pa_table.schema.metadata or {}
    types_serialized = metadata.get(b"dashai_types", b"{}").decode("utf-8")

    try:
        types = json.loads(types_serialized)
        dashai_types = {}
        for column, info in types.items():
            _type = info.get("type")
            if _type == "Categorical":
                cats = info.get("categories", [])
                converted = info.get("converted", False)
                encoding = info.get("encoding", None)
                dtype = info.get("dtype", "string")
                encoder = info.get("encoder", "one_hot")
                dashai_types[column] = Categorical(
                    values=cats,
                    encoding=encoding,
                    converted=converted,
                    dtype=dtype,
                    encoder=encoder,
                )
            elif _type == "Image":
                from DashAI.back.types.dashai_image import DashAIImage

                dtype = info.get("dtype", "string")
                dashai_types[column] = DashAIImage(dtype=dtype)
            else:
                dtype = info.get("dtype")
                dtype_map = _get_dtype_arrow_map()
                dashai_types[column] = arrow_to_dashai_types(dtype_map[dtype])
    except KeyError as e:
        # If the key is not found, we can log it or handle it as needed
        print(f"KeyError: dtype {e} not found in dtype_arrow_map")
        dashai_types = {}

    return dashai_types


# Both Date and Time conversion functions are in the case
# if DashAI decides to use pyarrow dates and times instead of strings.
# Both should be modified accordingly to function properly.
def pyarrow_date_conversion(column: Any, format: str = "%Y-%m-%d") -> Any:
    """
    Convert a PyArrow array of date strings to a PyArrow date32 array.

    Parameters
    ----------
    column : pa.Array
        The PyArrow array containing date strings.
    format : str, optional
        The format of the date strings. Default is "%Y-%m-%d".
    Returns
    -------
    pa.Array
        A PyArrow array of date32 values.
    """

    import pandas as pd  # local import
    import pyarrow as pa  # local import

    str_dates = column.to_pylist()

    try:
        parsed_dates = pd.to_datetime(str_dates, format=format, errors="coerce")
    except ValueError as e:
        raise ValueError(
            f"Invalid date format: {e} - expected format is {format} "
            f"check and clean your data and try again."
        ) from e

    return pa.array(parsed_dates, type=pa.date32())


def pyarrow_time_conversion(column: Any, format: str = "%H:%M:%S") -> Any:
    """
    Convert a PyArrow array of time strings to a PyArrow time64 array.

    Parameters
    ----------
    column : pa.Array
        The PyArrow array containing time strings.
    format : str, optional
        The format of the time strings. Default is "%H:%M:%S".

    Returns
    -------
    pa.Array
        A PyArrow array of time32 values.
    """

    import pandas as pd  # local import
    import pyarrow as pa  # local import

    str_times = column.to_pylist()

    try:
        parsed_times = pd.to_datetime(str_times, format=format, errors="coerce")
    except ValueError as e:
        raise ValueError(
            f"Invalid time format: {e} - expected format is {format} "
            f"check and clean your data and try again."
        ) from e

    return pa.array(parsed_times, type=pa.time32("s"))


def is_image_path(value: Any) -> bool:
    """
    Check if the value is an image path.

    Parameters
    ----------
    value : Any
        The value of the cell to check.
    Returns
    -------
    bool
        True if the value is an image path, False otherwise.
    """
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".svg",
        ".ico",
        ".heic",
        ".heif",
    }

    if not isinstance(value, str):
        return False

    match = re.search(r"(\.[a-z0-9]+)$", value.lower())
    return bool(match) and match.group(1) in IMAGE_EXTENSIONS


# This function should be improved to detect complex situations
# Like "1.234,56" or "1,234.56"
# So it doesn't overwrite already good floats
def comma_float_to_float(array: Any) -> Any:
    """Convert a PyArrow array of float strings with commas to a PyArrow float64 array."""  # noqa: E501
    # Remove commas and convert to float
    try:
        import pyarrow as pa  # local import

        if pa.types.is_floating(array.type):
            return array
        else:
            return pa.array(
                array.to_pandas().str.replace(",", ".").astype(float), type=pa.float64()
            )
    except Exception as e:
        print("Unable to convert array to float:", e)
