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

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_integer(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not an integer type.")
        if pa.types.is_unsigned_integer(arrow_type):
            self.unsigned = True
        else:
            self.unsigned = False
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
        return {"type": "Integer", "size": self.size, "unsigned": self.unsigned}
        

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

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_floating(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a float type.")
        
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
        return {"type": "Float", "size": self.size}
    

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

    def __init__(self, arrow_type: pa.DataType):
        if not (pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type)):
            raise ValueError(
                f"Arrow type {arrow_type} is not a string type.")
        
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
        return {"type": "Text", "encoding": self.encoding, "large": self.large}
        



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

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_time(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a time type.")
        
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
        return {"type": "Time", "size": self.size, "unit": self.unit}
    



@dataclass
class Boolean(DashAIValue):
    """
    Represents a boolean value.
    """

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_boolean(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a boolean type.")
    
        
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
        return {"type": "Boolean"}


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

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_timestamp(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a timestamp type.")
        
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
        return {"type": "Timestamp", "unit": self.unit, "timezone": self.timezone}

@dataclass
class Duration(DashAIValue):
    """Represents a duration value.

    Attributes
    ----------
    unit : str
        Unit of time used. It should be 's', 'ms', 'us' or 'ns'.
    """

    unit: str = "ms"

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_duration(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a duration type.")
        
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
        return {"type": "Duration", "unit": self.unit}

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

    def __init__ (self, arrow_type: pa.DataType):
        if not pa.types.is_decimal(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a decimal type.")
        
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
        return {"type": "Decimal", "size": self.size, "precision": self.precision, "scale": self.scale}


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

    def __init__ (self, arrow_type: pa.DataType):
        if not pa.types.is_date(arrow_type):
            raise ValueError(
                f"Arrow type {arrow_type} is not a date type.")
        
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
        return {"type": "Date", "size": self.size}

@dataclass
class Binary(DashAIValue):
    """Represents a binary value.

    Attributes
    ----------
    binary_type : str
        Type of binary. It should be 'binary' or 'large_binary'.

    """

    binary_type: str = "binary"

    def __init__(self, arrow_type: pa.DataType):
        if not (pa.types.is_binary(arrow_type) or pa.types.is_large_binary(arrow_type)):
            raise ValueError(
                f"Arrow type {arrow_type} is not a binary type.")

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
        return {"type": "Binary", "binary_type": self.binary_type}
    

VALUES_DICT: "dict[str, DashAIValue]" = {
    "bool": Boolean,
    "int8": Integer,
    "int16": Integer,
    "int32": Integer,
    "int64": Integer,
    "uint8": Integer,
    "uint16": Integer,
    "uint32": Integer,
    "uint64": Integer,
    "float16": Float,
    "float32": Float,
    "float64": Float,
    "time32": Time,
    "time64": Time,
    "timestamp": Timestamp,
    "date32": "Date",
    "date64": "Date",
    "duration": Duration,
    "decimal128": Decimal,
    "decimal256": Decimal,
    "binary": Binary,
    "large_binary": Binary,
    "string": Text,
    "large_string": Text,
}


def to_dashai_value(value: Value) -> "DashAIValue":
    """Cast a Hugging Face Value into a DashAI Value according its
    dtype attribute.

    Parameters
    ----------
    value : Value
        Hugging Face Value to be casted.

    Returns
    -------
    DashAIValue
        DashAI Value corresponding to the Hugging Face Value.

    Raises
    ------
    ValueError
        Raised when an invalid value data type is given.
    """
    try:
        parenthesis = value.dtype.index("(")
        val = value.dtype[:parenthesis]
    except ValueError:
        val = value.dtype
    if val not in VALUES_DICT:
        raise ValueError(f"{value.dtype} is not a valid value data type.")

    return VALUES_DICT[val].from_value(value)

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

if __name__ == "__main__":
    int_val = Integer()
    text_val = Text()
    float_val = Float()