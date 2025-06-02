import pyarrow as pa
import json
from typing import Dict
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import DashAIValue, Integer, Float, Text, Time, Boolean, Timestamp, Duration, Decimal, Date, Binary
from DashAI.back.types.categorical import Categorical



dtype_arrow_map = {
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
    "boolean": {"type": "Boolean", "dtype": "bool"},
    "categorical": {"type": "Categorical", "dtype": "string"},
    "date-iso-8601": {"type": "Date", "dtype": "date64"},
    "date-eu": {"type": "Date", "dtype": "date64"},
    "date-non-std": {"type": "Date", "dtype": "date64"},
}

def arrow_to_dashai_types(arrow_type) -> DashAIValue:
    """Convert an Arrow type to a DashAI value."""
    if pa.types.is_integer(arrow_type):
        return Integer(arrow_type)
    elif pa.types.is_floating(arrow_type):
        return Float(arrow_type)
    elif pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
        return Text(arrow_type)
    elif pa.types.is_boolean(arrow_type):
        return Boolean(arrow_type)
    elif pa.types.is_time(arrow_type):
        return Time(arrow_type)
    elif pa.types.is_timestamp(arrow_type):
        return Timestamp(arrow_type)
    elif pa.types.is_duration(arrow_type):
        return Duration(arrow_type)
    elif pa.types.is_date(arrow_type):
        return Date(arrow_type)
    elif pa.types.is_decimal(arrow_type):
        return Decimal(arrow_type)
    elif pa.types.is_binary(arrow_type) or pa.types.is_large_binary(arrow_type):
        return Binary(arrow_type)
    

def arrow_to_dashai_schema(arrow_tbl):
    """Iterates arrow table and asigns corresponding DashAI value type."""
    schema = {}
    for field in arrow_tbl.schema:
        column_name = field.name
        column_type = field.type
        schema[column_name] = arrow_to_dashai_types(column_type)
    return schema

def to_arrow_types(dashai_type) -> pa.DataType:
    """Convert a DashAI type to an Arrow type."""
    return dtype_arrow_map.get(dashai_type, None)
    

#Horrible pero temporal.
def bp(dtype):
    print("dtype:", dtype)
    print("dtype_arrow_map:", dtype_arrow_map[dtype])
    if dtype == "Integer":
        return Integer(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Float":
        return Float(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Text":
        return Text(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Boolean":
        return Boolean(arrow_type=pa.bool_())
    elif dtype == "Time":
        return Time(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Timestamp":
        return Timestamp(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Duration":
        return Duration(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Date":
        return Date(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Decimal":
        return Decimal(arrow_type=dtype_arrow_map[dtype])
    elif dtype == "Binary":
        return Binary(arrow_type=dtype_arrow_map[dtype])
    else:
        raise ValueError(f"Unsupported DashAI type: {dtype_arrow_map[dtype]}")


def save_types_in_arrow_metadata(pa_table: pa.Table, datatypes: Dict[str, Dict]) -> pa.Table:
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

    #We serialize the data
    metadata_serialized = json.dumps(datatypes).encode('utf-8')

    #We obtain the current metadata
    metadata = pa_table.schema.metadata or {}

    #We add the serialized metadata to the Arrow table
    new_metadata = dict(metadata)
    new_metadata[b"dashai_types"] = metadata_serialized
    return pa_table.replace_schema_metadata(new_metadata)

def get_types_from_arrow_metadata(pa_table: pa.Table) -> Dict[str, DashAIDataType]:
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
    
    metadata = pa_table.schema.metadata or {}
    
    # Deserialize the metadata
    try:
        types_serialized = metadata[b"dashai_types"].decode('utf-8')
        types = json.loads(types_serialized)

        dashai_types = {}
        for column, info in types.items():
            _type = info.get("type")
            if _type == "Categorical":
                cats = info.get("categories", [])
                dashai_types[column] = Categorical(cats)
            else:
                dtype = info.get("dtype")
                dashai_types[column] = arrow_to_dashai_types(dtype_arrow_map[dtype])
    except:
        dashai_types = {}
    
    return dashai_types

