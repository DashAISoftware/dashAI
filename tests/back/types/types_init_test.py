import pyarrow as pa
import pytest

from DashAI.back.types.value_types import (
    Binary,
    Decimal,
    Duration,
    Float,
    Integer,
    Text,
)


@pytest.mark.parametrize(
    ("arrow_t", "bit_width", "is_unsigned", "dtype_str"),
    [
        (pa.int8(), 8, False, "int8"),
        (pa.int16(), 16, False, "int16"),
        (pa.int32(), 32, False, "int32"),
        (pa.int64(), 64, False, "int64"),
        (pa.uint8(), 8, True, "uint8"),
        (pa.uint16(), 16, True, "uint16"),
        (pa.uint32(), 32, True, "uint32"),
        (pa.uint64(), 64, True, "uint64"),
    ],
    ids=[
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
    ],
)
def test_dashai_types_init_valid(arrow_t, bit_width, is_unsigned, dtype_str):
    int_type = Integer(arrow_t)
    assert int_type.size == bit_width
    assert int_type.unsigned == is_unsigned
    assert int_type.dtype == dtype_str

    int_str = int_type.to_string()
    assert int_str.get("type") == "Integer"
    assert int_str.get("dtype") == dtype_str


@pytest.mark.parametrize(
    ("arrow_t", "bit_width", "dtype_str"),
    [
        (pa.float16(), 16, "float16"),
        (pa.float32(), 32, "float32"),
        (pa.float64(), 64, "float64"),
    ],
    ids=[
        "float16",
        "float32",
        "float64",
    ],
)
def test_dashai_types_float_init_valid(arrow_t, bit_width, dtype_str):
    float_type = Float(arrow_t)
    assert float_type.size == bit_width
    assert float_type.dtype == dtype_str

    float_str = float_type.to_string()
    assert float_str.get("type") == "Float"
    assert float_str.get("dtype") == dtype_str


@pytest.mark.parametrize(
    ("arrow_t", "encoding", "is_large", "dtype_str"),
    [
        (pa.string(), "utf-8", False, "string"),
        (pa.large_string(), "utf-8", True, "large_string"),
    ],
    ids=[
        "string",
        "large_string",
    ],
)
def test_dashai_types_text_init_valid(arrow_t, encoding, is_large, dtype_str):
    text_type = Text(arrow_t)
    assert text_type.encoding == encoding
    assert text_type.large == is_large
    assert text_type.dtype == dtype_str

    text_str = text_type.to_string()
    assert text_str.get("type") == "Text"
    assert text_str.get("dtype") == dtype_str


# Time, Timestamp and Date test should be implemented if the implementation changes
# This means using pa time, timestamp and date types instead of default string.
# Now it can be initialized with any arrow type as string is the default. BAD!


@pytest.mark.parametrize(
    ("arrow_t", "dtype_str"),
    [
        (pa.duration("s"), "duration[s]"),
        (pa.duration("ms"), "duration[ms]"),
        (pa.duration("us"), "duration[us]"),
        (pa.duration("ns"), "duration[ns]"),
    ],
    ids=[
        "duration[s]",
        "duration[ms]",
        "duration[us]",
        "duration[ns]",
    ],
)
def test_dashai_types_duration_init_valid(arrow_t, dtype_str):
    duration_type = Duration(arrow_t)
    assert duration_type.dtype == dtype_str

    duration_str = duration_type.to_string()
    assert duration_str.get("type") == "Duration"
    assert duration_str.get("dtype") == dtype_str


@pytest.mark.parametrize(
    ("arrow_t", "size", "precision", "scale", "dtype_str"),
    [
        (pa.decimal128(38, 10), 128, 38, 10, "decimal128(38, 10)"),
        (pa.decimal256(76, 20), 256, 76, 20, "decimal256(76, 20)"),
    ],
    ids=[
        "decimal128(38, 10)",
        "decimal256(76, 20)",
    ],
)
def test_dashai_types_decimal_init_valid(arrow_t, size, precision, scale, dtype_str):
    decimal_type = Decimal(arrow_t)
    assert decimal_type.size == size
    assert decimal_type.precision == precision
    assert decimal_type.scale == scale
    assert decimal_type.dtype == dtype_str

    decimal_str = decimal_type.to_string()
    assert decimal_str.get("type") == "Decimal"
    assert decimal_str.get("dtype") == dtype_str


@pytest.mark.parametrize(
    ("arrow_t", "dtype_str"),
    [
        (pa.binary(), "binary"),
        (pa.large_binary(), "large_binary"),
    ],
    ids=[
        "binary",
        "large_binary",
    ],
)
def test_dashai_types_binary_init_valid(arrow_t, dtype_str):
    binary_type = Binary(arrow_t)
    assert binary_type.dtype == dtype_str

    binary_str = binary_type.to_string()
    assert binary_str.get("type") == "Binary"
    assert binary_str.get("dtype") == dtype_str
