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


def test_the_inputs_after_the_time_index_are_exogenous_variables():
    # Exogenous variables are a role of this task, not a task apart
    # (RECONCILING_FORECASTING §2.14, decision 1): the first input is the time
    # index and every other one feeds the exogenous role.
    task = SingleSeriesForecastingTask()
    dataset = _dataset(date=DATES, sales=[1.0, 2.0, 3.0, 4.0], count=[1, 2, 3, 4])

    prepared = task.prepare_for_task(dataset, ["date", "count"], ["sales"])

    assert len(prepared) == 4
    assert task.roles_from_io(["date", "count"], ["sales"]) == {
        "time_index": ["date"],
        "exogenous": ["count"],
        "series": ["sales"],
    }


def test_an_exogenous_variable_that_is_not_a_number_is_rejected():
    # The role takes what the model reads: numbers. A date reaches it through
    # a converter that turns it into calendar numbers.
    dataset = _dataset(date=DATES, other_date=DATES, sales=[1.0, 2.0, 3.0, 4.0])

    with pytest.raises(TypeError, match="input columns"):
        SingleSeriesForecastingTask().prepare_for_task(
            dataset, ["date", "other_date"], ["sales"]
        )


def test_the_role_takes_any_number_of_exogenous_variables():
    task = SingleSeriesForecastingTask()

    io = task.io_columns(
        {"time_index": ["date"], "series": ["sales"], "exogenous": ["a", "b"]}
    )

    assert (io.inputs, io.outputs) == (["date", "a", "b"], ["sales"])
    assert task.io_columns({"time_index": ["date"], "series": ["sales"]}).inputs == [
        "date"
    ]


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
        "exogenous",
    ]
    assert metadata["io_roles"] == {
        "inputs": ["time_index", "exogenous"],
        "outputs": ["series"],
    }
    assert metadata["prediction_mode"] == "horizon"
    assert metadata["takes_preprocessing"] is True
    # The flat view of the x/y short form is not emitted any more.
    assert "inputs_types" not in metadata
    # One time index and any number of exogenous variables.
    assert SingleSeriesForecastingTask.inputs_cardinality() == "n"


def test_the_task_keeps_the_rows_its_preprocessing_is_given():
    from DashAI.back.tasks.base_task import BaseTask

    assert BaseTask.PREPROCESSING_KEEPS_ROWS is False
    assert SingleSeriesForecastingTask.PREPROCESSING_KEEPS_ROWS is True


def test_the_family_only_says_it_forecasts_forward():
    from DashAI.back.tasks.forecasting_task import ForecastingTask

    assert ForecastingTask.PREDICTS_FORWARD_ONLY is True
    assert SingleSeriesForecastingTask.PREDICTS_FORWARD_ONLY is True
    assert "PREDICTS_FORWARD_ONLY" not in SingleSeriesForecastingTask.__dict__
