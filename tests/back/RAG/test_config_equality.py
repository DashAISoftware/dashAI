"""Tests for the RAG configuration equality contract.

The cases in ``tests/shared/config_equality_cases.json`` are the contract's
examples; the frontend reads the same file. The tests here add what JSON cannot
express: tuples, sets, bytes, non-string keys, non-finite numbers and custom
objects, which must raise rather than compare.
"""

import json
import math
from pathlib import Path
from typing import Any

import pytest

from DashAI.back.services.RAG.config_equality import configs_equal

CASES_PATH = (
    Path(__file__).resolve().parents[2] / "shared" / "config_equality_cases.json"
)
CASES_KEY = "cases"
NAME_KEY = "name"
LEFT_KEY = "a"
RIGHT_KEY = "b"
IGNORED_KEY = "ignored_keys"
EQUAL_KEY = "equal"


MALFORMED_KEY = "malformed_cases"


def _load_document() -> dict[str, Any]:
    """Return the shared cases document, read relative to this test file."""
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


_DOCUMENT = _load_document()
_CASES = _DOCUMENT[CASES_KEY]
_MALFORMED_CASES = _DOCUMENT[MALFORMED_KEY]


class _CustomValue:
    """A value outside the contract."""


@pytest.mark.parametrize("case", _CASES, ids=[case[NAME_KEY] for case in _CASES])
def test_shared_case_matches_expected_result(case: dict[str, Any]):
    left, right = case[LEFT_KEY], case[RIGHT_KEY]
    ignored = case[IGNORED_KEY]

    assert configs_equal(left, right, ignored) is case[EQUAL_KEY]


@pytest.mark.parametrize("case", _CASES, ids=[case[NAME_KEY] for case in _CASES])
def test_shared_case_is_symmetric(case: dict[str, Any]):
    left, right = case[LEFT_KEY], case[RIGHT_KEY]
    ignored = case[IGNORED_KEY]

    assert configs_equal(right, left, ignored) is case[EQUAL_KEY]


@pytest.mark.parametrize(
    "case", _MALFORMED_CASES, ids=[case[NAME_KEY] for case in _MALFORMED_CASES]
)
def test_shared_malformed_case_raises_on_either_side(case: dict[str, Any]):
    left, right = case[LEFT_KEY], case[RIGHT_KEY]
    ignored = case[IGNORED_KEY]

    with pytest.raises(ValueError, match="safe integer"):
        configs_equal(left, right, ignored)
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal(right, left, ignored)


def test_shared_cases_file_covers_the_required_scenarios():
    names = {case[NAME_KEY] for case in _CASES}
    assert len(_CASES) >= 40
    assert any("key order" in name for name in names)
    assert any("realistic hybrid" in name for name in names)
    assert any("realistic chunking" in name for name in names)
    assert any("proto key" in name for name in names)
    assert any("e-acute" in name for name in names)
    assert any("negative zero" in name for name in names)


def test_nothing_is_ignored_by_default():
    assert configs_equal({"top_k": 1}, {"top_k": 2}) is False


def test_ignored_keys_accept_any_collection_of_strings():
    assert configs_equal({"top_k": 1}, {"top_k": 2}, ("top_k",)) is True
    assert configs_equal({"top_k": 1}, {"top_k": 2}, frozenset({"top_k"})) is True


def test_inputs_are_not_mutated():
    left = {"top_k": 1, "children": [{"params": {"top_k": 2}}]}
    right = {"children": [{"params": {"top_k": 3}}], "top_k": 1}
    left_before = json.dumps(left, sort_keys=True)
    right_before = json.dumps(right, sort_keys=True)

    assert configs_equal(left, right, ("top_k",)) is True

    assert json.dumps(left, sort_keys=True) == left_before
    assert json.dumps(right, sort_keys=True) == right_before


@pytest.mark.parametrize(
    "value",
    [
        (1, 2),
        {1, 2},
        frozenset({1}),
        b"bytes",
        bytearray(b"bytes"),
        1j,
        _CustomValue(),
        {"nested": (1, 2)},
        [{"nested": {1, 2}}],
    ],
    ids=[
        "tuple",
        "set",
        "frozenset",
        "bytes",
        "bytearray",
        "complex",
        "custom-object",
        "tuple-in-object",
        "set-in-array",
    ],
)
def test_unsupported_value_raises_type_error_on_either_side(value: Any):
    with pytest.raises(TypeError):
        configs_equal(value, {"a": 1})
    with pytest.raises(TypeError):
        configs_equal({"a": 1}, value)


@pytest.mark.parametrize(
    "key",
    [1, 2.5, None, True, (1, 2)],
    ids=["int", "float", "none", "bool", "tuple"],
)
def test_non_string_object_key_raises_type_error(key: Any):
    with pytest.raises(TypeError):
        configs_equal({key: 1}, {"a": 1})
    with pytest.raises(TypeError):
        configs_equal({"a": 1}, {key: 1})


@pytest.mark.parametrize(
    "bad",
    [math.nan, math.inf, -math.inf],
    ids=["nan", "inf", "negative-inf"],
)
def test_non_finite_number_raises_value_error_on_either_side(bad: float):
    with pytest.raises(ValueError, match="non-finite"):
        configs_equal(bad, 1)
    with pytest.raises(ValueError, match="non-finite"):
        configs_equal(1, bad)
    with pytest.raises(ValueError, match="non-finite"):
        configs_equal({"a": [bad]}, {"a": [1]})
    with pytest.raises(ValueError, match="non-finite"):
        configs_equal({"a": [1]}, {"a": {"b": bad}})


