"""``reductionForecasterForm.json`` matches what the API serves the run form.

The reduction model's regressor is a nested form, which the run dialog draws
from the backend's schema with no code of its own (RECONCILING_FORECASTING
§8.6, slice 7). The jest test ``ReductionForecasterForm.test.jsx`` renders the
form from this file, instead of a hand-written copy of the schema, and checks
the parameters it submits against the file's ``payload``. This module keeps
both ends tied to the same file:

- the schemas and the list of regressors in the file are what the API serves
  today: a change to the model's schema fails here until the file is
  recorded again;
- the ``payload`` the form submits is accepted by ``POST /run/`` and trains.

Record the served part again with ``DASHAI_RECORD_REDUCTION_FORM=1``; the
``payload`` is kept, since it is what the front sends, not what the API
serves.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import json
import os
from pathlib import Path

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import Run
from DashAI.back.job.model_job import ModelJob
from tests.back.api.test_forecasting_acceptance import (
    _create_run,
    _get,
    _monthly,
    _session,
)

FIXTURE_PATH = (
    Path(__file__).parents[3]
    / "DashAI"
    / "front"
    / "src"
    / "components"
    / "models"
    / "__fixtures__"
    / "reductionForecasterForm.json"
)
RECORDING = os.environ.get("DASHAI_RECORD_REDUCTION_FORM") == "1"

MODEL = "RecursiveRegressionForecaster"
PARENT = "SklearnLikeRegressor"


def _served(client) -> dict:
    """What the run form asks the API for, as the API answers it."""

    def get(url, **params):
        response = client.get(url, params=params)
        assert response.status_code == 200, response.text
        return response.json()

    parents = get("/api/v1/component/", component_parent=PARENT)
    return {
        "model": get(f"/api/v1/component/{MODEL}/"),
        "regressor": get("/api/v1/component/LinearRegression/"),
        # The form lists them by name and reads nothing else of a regressor
        # it has not selected.
        "parents": sorted(
            (
                {"name": c["name"], "display_name": c.get("display_name")}
                for c in parents
            ),
            key=lambda c: c["name"],
        ),
    }


def test_the_reduction_form_fixture_is_what_the_api_serves(client):
    served = _served(client)

    if RECORDING:
        stored = (
            json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
            if FIXTURE_PATH.exists()
            else {}
        )
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(
            json.dumps({**stored, **served}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return

    stored = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert {key: stored[key] for key in served} == served, (
        f"{FIXTURE_PATH.name} is out of date with the API. Record it again "
        "with DASHAI_RECORD_REDUCTION_FORM=1 and commit the result."
    )


def test_the_parameters_the_form_submits_train_a_run(client, tmp_path):
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["payload"]
    session_id = _session(client, tmp_path, _monthly())

    run_id = _create_run(client, session_id, MODEL, payload)
    ModelJob(run_id=run_id).run()

    run = _get(client, Run, run_id)
    assert run.status == RunStatus.FINISHED
    # The form leaves the season empty, so on a monthly series the run reads
    # it from the frequency: twelve lags by default, as through the API.
    from DashAI.back.models.forecasting.recursive_regression import (
        RecursiveRegressionForecaster,
    )

    model = RecursiveRegressionForecaster.load(run.run_path)
    assert model.season_length == 12
    assert model.resolved_lags() == 12
