import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.tasks.single_series_forecasting_task import (
    SingleSeriesForecastingTask,
)

DATES = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]


def _dataset(**columns):
    schema = {
        "date": {"type": "Date", "dtype": "%Y-%m-%d"},
        "other_date": {"type": "Date", "dtype": "%Y-%m-%d"},
        "sales": {"type": "Float", "dtype": "float64"},
        "count": {"type": "Integer", "dtype": "int64"},
        "label": {"type": "Text", "dtype": "string"},
    }
    frame = pd.DataFrame(columns)
    return transform_dataset_with_schema(
        to_dashai_dataset(frame), {name: schema[name] for name in frame.columns}
    )


def test_a_date_input_and_a_float_output_are_accepted():
    dataset = _dataset(date=DATES, sales=[1.0, 2.0, 3.0, 4.0])

    prepared = SingleSeriesForecastingTask().prepare_for_task(
        dataset, ["date"], ["sales"]
    )

    assert len(prepared) == 4


def test_an_integer_output_is_accepted():
    dataset = _dataset(date=DATES, count=[1, 2, 3, 4])

    prepared = SingleSeriesForecastingTask().prepare_for_task(
        dataset, ["date"], ["count"]
    )

    assert len(prepared) == 4


def test_a_text_input_is_rejected():
    dataset = _dataset(label=["a", "b", "c", "d"], sales=[1.0, 2.0, 3.0, 4.0])

    with pytest.raises(TypeError):
        SingleSeriesForecastingTask().prepare_for_task(dataset, ["label"], ["sales"])


def test_a_text_output_is_rejected():
    dataset = _dataset(date=DATES, label=["a", "b", "c", "d"])

    with pytest.raises(TypeError):
        SingleSeriesForecastingTask().prepare_for_task(dataset, ["date"], ["label"])


def test_a_second_input_column_is_rejected():
    # Exogenous variables are a separate task by design, so a second input is
    # refused here rather than quietly ignored.
    dataset = _dataset(date=DATES, other_date=DATES, sales=[1.0, 2.0, 3.0, 4.0])

    with pytest.raises(ValueError, match="Input cardinality"):
        SingleSeriesForecastingTask().prepare_for_task(
            dataset, ["date", "other_date"], ["sales"]
        )


def test_two_output_columns_are_rejected():
    dataset = _dataset(date=DATES, sales=[1.0, 2.0, 3.0, 4.0], count=[1, 2, 3, 4])

    with pytest.raises(ValueError, match="Output cardinality"):
        SingleSeriesForecastingTask().prepare_for_task(
            dataset, ["date"], ["sales", "count"]
        )


def test_it_has_no_labels_to_count_nor_predictions_to_decode():
    # Those serve the x/y units, which never train nor predict a series: the
    # backtest and the prediction by horizon read the values directly.
    assert not hasattr(SingleSeriesForecastingTask, "num_labels")
    assert not hasattr(SingleSeriesForecastingTask, "process_predictions")


def test_the_metadata_the_frontend_reads():
    metadata = SingleSeriesForecastingTask.get_metadata()

    assert [role["name"] for role in metadata["column_roles"]] == [
        "time_index",
        "series",
    ]
    assert metadata["io_roles"] == {"inputs": ["time_index"], "outputs": ["series"]}
    assert metadata["prediction_mode"] == "horizon"
    # The flat view of the x/y short form is not emitted any more.
    assert "inputs_types" not in metadata
    assert SingleSeriesForecastingTask.inputs_cardinality() == 1


def test_the_family_only_says_it_forecasts_forward():
    from DashAI.back.tasks.forecasting_task import ForecastingTask

    assert ForecastingTask.PREDICTS_FORWARD_ONLY is True
    assert SingleSeriesForecastingTask.PREDICTS_FORWARD_ONLY is True
    assert "PREDICTS_FORWARD_ONLY" not in SingleSeriesForecastingTask.__dict__