def test_malformed_value_raises_even_when_the_comparison_would_differ_early():
    """Validation covers both inputs before any comparison can stop early."""
    left = {"a": 0, "z": (1,)}
    right = {"a": 1}

    with pytest.raises(TypeError):
        configs_equal(left, right)
    with pytest.raises(TypeError):
        configs_equal(right, left)


def test_non_finite_number_raises_even_when_the_key_would_be_ignored():
    with pytest.raises(ValueError, match="non-finite"):
        configs_equal({"top_k": math.nan}, {}, ("top_k",))


def test_malformed_value_under_an_ignored_key_still_raises():
    with pytest.raises(TypeError):
        configs_equal({"top_k": (1,)}, {}, ("top_k",))


def test_non_string_ignored_key_raises_type_error():
    with pytest.raises(TypeError):
        configs_equal({"a": 1}, {"a": 1}, (1,))


def test_string_as_ignored_keys_is_rejected():
    """A bare string would iterate per character; it must not be accepted."""
    with pytest.raises(TypeError):
        configs_equal({"top_k": 1}, {"top_k": 2}, "top_k")


def test_top_level_list_versus_tuple_raises_type_error():
    with pytest.raises(TypeError):
        configs_equal([1, 2], (1, 2))


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ({"x": {"y": [{"z": True}]}}, {"x": {"y": [{"z": 1}]}}),
        ({"x": {"y": [{"z": False}]}}, {"x": {"y": [{"z": 0.0}]}}),
        ([[True, {"k": 1}]], [[1, {"k": True}]]),
        ({"a": [0, [False]]}, {"a": [False, [0]]}),
    ],
)
def test_booleans_never_equal_numbers_inside_nested_containers(left: Any, right: Any):
    assert configs_equal(left, right) is False
    assert configs_equal(right, left) is False


def test_numbers_inside_nested_containers_compare_by_value():
    assert configs_equal({"x": [{"y": [1]}]}, {"x": [{"y": [1.0]}]}) is True


def test_none_inside_nested_containers_is_not_an_absent_key():
    assert configs_equal({"x": {"y": None}}, {"x": {}}) is False
    assert configs_equal({"x": {"y": None}}, {"x": {"y": None}}) is True


#: JavaScript's largest integer that every double represents exactly.
JS_MAX_SAFE_INTEGER = 2**53 - 1


def test_the_module_exposes_the_javascript_safe_integer_bound():
    from DashAI.back.services.RAG.config_equality import MAX_SAFE_INTEGER

    assert MAX_SAFE_INTEGER == JS_MAX_SAFE_INTEGER


@pytest.mark.parametrize(
    "value",
    [JS_MAX_SAFE_INTEGER + 1, -(JS_MAX_SAFE_INTEGER + 1), 2**64],
    ids=["just-above", "just-below", "far-above"],
)
def test_integer_beyond_the_javascript_safe_range_raises_value_error(value: int):
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal(value, value)
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal({"a": [value]}, {"a": [1]})
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal({"a": 1}, {"a": {"b": value}})


def test_unsafe_integer_under_an_ignored_key_still_raises():
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal({"top_k": JS_MAX_SAFE_INTEGER + 1}, {}, ("top_k",))


def test_the_safe_range_bounds_are_accepted_and_compared_exactly():
    assert configs_equal(JS_MAX_SAFE_INTEGER, JS_MAX_SAFE_INTEGER) is True
    assert configs_equal(-JS_MAX_SAFE_INTEGER, -JS_MAX_SAFE_INTEGER) is True
    assert configs_equal(JS_MAX_SAFE_INTEGER, JS_MAX_SAFE_INTEGER - 1) is False


@pytest.mark.parametrize(
    "value",
    [1e20, -1e20, 2.0**53, -(2.0**53), 1.5e300, 2.0**60],
    ids=["1e20", "-1e20", "2-pow-53", "-2-pow-53", "1.5e300", "2-pow-60"],
)
def test_integral_float_beyond_the_safe_range_raises_value_error(value: float):
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal(value, 1)
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal(1, value)
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal({"a": [value]}, {"a": [1]})
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal({"a": 1}, {"a": {"b": value}})


def test_unsafe_integral_float_under_an_ignored_key_still_raises():
    with pytest.raises(ValueError, match="safe integer"):
        configs_equal({"top_k": 1e20}, {}, ("top_k",))


@pytest.mark.parametrize(
    "value",
    [2.0**53 - 1, -(2.0**53 - 1), 1e15, 0.5, -0.5, 1e-9],
    ids=["2-pow-53-minus-1", "-2-pow-53-minus-1", "1e15", "0.5", "-0.5", "1e-9"],
)
def test_float_within_the_safe_range_or_fractional_is_accepted(value: float):
    assert configs_equal(value, value) is True
    assert configs_equal(value, 1) is False


def test_integral_float_within_the_safe_range_equals_its_integer():
    assert configs_equal(1e15, 10**15) is True
    assert configs_equal(2.0**53 - 1, 2**53 - 1) is True
