from dataclasses import dataclass

from datasets import Value
import pyarrow as pa
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.dashai_value import DashAIValue
from typing import Optional


@dataclass
class Integer(DashAIValue):
    """Represents an integer value.
    
    Attributes
    ----------
    size : int
        Number of bits used to represent the integer numbers.
        The accepted sizes are 8, 16, 32 and 64.
    unsigned : bool
        Whether the integer is unsigned or not.
    """

    size: int = 64
    unsigned: bool = False
    dtype: str = "int64"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_integer(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not an integer type.")
        if pa.types.is_unsigned_integer(arrow_type):
            self.unsigned = True
        else:
            self.unsigned = False
        self.dtype = str(arrow_type)
        self.size = arrow_type.bit_width
        
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Integer", "dtype": self.dtype}
        

@dataclass
class Float(DashAIValue):
    """Represents a float value.
    
    Attributes
    ----------
    size : int
        Number of bits used to represent the float numbers.
        The accepted sizes are 16, 32 and 64.
    """

    size: int = 64
    dtype: str = "float64"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_floating(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a float type.")
        if pa.types.is_float16(arrow_type):
            self.size = 16
            self.dtype = "float16"
        elif pa.types.is_float32(arrow_type):
            self.size = 32
            self.dtype = "float32"
        elif pa.types.is_float64(arrow_type):
            self.size = 64
            self.dtype = "float64"
        

    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Float", "dtype": self.dtype}
    

@dataclass
class Text(DashAIValue):
    """
    Represents a text value.
    
    Attributes
    ----------
    encoding : str
        Encoding used for the text. It should be a valid Python encoding.
    large : bool
        Whether the text is large or not.
    """
    

    encoding: str = "utf-8"
    large: bool = False
    dtype: str = "string"

    def __init__(self, arrow_type: pa.DataType):
        if not (pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type)):
            raise ValueError(
                f"Arrow type {arrow_type} is not a string type.")
        self.dtype = str(arrow_type)
        if arrow_type.equals(pa.large_string()):
            self.large = True
        else:
            self.large = False
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Text", "encoding": self.encoding, "dtype": self.dtype}
        

@dataclass
class Time(DashAIValue):
    """Represents a time value.
        
    Attributes
    ----------
    size : int
        Number of bits used to represent the integer numbers.
        The accepted sizes are 32 and 64.
    unit : str
        Unit of time used. It should be 's' or 'ms'.
    """
    size: int = 32
    unit: str = "s"
    dtype: str = "time32(s)"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_time(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a time type.")
        self.dtype = str(arrow_type)
        self.size = arrow_type.bit_width
        if arrow_type.equals(pa.time32()):
            if arrow_type.unit == "s":
                self.unit = "s"
            elif arrow_type.unit == "ms":
                self.unit = "ms"
        elif arrow_type.equals(pa.time64()):
            if arrow_type.unit == "us":
                self.unit = "us"
            elif arrow_type.unit == "ns":
                self.unit = "ns"
        else:
            raise ValueError(
                f"Invalid time type: {arrow_type}. Expected time32 or time64."
            )
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Time", "dtype": self.dtype}
    

@dataclass
class Boolean(DashAIValue):
    """
    Represents a boolean value.
    """

    dtype: str = "bool"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_boolean(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a boolean type.")
        self.dtype = str(arrow_type)
        
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Boolean", "dtype": self.dtype}


@dataclass
class Timestamp(DashAIValue):
    """Represents a timestamp value.
    
    Attributes
    ----------
    unit : str
        Unit of time used. It should be 's', 'ms', 'us' or 'ns'.
        timezone : str or None
        Timezone used for the timestamp. If None, the timestamp is timezone-naive.
    """

    unit: str = "s"
    timezone: Optional[str] = None
    dtype: str = "timestamp(s)"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_timestamp(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a timestamp type.")
        self.dtype = str(arrow_type)
        self.unit = arrow_type.unit
        self.timezone = arrow_type.tz
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Timestamp", "dtype": self.dtype}


@dataclass
class Duration(DashAIValue):
    """Represents a duration value.

    Attributes
    ----------
    unit : str
        Unit of time used. It should be 's', 'ms', 'us' or 'ns'.
    """

    unit: str = "ms"
    dtype: str = "duration(ms)"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_duration(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a duration type.")
        self.dtype = str(arrow_type)
        self.unit = arrow_type.unit
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")

    def to_string(self):
        return {"type": "Duration", "dtype": self.dtype}


@dataclass
class Decimal(DashAIValue):
    """Represents a decimal value.

    Attributes
    ----------
    size : int
        Number of bits used to represent the decimal value.
        It should be 128 or 256.
    precision : int
        Number of digits used in the value.
    scale : int
        Number of decimal digits

    """

    size: int = 128
    precision: int = 8
    scale: int = 0
    dtype: str = "decimal128(8, 0)"

    def __init__ (self, arrow_type: pa.DataType):
        if not pa.types.is_decimal(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a decimal type.")
        self.dtype = str(arrow_type)
        if isinstance(arrow_type, pa.Decimal128Type):
            self.size = 128
        elif isinstance(arrow_type, pa.Decimal256Type):
            self.size = 256
        else:
            raise ValueError(
                f"Invalid decimal type: {arrow_type}. Expected Decimal128 or Decimal256."
            )
        self.precision = arrow_type.precision
        self.scale = arrow_type.scale
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Decimal", "dtype": self.dtype}


@dataclass
class Date(DashAIValue):
    """Represents a date value.

    Attributes
    ----------
    size : int
        Number of bits used to represent the date value.
        It should be 32 or 64.

    """

    size: int = 64
    dtype: str = "date64"
    def __init__ (self, arrow_type: pa.DataType):
        if not pa.types.is_date(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a date type.")
        self.dtype = str(arrow_type)
        if arrow_type.equals(pa.date32()):
            self.size = 32
        elif arrow_type.equals(pa.date64()):
            self.size = 64
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Date", "dtype": self.dtype}


@dataclass
class Binary(DashAIValue):
    """Represents a binary value.

    Attributes
    ----------
    binary_type : str
        Type of binary. It should be 'binary' or 'large_binary'.

    """

    binary_type: str = "binary"
    dtype: pa.DataType = "binary"

    def __init__(self, arrow_type: pa.DataType):
        if not (pa.types.is_binary(arrow_type) or pa.types.is_large_binary(arrow_type)):
            raise ValueError(
                f"Arrow type {arrow_type} is not a binary type.")
        self.dtype = arrow_type
        if arrow_type.equals(pa.binary()):
            self.binary_type = "binary"
        elif arrow_type.equals(pa.large_binary()):
            self.binary_type = "large_binary"
    
    def transform(self, values, library):
        if library == "numpy":
            return values.to_numpy()
        elif library == "torch":
            return values.to_torch()
        elif library == "tensorflow":
            return values.to_tensorflow()
        else:
            raise ValueError(f"Unsupported library: {library}")
    
    def to_string(self):
        return {"type": "Binary", "dtype": self.dtype}
    
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


def arrow_to_dashai_types(arrow_type) -> DashAIValue:
    """Convert an Arrow type to a DashAI value."""
    if pa.types.is_integer(arrow_type):
        return Integer(arrow_type).to_string()
    elif pa.types.is_floating(arrow_type):
        return Float(arrow_type).to_string()
    elif pa.types.is_string(arrow_type):
        return Text(arrow_type).to_string()
    elif pa.types.is_large_string(arrow_type):
        return Text(arrow_type).to_string()
    elif pa.types.is_boolean(arrow_type):
        return Boolean(arrow_type).to_string()
    elif pa.types.is_time(arrow_type):
        return Time(arrow_type).to_string()
    elif pa.types.is_timestamp(arrow_type):
        return Timestamp(arrow_type).to_string()
    elif pa.types.is_duration(arrow_type):
        return Duration(arrow_type).to_string()
    elif pa.types.is_date(arrow_type):
        return Date(arrow_type).to_string()
    elif pa.types.is_decimal(arrow_type):
        return Decimal(arrow_type).to_string()
    elif pa.types.is_binary(arrow_type):
        return Binary(arrow_type).to_string()
    elif pa.types.is_large_binary(arrow_type):
        return Binary(arrow_type).to_string()

def arrow_to_dashai_schema(arrow_tbl):
    """Iterates arrow table and asigns corresponding DashAI value type."""
    schema = {}
    for field in arrow_tbl.schema:
        column_name = field.name
        column_type = field.type
        schema[column_name] = arrow_to_dashai_types(column_type)
    return schema

def dashai_to_arrow_types(dashai_type) -> pa.DataType:
    """Convert a DashAI type to an Arrow type."""
    return dtype_arrow_map.get(dashai_type, None)
    

#Horrible pero temporal.
def new_types_iterator(columns):
    """Iterates over the columns of a table."""

    new_types = {}

    for column in columns:
        dashai_type = getattr(columns[column], "type", None)
        dtype = getattr(columns[column], "dtype", None)
        if dashai_type == "Integer":
            if dtype == "int8":
                new_types[column] = Integer(arrow_type=pa.int8()).to_string()
            elif dtype == "int16":
                new_types[column] = Integer(arrow_type=pa.int16()).to_string()
            elif dtype == "int32":
                new_types[column] = Integer(arrow_type=pa.int32()).to_string()
            elif dtype == "int64":
                new_types[column] = Integer(arrow_type=pa.int64()).to_string()
            elif dtype == "uint8":
                new_types[column] = Integer(arrow_type=pa.uint8()).to_string()
            elif dtype == "uint16":
                new_types[column] = Integer(arrow_type=pa.uint16()).to_string()
            elif dtype == "uint32":
                new_types[column] = Integer(arrow_type=pa.uint32()).to_string()
            elif dtype == "uint64":
                new_types[column] = Integer(arrow_type=pa.uint64()).to_string()
        elif dashai_type == "Float":
            if dtype == "float16":
                new_types[column] = Float(arrow_type=pa.float16()).to_string()
            elif dtype == "float32":
                new_types[column] = Float(arrow_type=pa.float32()).to_string()
            elif dtype == "float64":
                new_types[column] = Float(arrow_type=pa.float64()).to_string()
        elif dashai_type == "Text":
            if dtype == "string":
                new_types[column] = Text(arrow_type=pa.string()).to_string()
            elif dtype == "large_string":
                new_types[column] = Text(arrow_type=pa.large_string()).to_string()
        elif dashai_type == "Boolean":
            if dtype == "bool":
                new_types[column] = Boolean(arrow_type=pa.bool_()).to_string()
        elif dashai_type == "Time":
            if dtype == "time32(s)":
                new_types[column] = Time(arrow_type=pa.time32("s")).to_string()
            elif dtype == "time64(us)":
                new_types[column] = Time(arrow_type=pa.time64("us")).to_string()
            elif dtype == "time64(ns)":
                new_types[column] = Time(arrow_type=pa.time64("ns")).to_string()
        elif dashai_type == "Timestamp":
            if dtype == "timestamp(s)":
                new_types[column] = Timestamp(arrow_type=pa.timestamp("s")).to_string()
            elif dtype == "timestamp(ms)":
                new_types[column] = Timestamp(arrow_type=pa.timestamp("ms")).to_string()
            elif dtype == "timestamp(us)":
                new_types[column] = Timestamp(arrow_type=pa.timestamp("us")).to_string()
            elif dtype == "timestamp(ns)":
                new_types[column] = Timestamp(arrow_type=pa.timestamp("ns")).to_string()
        elif dashai_type == "Duration":
            if dtype == "duration(s)":
                new_types[column] = Duration(arrow_type=pa.duration("s")).to_string()
            elif dtype == "duration(ms)":
                new_types[column] = Duration(arrow_type=pa.duration("ms")).to_string()
            elif dtype == "duration(us)":
                new_types[column] = Duration(arrow_type=pa.duration("us")).to_string()
            elif dtype == "duration(ns)":
                new_types[column] = Duration(arrow_type=pa.duration("ns")).to_string()
        elif dashai_type == "Date":
            if dtype == "date32":
                new_types[column] = Date(arrow_type=pa.date32()).to_string()
            elif dtype == "date64":
                new_types[column] = Date(arrow_type=pa.date64()).to_string()
        elif dashai_type == "Decimal":
            if dtype == "decimal128(8, 0)":
                new_types[column] = Decimal(arrow_type=pa.decimal128(8, 0)).to_string()
            elif dtype == "decimal128(16, 0)":
                new_types[column] = Decimal(arrow_type=pa.decimal128(16, 0)).to_string()
            elif dtype == "decimal256(38, 0)":
                new_types[column] = Decimal(arrow_type=pa.decimal256(38, 0)).to_string()
            elif dtype == "decimal256(38, 10)":
                new_types[column] = Decimal(arrow_type=pa.decimal256(38, 10)).to_string()
        elif dashai_type == "Binary":
            if dtype == "binary":
                new_types[column] = Binary(arrow_type=pa.binary()).to_string()
            elif dtype == "large_binary":
                new_types[column] = Binary(arrow_type=pa.large_binary()).to_string()
        else:
            raise ValueError(f"Unsupported DashAI type: {dashai_type}")
        
    return new_types
