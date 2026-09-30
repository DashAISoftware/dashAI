from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.job.predict_job import _run_prediction_pipeline

SCHEMA = {
    "age": {"type": "Integer", "dtype": "int64"},
    "height": {"type": "Float", "dtype": "float64"},
}

SESSION = SimpleNamespace(
    preprocessing=None, input_columns=["age", "height"], output_columns=["label"]
)


def _rows(ages):
    frame = pd.DataFrame(
        {"age": pd.array(ages, dtype="Int64"), "height": [1.7] * len(ages)}
    )
    return transform_dataset_with_schema(to_dashai_dataset(frame), SCHEMA)


class _Model:
    """Stands in for a trained model; raises `error` if one is given."""

    def __init__(self, error=None):
        self.error = error

    def predict(self, x):
        if self.error is not None:
            raise self.error
        return np.zeros((x.num_rows, 2))


class _Task:
    def process_predictions(self, train_dataset, y_pred_proba, output_column):
        return list(y_pred_proba.argmax(axis=1))


def test_a_model_failing_on_missing_values_gets_a_clear_message():
    model = _Model(ValueError("Input X contains NaN."))

    with pytest.raises(ValueError, match="Row 2: age"):
        _run_prediction_pipeline(_Task(), model, None, _rows([30, None]), SESSION)


def test_a_model_that_accepts_missing_values_still_predicts():
    _, y_pred = _run_prediction_pipeline(
        _Task(), _Model(), None, _rows([30, None]), SESSION
    )

    assert len(y_pred) == 2


def test_an_unrelated_failure_keeps_its_own_error():
    model = _Model(RuntimeError("out of memory"))

    with pytest.raises(RuntimeError, match="out of memory"):
        _run_prediction_pipeline(_Task(), model, None, _rows([30]), SESSION)
