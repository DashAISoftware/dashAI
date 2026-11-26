"""Structural equality for RAG configurations.

This is the one comparison standard for RAG configurations. Every place in the
backend that decides whether two parameter sets, component references or
persistence signatures are the same uses :func:`configs_equal`. The frontend
mirrors this contract and reads the same examples from
``tests/shared/config_equality_cases.json``.

Contract
--------
Values: null, booleans, finite numbers, strings, arrays, objects with string
keys. Anything else (tuple, set, bytes, non-str dict keys, NaN/Infinity, custom
objects) raises a clear error (TypeError for unsupported types, ValueError for
non-finite numbers); never a silent default.

Numbers beyond +/-(2**53 - 1) (:data:`MAX_SAFE_INTEGER`) are outside the
contract. An integer whose absolute value exceeds the bound is rejected, and so
is a float whose value is integral and whose absolute value exceeds it (1e20,
2.0**53, 1.5e300), with ValueError: JavaScript cannot represent them exactly and
the frontend would compare them differently. Fractional floats (0.5, 1e-9) and
integral values within the bound are ordinary numbers.

Objects are equal iff, after dropping the ignored keys, they have exactly the
same keys and equal values; key order is irrelevant. No subsets: an extra or a
missing key makes them differ.

Arrays are equal iff same length and element-wise equal IN ORDER.

Strict types: a boolean is never equal to a number (False != 0, True != 1,
False != 0.0). null/None is never equal to an absent key. Numbers compare by
value, and 1 equals 1.0 (JavaScript cannot tell them apart, so the contract does
not either). Strings never equal numbers.

Ignored keys: an optional, explicit collection of key names, applied recursively
at every object level, including objects nested in arrays and in component
references' ``params``. Default empty.

Cross-language note: in JavaScript an object property whose value is
``undefined`` is treated as absent (it is what the wire/JSON carries);
``undefined`` anywhere else (top level, array element) is malformed and raises.

Both inputs are validated completely before anything is compared, so a malformed
value raises even when the comparison would have stopped earlier, and the result
never depends on evaluation order.
"""

import math
from collections.abc import Collection
from enum import Enum
from typing import Any, Dict, FrozenSet, List

#: Largest integer magnitude JavaScript represents exactly (``MAX_SAFE_INTEGER``).
MAX_SAFE_INTEGER = 2**53 - 1

_ROOT_PATH = "$"


class _Kind(Enum):
    """The contract's value categories."""

    NULL = "null"
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"
    ARRAY = "array"
    OBJECT = "object"


def _is_unsafe_number(value: int | float) -> bool:
    """Whether a number lies beyond the safe range of the contract.

    Only integral values can be unsafe: a fractional float is never beyond the
    bound, whatever its magnitude, so it is never rejected.

    Parameters
    ----------
    value : int | float
        A finite number.

    Returns
    -------
    bool
        ``True`` when *value* is integral and its absolute value exceeds
        :data:`MAX_SAFE_INTEGER`.
    """
    if isinstance(value, float) and not value.is_integer():
        return False
    return abs(value) > MAX_SAFE_INTEGER


def _check_number(value: int | float, path: str) -> None:
    """Check that one number is finite and within the safe range.

    Parameters
    ----------
    value : int | float
        The number to check.
    path : str
        Location of the value, used in error messages.

    Raises
    ------
    ValueError
        If the float is not finite, or the number is beyond
        :data:`MAX_SAFE_INTEGER`.
    """
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(
            f"{path}: non-finite number {value!r} has no configuration equality"
        )
    if _is_unsafe_number(value):
        raise ValueError(
            f"{path}: number {value!r} is outside the safe integer range "
            f"+/-{MAX_SAFE_INTEGER}, which JavaScript cannot represent exactly"
        )


def _kind_of(value: Any, path: str) -> _Kind:
    """Return the contract category of one value.

    Parameters
    ----------
    value : Any
        The value to classify.
    path : str
        Location of the value, used in error messages.

    Returns
    -------
    _Kind
        The category of *value*.

    Raises
    ------
    TypeError
        If the value is outside the contract.
    ValueError
        If the value is a non-finite number, or a number beyond
        :data:`MAX_SAFE_INTEGER`.
    """
    if value is None:
        return _Kind.NULL
    if isinstance(value, bool):
        return _Kind.BOOLEAN
    if isinstance(value, (int, float)):
        _check_number(value, path)
        return _Kind.NUMBER
    if isinstance(value, str):
        return _Kind.STRING
    if isinstance(value, list):
        return _Kind.ARRAY
    if isinstance(value, dict):
        return _Kind.OBJECT
    raise TypeError(
        f"{path}: unsupported configuration value of type {type(value).__name__}"
    )


def _validate(value: Any, path: str) -> None:
    """Check that *value* and everything nested in it is within the contract.

    Parameters
    ----------
    value : Any
        The value to check.
    path : str
        Location of the value, used in error messages.

    Raises
    ------
    TypeError
        If the value or a nested value is outside the contract, or an object
        key is not a string.
    ValueError
        If a nested number is not finite or is beyond the safe range.
    """
    kind = _kind_of(value, path)
    if kind is _Kind.ARRAY:
        for index, item in enumerate(value):
            _validate(item, f"{path}[{index}]")
    elif kind is _Kind.OBJECT:
        _validate_object(value, path)


