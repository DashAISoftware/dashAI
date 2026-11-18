"""DateRangeConverter: the date column it adds, and what it refuses.

What it writes has to sit on the grid a forecast checks, read back the way
``SingleSeriesForecastingTask.prepare_series`` reads it: with the format the
column stores (RECONCILING_FORECASTING §9.3).
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.converters.dataset_columns import (
    rebuild_dataset_with_transformed_columns,
)
from DashAI.back.converters.simple_converters.date_range import DateRangeConverter
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.tasks.time_grid import validate_grid
from DashAI.back.types.date_utils import parse_date_column
from DashAI.back.types.value_types import Date

SCHEMA = {
    "sales": {"type": "Float", "dtype": "float64"},
    "store": {"type": "Categorical", "dtype": "string"},
}


def _dataset(n: int = 10, **extra):
    frame = pd.DataFrame(
        {
            "sales": [100.0 + i for i in range(n)],
            "store": [["a", "b"][i % 2] for i in range(n)],
            **extra,
        }
    )
    schema = {**SCHEMA, **{name: {"type": "Text", "dtype": "string"} for name in extra}}
    return transform_dataset_with_schema(to_dashai_dataset(frame), schema)


def _apply(dataset, **params):
    converter = DateRangeConverter(**params)
    return converter, converter.fit(dataset).transform(dataset)


def _read_back(result, name="date"):
    """The dates as a forecast reads them: parsed with the stored format."""
    date_format = result.types[name].format
    return parse_date_column(result.to_pandas()[name], date_format)


# --------------------------------------------------------------------------- #
# The column it adds
# --------------------------------------------------------------------------- #


def test_it_dates_every_row_from_the_start_and_leaves_the_rest_alone():
    dataset = _dataset(10)

    _, result = _apply(dataset)

    assert result.column_names == ["sales", "store", "date"]
    assert len(result) == len(dataset)
    table = result.to_pandas()
    assert table["sales"].tolist() == dataset.to_pandas()["sales"].tolist()
    assert table["store"].tolist() == dataset.to_pandas()["store"].tolist()
    for name in ("sales", "store"):
        assert result.types[name].to_string() == dataset.types[name].to_string()
    expected = pd.date_range("2024-01-01", periods=10, freq="D")
    assert table["date"].tolist() == list(expected.strftime("%Y-%m-%d"))


def test_the_new_column_is_a_date_with_its_format():
    _, result = _apply(_dataset(5))

    assert isinstance(result.types["date"], Date)
    assert result.types["date"].format == "%Y-%m-%d"


@pytest.mark.parametrize(
    ("start", "frequency", "date_format"),
    [
        ("2024-01-01", "MS", "%Y-%m-%d"),
        ("2024-01-01 08:30", "D", "%Y-%m-%d %H:%M:%S"),
        ("2024-01-01", "h", "%Y-%m-%d %H:%M:%S"),
        ("2024-01-01", "ms", "%Y-%m-%d %H:%M:%S.%f"),
        ("2024-01-01", "us", "%Y-%m-%d %H:%M:%S.%f"),
    ],
    ids=["midnight", "daily-from-08:30", "hourly", "milliseconds", "microseconds"],
)
def test_the_format_keeps_every_part_the_dates_have(start, frequency, date_format):
    converter, result = _apply(_dataset(10), start_date=start, frequency=frequency)

    assert result.types["date"].format == date_format
    assert converter.get_output_type().format == date_format


@pytest.mark.parametrize(
    "frequency",
    [
        "D",
        "h",
        "15min",
        "s",
        "ms",
        "us",
        "W-MON",
        "7D",
        "MS",
        "ME",
        "QS",
        "YS",
        "B",
        "2MS",
    ],
)
def test_what_it_writes_sits_on_the_grid_a_forecast_checks(frequency):
    import pandas.tseries.frequencies as frequencies

    offset = frequencies.to_offset(frequency)
    start = pd.Timestamp(offset.rollforward(pd.Timestamp("2024-01-01")))
    dataset = _dataset(24)

    _, result = _apply(dataset, start_date=f"{start:%Y-%m-%d}", frequency=frequency)

    grid = validate_grid(_read_back(result), pd.Series(np.zeros(24)))
    assert grid.n_steps == 24
    assert grid.first == start


# --------------------------------------------------------------------------- #
# What it refuses
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({"start_date": "01/02/2024"}, "is not in the form YYYY-MM-DD"),
        ({"start_date": "2024-13-01"}, "is not in the form YYYY-MM-DD"),
        ({"frequency": "foo"}, "'foo' is not a pandas frequency. Examples: D"),
        ({"frequency": ""}, "is not a pandas frequency"),
        ({"frequency": "-1D"}, "must move forward in time; got '-1D'"),
        ({"frequency": "0D"}, "must move forward in time; got '0D'"),
        (
            {"frequency": "MS", "start_date": "2024-01-15"},
            "2024-01-15 is not one. The next one is 2024-02-01",
        ),
        (
            {"frequency": "W-SUN", "start_date": "2024-01-03"},
            "The next one is 2024-01-07",
        ),
        ({"column_name": "  "}, "The new column needs a name."),
    ],
    ids=[
        "day-first-start",
        "impossible-start",
        "unknown-frequency",
        "empty-frequency",
        "backwards",
        "no-step",
        "off-month-anchor",
        "off-week-anchor",
        "blank-name",
    ],
)
def test_fit_refuses_settings_it_cannot_honour(params, message):
    with pytest.raises(ValueError, match=message.replace("(", r"\(")):
        DateRangeConverter(**params).fit(_dataset(5))


def test_it_refuses_a_dataset_without_rows():
    dataset = _dataset(0)
    converter = DateRangeConverter().fit(dataset)

    with pytest.raises(ValueError, match="no rows to date"):
        converter.transform(dataset)


@pytest.mark.parametrize("n", [1, 2])
def test_it_refuses_fewer_rows_than_a_frequency_is_inferred_from(n):
    dataset = _dataset(n)
    converter = DateRangeConverter().fit(dataset)

    with pytest.raises(ValueError, match=f"at least 3 rows; this dataset has {n}"):
        converter.transform(dataset)


def test_it_refuses_dates_past_the_last_one_pandas_holds():
    dataset = _dataset(500)
    converter = DateRangeConverter(start_date="2000-01-01", frequency="YS").fit(dataset)

    with pytest.raises(ValueError, match="reach past 2262-04-11"):
        converter.transform(dataset)


def test_it_refuses_steps_finer_than_a_microsecond():
    dataset = _dataset(10)
    converter = DateRangeConverter(frequency="ns").fit(dataset)

    with pytest.raises(ValueError, match="finer than a microsecond"):
        converter.transform(dataset)


def test_it_refuses_a_frequency_a_forecast_cannot_read_back():
    dataset = _dataset(24)
    converter = DateRangeConverter(frequency="SMS").fit(dataset)

    with pytest.raises(
        ValueError,
        match="pandas can generate frequency 'SMS' but a forecast cannot read it back",
    ):
        converter.transform(dataset)


# --------------------------------------------------------------------------- #
# Names
# --------------------------------------------------------------------------- #


def test_a_name_taken_in_the_scope_is_numbered():
    dataset = _dataset(5, date=list("abcde"))

    _, result = _apply(dataset)

    assert result.column_names == ["sales", "store", "date", "date_1"]
    assert result.to_pandas()["date"].tolist() == list("abcde")
    assert isinstance(result.types["date_1"], Date)


def test_the_first_free_number_is_taken():
    dataset = _dataset(5, date=list("abcde"), date_1=list("vwxyz"))

    _, result = _apply(dataset)

    assert result.column_names[-1] == "date_2"


def test_with_an_explicit_scope_the_merge_numbers_a_name_outside_it():
    """Through the API a scope can be explicit: a name taken outside it is
    numbered by the merge, the way it numbers every converter's columns."""
    dataset = _dataset(5, date=list("abcde"))
    scope = dataset.select_columns(["sales"])

    _, transformed = _apply(scope)
    result = rebuild_dataset_with_transformed_columns(
        dataset, transformed, ["sales"], [0]
    )

    assert result.column_names == ["sales", "store", "date", "date_1"]
    assert result.to_pandas()["date"].tolist() == list("abcde")


def test_a_row_scope_narrows_the_fit_and_the_column_covers_every_row():
    dataset = _dataset(10)
    converter = DateRangeConverter().fit(dataset.select([0, 1]))

    result = converter.transform(dataset)

    assert len(result.to_pandas()["date"]) == 10


# --------------------------------------------------------------------------- #
# Declarations
# --------------------------------------------------------------------------- #


def test_it_runs_in_a_notebook_only_and_reads_no_column():
    metadata = DateRangeConverter.get_metadata()

    assert DateRangeConverter.NOTEBOOK_ONLY is True
    assert DateRangeConverter.runs_in_session() is False
    assert DateRangeConverter.CHANGES_ROW_COUNT is False
    assert metadata["input_cardinality"] == {"exact": 0}
    assert metadata["data_kinds"] == ["dataset"]
    assert metadata["learns_from_data"] is False
    assert "notebook_only" not in metadata
    assert "runs_in_session" not in metadata


def test_its_schema_shows_the_three_defaults():
    properties = DateRangeConverter.get_schema()["properties"]

    assert {name: field["placeholder"] for name, field in properties.items()} == {
        "start_date": "2024-01-01",
        "frequency": "D",
        "column_name": "date",
    }
