import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.tasks.exogenous_forecasting_task import ExogenousForecastingTask

DATES = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]

SCHEMA = {
    "date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "other_date": {"type": "Date", "dtype": "%Y-%m-%d"},
    "sales": {"type": "Float", "dtype": "float64"},
    "price": {"type": "Float", "dtype": "float64"},
    "promo": {"type": "Integer", "dtype": "int64"},
    "label": {"type": "Text", "dtype": "string"},
}


def _dataset(**columns):
    frame = pd.DataFrame(columns)
    return transform_dataset_with_schema(
        to_dashai_dataset(frame), {name: SCHEMA[name] for name in frame.columns}
    )


def test_a_date_and_one_exogenous_variable_are_accepted():
    dataset = _dataset(
        date=DATES, price=[1.0, 2.0, 3.0, 4.0], sales=[10.0, 11.0, 12.0, 13.0]
    )

    prepared = ExogenousForecastingTask().prepare_for_task(
        dataset, ["date", "price"], ["sales"]
    )

    assert len(prepared) == 4


def test_any_number_of_exogenous_variables_is_accepted():
    dataset = _dataset(
        date=DATES,
        price=[1.0, 2.0, 3.0, 4.0],
        promo=[0, 1, 0, 1],
        sales=[10.0, 11.0, 12.0, 13.0],
    )

    prepared = ExogenousForecastingTask().prepare_for_task(
        dataset, ["date", "price", "promo"], ["sales"]
    )

    assert len(prepared) == 4


def test_the_date_column_may_come_last():
    dataset = _dataset(
        date=DATES, price=[1.0, 2.0, 3.0, 4.0], sales=[10.0, 11.0, 12.0, 13.0]
    )

    prepared = ExogenousForecastingTask().prepare_for_task(
        dataset, ["price", "date"], ["sales"]
    )

    assert len(prepared) == 4


def test_a_date_on_its_own_is_rejected():
    dataset = _dataset(date=DATES, sales=[10.0, 11.0, 12.0, 13.0])

    with pytest.raises(ValueError, match="Input cardinality"):
        ExogenousForecastingTask().prepare_for_task(dataset, ["date"], ["sales"])


def test_exogenous_variables_without_a_date_are_rejected():
    dataset = _dataset(price=[1.0, 2.0, 3.0, 4.0], sales=[10.0, 11.0, 12.0, 13.0])

    with pytest.raises(ValueError, match="Input cardinality"):
        ExogenousForecastingTask().prepare_for_task(dataset, ["price"], ["sales"])


def test_a_second_date_column_is_rejected():
    dataset = _dataset(
        date=DATES,
        other_date=DATES,
        price=[1.0, 2.0, 3.0, 4.0],
        sales=[10.0, 11.0, 12.0, 13.0],
    )

    with pytest.raises(ValueError, match="Input cardinality"):
        ExogenousForecastingTask().prepare_for_task(
            dataset, ["date", "other_date", "price"], ["sales"]
        )


def test_a_text_variable_is_rejected():
    dataset = _dataset(
        date=DATES, label=["a", "b", "c", "d"], sales=[10.0, 11.0, 12.0, 13.0]
    )

    with pytest.raises(TypeError):
        ExogenousForecastingTask().prepare_for_task(
            dataset, ["date", "label"], ["sales"]
        )


def test_two_output_columns_are_rejected():
    dataset = _dataset(
        date=DATES,
        price=[1.0, 2.0, 3.0, 4.0],
        promo=[0, 1, 0, 1],
        sales=[10.0, 11.0, 12.0, 13.0],
    )

    with pytest.raises(ValueError, match="Output cardinality"):
        ExogenousForecastingTask().prepare_for_task(
            dataset, ["date", "price"], ["sales", "promo"]
        )


def test_the_rows_come_back_in_date_order():
    dataset = _dataset(
        date=["2026-01-03", "2026-01-01", "2026-01-04", "2026-01-02"],
        price=[3.0, 1.0, 4.0, 2.0],
        sales=[30.0, 10.0, 40.0, 20.0],
    )

    prepared = ExogenousForecastingTask().prepare_for_task(
        dataset, ["price", "date"], ["sales"]
    )

    frame = prepared.to_pandas()
    assert list(frame["date"]) == DATES
    assert list(frame["price"]) == [1.0, 2.0, 3.0, 4.0]
    assert list(frame["sales"]) == [10.0, 20.0, 30.0, 40.0]


def test_it_reports_no_labels():
    dataset = _dataset(
        date=DATES, price=[1.0, 2.0, 3.0, 4.0], sales=[10.0, 11.0, 12.0, 13.0]
    )

    assert ExogenousForecastingTask().num_labels(dataset, "sales") is None


def test_predictions_pass_through_unchanged():
    import numpy as np

    dataset = _dataset(
        date=DATES, price=[1.0, 2.0, 3.0, 4.0], sales=[10.0, 11.0, 12.0, 13.0]
    )
    predictions = np.array([1.5, 2.5])

    processed = ExogenousForecastingTask().process_predictions(
        dataset, predictions, "sales"
    )

    assert list(processed) == [1.5, 2.5]


def test_it_only_predicts_forward():
    assert ExogenousForecastingTask.PREDICTS_FORWARD_ONLY is True


def test_the_metadata_the_frontend_reads():
    metadata = ExogenousForecastingTask.get_metadata()

    assert metadata["inputs"] == [
        {"types": ["Date"], "min": 1, "max": 1},
        {"types": ["Float", "Integer"], "min": 1, "max": "n"},
    ]
    assert metadata["outputs"] == [{"types": ["Float", "Integer"], "min": 1, "max": 1}]
    assert metadata["inputs_types"] == ["Date", "Float", "Integer"]
    assert metadata["inputs_cardinality"] == "n"
    assert metadata["outputs_cardinality"] == 1
