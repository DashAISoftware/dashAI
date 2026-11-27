import pandas as pd

from DashAI.back.converters.dataset_columns import (
    rebuild_dataset_with_transformed_columns,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)


def _dataset(columns, schema):
    return transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame(columns)), schema
    )


def test_replaces_scoped_column_in_place_and_keeps_others():
    base = _dataset(
        {"a": [1, 2, 3], "b": [10, 20, 30]},
        {
            "a": {"type": "Integer", "dtype": "int64"},
            "b": {"type": "Integer", "dtype": "int64"},
        },
    )
    transformed = _dataset(
        {"a": [0, 1, 0]},
        {"a": {"type": "Integer", "dtype": "int64"}},
    )

    result = rebuild_dataset_with_transformed_columns(base, transformed, ["a"], [0])

    assert result.column_names == ["a", "b"]
    assert result.to_pandas()["a"].tolist() == [0, 1, 0]
    assert result.to_pandas()["b"].tolist() == [10, 20, 30]


def test_appends_new_columns_not_in_the_scope():
    base = _dataset(
        {"a": [1, 2, 3]},
        {"a": {"type": "Integer", "dtype": "int64"}},
    )
    transformed = _dataset(
        {"a_bin_0": [1, 0, 1], "a_bin_1": [0, 1, 0]},
        {
            "a_bin_0": {"type": "Integer", "dtype": "int64"},
            "a_bin_1": {"type": "Integer", "dtype": "int64"},
        },
    )

    result = rebuild_dataset_with_transformed_columns(base, transformed, ["a"], [0])

    assert result.column_names == ["a_bin_0", "a_bin_1"]


def _int_schema(*names):
    return {name: {"type": "Integer", "dtype": "int64"} for name in names}


def _bag_of_words_case(transformed_columns):
    base = _dataset(
        {"text": [1, 2, 3], "age": [30, 40, 50]}, _int_schema("text", "age")
    )
    transformed = _dataset(transformed_columns, _int_schema(*transformed_columns))
    return base, transformed


def test_drops_requested_scope_columns_and_keeps_the_new_ones():
    base, transformed = _bag_of_words_case(
        {"text": [1, 2, 3], "w_hola": [1, 0, 1], "w_chao": [0, 1, 0]}
    )

    result = rebuild_dataset_with_transformed_columns(
        base, transformed, ["text"], [0], columns_to_drop=["text"]
    )

    assert result.column_names == ["age", "w_hola", "w_chao"]
    assert "text" not in result.types
    assert result.to_pandas()["w_hola"].tolist() == [1, 0, 1]


def test_dropping_a_column_the_converter_already_removed_is_harmless():
    base, transformed = _bag_of_words_case({"w_hola": [1, 0, 1], "w_chao": [0, 1, 0]})

    result = rebuild_dataset_with_transformed_columns(
        base, transformed, ["text"], [0], columns_to_drop=["text"]
    )

    assert result.column_names == ["age", "w_hola", "w_chao"]
    assert "text" not in result.types


def _scope_all_case(transformed_columns, transformed_schema):
    """A converter run on an empty notebook scope, which means every column."""
    base = _dataset(
        {"date": ["a", "b", "c"], "sales": [1.5, 2.5, 3.5]},
        {
            "date": {"type": "Text", "dtype": "string"},
            "sales": {"type": "Float", "dtype": "float64"},
        },
    )
    transformed = _dataset(transformed_columns, transformed_schema)
    return base, transformed


def test_scope_columns_returned_unchanged_keep_their_values_and_types():
    base, transformed = _scope_all_case(
        {"date": ["a", "b", "c"], "sales": [1.5, 2.5, 3.5], "new": [1, 2, 3]},
        {
            "date": {"type": "Text", "dtype": "string"},
            "sales": {"type": "Float", "dtype": "float64"},
            "new": {"type": "Integer", "dtype": "int64"},
        },
    )

    result = rebuild_dataset_with_transformed_columns(
        base, transformed, ["date", "sales"], [0, 1]
    )

    assert result.column_names == ["date", "sales", "new"]
    assert result.to_pandas()["date"].tolist() == ["a", "b", "c"]
    assert result.to_pandas()["sales"].tolist() == [1.5, 2.5, 3.5]
    assert result.types["date"].to_string() == base.types["date"].to_string()
    assert result.types["sales"].to_string() == base.types["sales"].to_string()


def test_a_new_column_named_like_a_scope_column_replaces_it_unnumbered():
    """Only names outside the scope are numbered: a converter whose scope is
    every column has to number its own new columns."""
    base, transformed = _scope_all_case(
        {"date": [7, 8, 9], "sales": [1.5, 2.5, 3.5]},
        {
            "date": {"type": "Integer", "dtype": "int64"},
            "sales": {"type": "Float", "dtype": "float64"},
        },
    )

    result = rebuild_dataset_with_transformed_columns(
        base, transformed, ["date", "sales"], [0, 1]
    )

    assert result.column_names == ["date", "sales"]
    assert result.to_pandas()["date"].tolist() == [7, 8, 9]


def test_a_new_column_named_like_one_outside_the_scope_is_numbered():
    base, transformed = _scope_all_case(
        {"sales": [1.5, 2.5, 3.5], "date": [7, 8, 9]},
        {
            "sales": {"type": "Float", "dtype": "float64"},
            "date": {"type": "Integer", "dtype": "int64"},
        },
    )

    result = rebuild_dataset_with_transformed_columns(base, transformed, ["sales"], [1])

    assert result.column_names == ["date", "sales", "date_1"]
    assert result.to_pandas()["date"].tolist() == ["a", "b", "c"]
    assert result.to_pandas()["date_1"].tolist() == [7, 8, 9]


def test_without_columns_to_drop_the_result_is_unchanged():
    base, transformed = _bag_of_words_case(
        {"text": [1, 2, 3], "w_hola": [1, 0, 1], "w_chao": [0, 1, 0]}
    )

    result = rebuild_dataset_with_transformed_columns(base, transformed, ["text"], [0])

    assert result.column_names == ["text", "age", "w_hola", "w_chao"]