def _validate_object(value: Dict[str, Any], path: str) -> None:
    """Check the keys and values of one object, recursively.

    Parameters
    ----------
    value : Dict[str, Any]
        The object to check.
    path : str
        Location of the object, used in error messages.

    Raises
    ------
    TypeError
        If a key is not a string, or a nested value is outside the contract.
    ValueError
        If a nested number is not finite or is beyond the safe range.
    """
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(
                f"{path}: object keys must be strings, got {type(key).__name__}"
            )
        _validate(item, f"{path}.{key}")


def _ignored_names(ignored_keys: Collection[str]) -> FrozenSet[str]:
    """Return the ignored key names as a frozen set, checking each one.

    Parameters
    ----------
    ignored_keys : Collection[str]
        Key names to drop at every object level.

    Returns
    -------
    FrozenSet[str]
        The names.

    Raises
    ------
    TypeError
        If *ignored_keys* is a bare string, or holds a non-string name.
    """
    if isinstance(ignored_keys, str):
        raise TypeError("ignored_keys must be a collection of key names, not a str")
    names: List[str] = []
    for name in ignored_keys:
        if not isinstance(name, str):
            raise TypeError(
                f"ignored key names must be strings, got {type(name).__name__}"
            )
        names.append(name)
    return frozenset(names)


def _kept_items(mapping: Dict[str, Any], ignored: FrozenSet[str]) -> Dict[str, Any]:
    """Return the entries of *mapping* whose keys are not ignored.

    Parameters
    ----------
    mapping : Dict[str, Any]
        An already validated object.
    ignored : FrozenSet[str]
        Key names to drop at this level.

    Returns
    -------
    Dict[str, Any]
        A new mapping holding the remaining entries.
    """
    kept: Dict[str, Any] = {}
    for key, item in mapping.items():
        if key not in ignored:
            kept[key] = item
    return kept


def _same_array(left: List[Any], right: List[Any], ignored: FrozenSet[str]) -> bool:
    """Return whether two validated arrays are equal element by element, in order.

    Parameters
    ----------
    left : List[Any]
        First array.
    right : List[Any]
        Second array.
    ignored : FrozenSet[str]
        Key names ignored inside the elements.

    Returns
    -------
    bool
        ``True`` when the lengths match and every pair of elements is equal.
    """
    if len(left) != len(right):
        return False
    for left_item, right_item in zip(left, right, strict=True):
        if not _same_value(left_item, right_item, ignored):
            return False
    return True


def _same_object(
    left: Dict[str, Any], right: Dict[str, Any], ignored: FrozenSet[str]
) -> bool:
    """Return whether two validated objects hold the same keys and values.

    Parameters
    ----------
    left : Dict[str, Any]
        First object.
    right : Dict[str, Any]
        Second object.
    ignored : FrozenSet[str]
        Key names dropped at this level and every level below it.

    Returns
    -------
    bool
        ``True`` when the kept keys are identical and every kept value is equal.
    """
    left_kept = _kept_items(left, ignored)
    right_kept = _kept_items(right, ignored)
    if left_kept.keys() != right_kept.keys():
        return False
    for key, item in left_kept.items():
        if not _same_value(item, right_kept[key], ignored):
            return False
    return True


def _same_value(left: Any, right: Any, ignored: FrozenSet[str]) -> bool:
    """Return whether two validated values are equal under the contract.

    Parameters
    ----------
    left : Any
        First value, already validated.
    right : Any
        Second value, already validated.
    ignored : FrozenSet[str]
        Key names dropped at every object level.

    Returns
    -------
    bool
        ``True`` when the two values are equal. Values of different categories
        are never equal, so a boolean never equals a number and null never
        equals an absent key.
    """
    # Both values were validated first, so the path is never reported.
    kind = _kind_of(left, _ROOT_PATH)
    if kind is not _kind_of(right, _ROOT_PATH):
        return False
    if kind is _Kind.NULL:
        return True
    if kind is _Kind.ARRAY:
        return _same_array(left, right, ignored)
    if kind is _Kind.OBJECT:
        return _same_object(left, right, ignored)
    return bool(left == right)


def configs_equal(left: Any, right: Any, ignored_keys: Collection[str] = ()) -> bool:
    """Return whether two RAG configuration values are equal under the contract.

    Parameters
    ----------
    left : Any
        First configuration value: null, boolean, finite number, string, array
        or object with string keys.
    right : Any
        Second configuration value, with the same allowed types.
    ignored_keys : Collection[str], optional
        Key names dropped at every object level, including objects nested in
        arrays and in component references' ``params``. Defaults to none.

    Returns
    -------
    bool
        ``True`` when the two values are equal.

    Raises
    ------
    TypeError
        If either value, or *ignored_keys*, holds a value outside the contract,
        or *ignored_keys* is a bare string.
    ValueError
        If either value holds a non-finite number or a number beyond
        :data:`MAX_SAFE_INTEGER`.
    """
    ignored = _ignored_names(ignored_keys)
    _validate(left, _ROOT_PATH)
    _validate(right, _ROOT_PATH)
    return _same_value(left, right, ignored)
