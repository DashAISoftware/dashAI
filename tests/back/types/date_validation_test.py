import pandas as pd

from DashAI.back.types.type_validation import (
    validate_multiple_type_changes,
    validate_type_change,
)


def test_text_to_date_accepts_a_matching_format():
    column = pd.Series(["2020-01-31", "2020-02-29"])

    is_valid, message, converted = validate_type_change(
        column, "Text", "Date", "%Y-%m-%d"
    )

    assert is_valid, message
    # Storage is text, so the values must come back untouched.
    assert list(converted) == ["2020-01-31", "2020-02-29"]


def test_text_to_date_rejects_a_mismatched_format():
    column = pd.Series(["31/01/2020"])

    is_valid, message, _ = validate_type_change(column, "Text", "Date", "%Y-%m-%d")

    assert not is_valid
    assert "31/01/2020" in message


def test_text_to_date_detects_the_format_when_none_is_given():
    column = pd.Series(["31 January 2020", "01 February 2020"])

    is_valid, message, _ = validate_type_change(column, "Text", "Date", None)

    assert is_valid, message


def test_date_to_text_is_allowed():
    column = pd.Series(["2020-01-31"])

    is_valid, message, converted = validate_type_change(column, "Date", "Text")

    assert is_valid, message
    assert list(converted) == ["2020-01-31"]


def test_multiple_changes_report_the_resolved_date_format():
    data = pd.DataFrame({"when": ["01/02/2020", "05/02/2020", "13/02/2020"]})

    all_valid, errors, resolved = validate_multiple_type_changes(
        data, {"when": {"current_type": "Text", "new_type": "Date"}}
    )

    assert all_valid, errors
    assert resolved["when"] == "%d/%m/%Y"


def test_multiple_changes_report_an_unreadable_date_column():
    data = pd.DataFrame({"when": ["Q1 2020", "Q2 2020"]})

    all_valid, errors, resolved = validate_multiple_type_changes(
        data, {"when": {"current_type": "Text", "new_type": "Date"}}
    )

    assert not all_valid
    assert "when" in errors
    assert resolved == {}
