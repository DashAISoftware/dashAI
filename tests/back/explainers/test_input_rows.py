"""Tests for serializing a local explainer's original input rows."""

from datasets import Dataset

from DashAI.back.explainability.input_rows import serialize_local_input_rows


def test_serialize_tabular_rows_preserves_order_and_columns():
    dataset = Dataset.from_dict(
        {
            "age": [30, 41, 25],
            "city": ["NY", "LA", "SF"],
            "label": [0, 1, 0],
        }
    )
    result = serialize_local_input_rows(dataset, ["age", "city"])

    assert result["kind"] == "tabular"
    assert result["columns"] == ["age", "city"]
    assert [i["values"] for i in result["instances"]] == [
        [30, "NY"],
        [41, "LA"],
        [25, "SF"],
    ]
    # One entry per row, and the output column is excluded.
    assert len(result["instances"]) == 3
    assert all(i["kind"] == "tabular" for i in result["instances"])


def test_serialize_tabular_rows_only_includes_requested_columns():
    dataset = Dataset.from_dict({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    result = serialize_local_input_rows(dataset, ["a", "c"])

    assert result["columns"] == ["a", "c"]
    assert [i["values"] for i in result["instances"]] == [[1, 5], [2, 6]]
