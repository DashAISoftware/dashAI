from dataclasses import dataclass
from typing import Optional

import pyarrow as pa

from DashAI.back.types.dashai_value import DashAIValue


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
            raise ValueError(f"Arrow type {arrow_type} is not an integer type.")
        if pa.types.is_unsigned_integer(arrow_type):
            self.unsigned = True
        else:
            self.unsigned = False
        self.dtype = str(arrow_type)
        self.size = arrow_type.bit_width

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
            raise ValueError(f"Arrow type {arrow_type} is not a float type.")
        if pa.types.is_float16(arrow_type):
            self.size = 16
            self.dtype = "float16"
        elif pa.types.is_float32(arrow_type):
            self.size = 32
            self.dtype = "float32"
        elif pa.types.is_float64(arrow_type):
            self.size = 64
            self.dtype = "float64"

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
            raise ValueError(f"Arrow type {arrow_type} is not a string type.")
        self.dtype = str(arrow_type)
        if arrow_type.equals(pa.large_string()):
            self.large = True
        else:
            self.large = False

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

    format: str = "HH:mm:ss"
    dtype: str = "string"

    def __init__(self, arrow_type: pa.DataType, format: Optional[str]):
        self.format = format if format else "HH:mm:ss"
        self.dtype = str(arrow_type)

    def to_string(self):
        return {"type": "Time", "dtype": self.dtype, "format": self.format}


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

    format: str = "YYYY-MM-DD HH:mm:ss"
    dtype: str = "string"

    def __init__(self, arrow_type: pa.DataType, format: Optional[str] = None):
        self.format = format if format else "YYYY-MM-DD HH:mm:ss"
        self.dtype = str(arrow_type)

    def to_string(self):
        return {"type": "Timestamp", "dtype": self.dtype, "format": self.format}


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
            raise ValueError(f"Arrow type {arrow_type} is not a duration type.")
        self.dtype = str(arrow_type)
        self.unit = arrow_type.unit

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

    def __init__(self, arrow_type: pa.DataType):
        if not pa.types.is_decimal(arrow_type):
            raise ValueError(f"Arrow type {arrow_type} is not a decimal type.")
        self.dtype = str(arrow_type)
        if isinstance(arrow_type, pa.Decimal128Type):
            self.size = 128
        elif isinstance(arrow_type, pa.Decimal256Type):
            self.size = 256
        else:
            raise ValueError(
                f"Invalid decimal type: {arrow_type}. "
                f"Expected Decimal128 or Decimal256."
            )
        self.precision = arrow_type.precision
        self.scale = arrow_type.scale

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

    format: str = "YYYY-MM-DD"
    dtype: str = "string"

    def __init__(self, arrow_type: pa.DataType, format: Optional[str]):
        self.format = format if format else "YYYY-MM-DD"
        self.dtype = str(arrow_type)

    def to_string(self):
        return {"type": "Date", "dtype": self.dtype, "format": self.format}


@dataclass
class Binary(DashAIValue):
    """Represents a binary value.

    Attributes
    ----------
    binary_type : str
        Type of binary. It should be 'binary' or 'large_binary'.

    """

    dtype: str = "binary"

    def __init__(self, arrow_type: pa.DataType):
        if not (pa.types.is_binary(arrow_type) or pa.types.is_large_binary(arrow_type)):
            raise ValueError(f"Arrow type {arrow_type} is not a binary type.")
        self.dtype = str(arrow_type)

    def to_string(self):
        return {"type": "Binary", "dtype": self.dtype}
