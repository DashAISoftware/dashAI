"""A notebook encoder refuses a category it did not see in fit, unless asked.

A notebook converter with a row scope is fitted on those rows and applied to
every row of the dataset, and what it writes is saved. So, unlike a session,
which declares its own defaults (``SESSION_PARAMS``), the notebook keeps the
encoders strict: a category outside the fitted rows stops the job with a
message that names the converter, the column and the values. A user who asks
for it explicitly gets the category treated.

Iris rows 1 to 3 are all ``Iris-setosa``, so fitted on them an encoder of
``Species`` meets the two other species in the rest of the rows.
"""

import pytest

from DashAI.back.core.enums.status import ConverterStatus
from DashAI.back.job.base_job import JobError
from DashAI.back.job.converter_job import ConverterJob
from tests.back.api.test_converter_job import (  # noqa: F401
    IRIS_COLUMNS,
    IRIS_ROWS,
    _notebook_dataset,
    _stored_converter,
    create_notebook,
)

SPECIES = {"idx": IRIS_COLUMNS.index("Species") + 1}
SETOSA_ROWS = [1, 2, 3]
HINTS = {
    "OneHotEncoder": 'set "handle_unknown" to "ignore"',
    "OrdinalEncoder": 'set "handle_unknown" to "use_encoded_value"',
}


def _converter(client, notebook, name, params, rows):
    response = client.post(
        "/api/v1/converter/",
        json={
            "notebook_id": notebook["id"],
            "converter": name,
            "parameters": {
                "order": 0,
                "params": params,
                "scope": {"columns": [SPECIES], "rows": rows},
                "target": None,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _added_column(notebook):
    """The one column the encoder appended, as a list."""
    dataset = _notebook_dataset(notebook)
    (added,) = [name for name in dataset.column_names if name not in IRIS_COLUMNS]
    return dataset[added]


@pytest.mark.parametrize("name", sorted(HINTS))
def test_a_category_outside_the_fitted_rows_stops_the_job(client, notebook, name):
    converter_id = _converter(client, notebook, name, {}, SETOSA_ROWS)

    with pytest.raises(JobError, match="cannot encode values") as error:
        ConverterJob(converter_id=converter_id).run()

    message = str(error.value)
    assert f"{name} cannot encode values of column 'Species'" in message
    assert "were not in the rows it was fitted on" in message
    assert "'Iris-versicolor', 'Iris-virginica'" in message
    assert HINTS[name] in message
    assert _stored_converter(client, converter_id)["status"] == ConverterStatus.ERROR
    assert _notebook_dataset(notebook).column_names == IRIS_COLUMNS


@pytest.mark.parametrize("name", sorted(HINTS))
def test_without_a_row_scope_every_category_is_seen(client, notebook, name):
    converter_id = _converter(client, notebook, name, {}, [])

    ConverterJob(converter_id=converter_id).run()

    assert _stored_converter(client, converter_id)["status"] == (
        ConverterStatus.FINISHED
    )


def test_one_hot_asked_to_ignore_gives_zeros_outside_the_fitted_rows(client, notebook):
    converter_id = _converter(
        client, notebook, "OneHotEncoder", {"handle_unknown": "ignore"}, SETOSA_ROWS
    )

    ConverterJob(converter_id=converter_id).run()

    encoded = _added_column(notebook)
    assert len(encoded) == IRIS_ROWS
    assert encoded[0] == 1
    assert encoded[-1] == 0


def test_ordinal_asked_to_encode_gives_its_unknown_value_outside_the_fitted_rows(
    client, notebook
):
    converter_id = _converter(
        client,
        notebook,
        "OrdinalEncoder",
        {"handle_unknown": "use_encoded_value", "unknown_value": -1},
        SETOSA_ROWS,
    )

    ConverterJob(converter_id=converter_id).run()

    encoded = _added_column(notebook)
    assert encoded[0] == 0
    assert encoded[-1] == -1
