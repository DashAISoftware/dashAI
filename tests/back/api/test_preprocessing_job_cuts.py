"""``PreprocessingJob`` fits a forecasting session once per cut of its backtest.

A backtest cuts a series in steps, not rows, so the splitter's ``split`` is
not there to call (``OriginSplitter.split`` raises). The job validates the
series' grid first, with the task's own ``prepare_series`` and its message
(D5), and then fits one preprocessor per cut on the steps before it
(RECONCILING_FORECASTING §2.14, decision 4 and detail 8):

- ``origin_{i}.pkl`` on the steps before validation origin ``i``;
- ``test.pkl`` on the steps before the test origin;
- ``final.pkl`` on the whole series, as the final model is (D4).

The series is uploaded shuffled, so a fit on the loaded order would see other
rows than the ones before its cut.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

import os

import numpy as np
import pytest

from DashAI.back.dependencies.database.models import ModelSession
from DashAI.back.preprocessing.session_preprocessor import SessionPreprocessor
from tests.back.api.test_forecasting_acceptance import (
    CV,
    HOLDOUT,
    HOLDOUT_STRATEGY,
    ROLLING,
    _create_run,
    _get,
    _monthly,
    _session_body,
    _upload,
)

SCALE_PROMO = {
    "converter": "StandardScaler",
    "params": {},
    "scope": [{"kind": "raw", "name": "promo"}],
}
EXOGENOUS = [{"kind": "raw", "name": "promo"}]


def _frame():
    frame = _monthly().assign(promo=np.arange(48, dtype=float))
    return frame.sample(frac=1.0, random_state=0).reset_index(drop=True)


def _create(client, tmp_path, frame, strategy, splits):
    dataset_id = _upload(client, frame, tmp_path, f"cuts-{tmp_path.name}")
    body = _session_body(
        dataset_id, strategy=strategy, splits=splits, preprocessing=[SCALE_PROMO]
    )
    body["column_roles"]["exogenous"] = EXOGENOUS
    return client.post("/api/v1/model-session/", json=body)


@pytest.mark.parametrize(
    ("strategy", "splits", "artifacts", "cuts"),
    [
        (
            CV,
            ROLLING,
            ["origin_0.pkl", "origin_1.pkl", "origin_2.pkl", "test.pkl"],
            [36, 39, 42, 45],
        ),
        (HOLDOUT_STRATEGY, HOLDOUT, ["origin_0.pkl", "test.pkl"], [42, 45]),
    ],
    ids=["rolling", "holdout"],
)
def test_each_cut_is_fitted_on_the_steps_before_it(
    client, tmp_path, monkeypatch, strategy, splits, artifacts, cuts
):
    fitted_on = []
    original_fit_transform = SessionPreprocessor.fit_transform

    def recording_fit_transform(self, split):
        fitted_on.append(
            {name: entry.to_pandas()["date"].tolist() for name, entry in split.items()}
        )
        return original_fit_transform(self, split)

    monkeypatch.setattr(SessionPreprocessor, "fit_transform", recording_fit_transform)

    response = _create(client, tmp_path, _frame(), strategy, splits)

    assert response.status_code == 201, response.text
    assert response.json()["preprocessing_status"] == "ready", response.text
    in_date_order = _monthly()["date"].tolist()
    # One fit per cut, in cut order, then the final one on the whole series,
    # each on nothing but its training steps, in date order.
    assert fitted_on == [{"train": in_date_order[:cut]} for cut in cuts] + [
        {"train": in_date_order}
    ]
    session = _get(client, ModelSession, response.json()["id"])
    assert sorted(os.listdir(session.preprocessing_artifacts_path)) == sorted(
        [*artifacts, "final.pkl"]
    )


def test_the_session_stores_the_exogenous_columns_the_chain_resolved(client, tmp_path):
    response = _create(client, tmp_path, _frame(), CV, ROLLING)

    assert response.status_code == 201, response.text
    session = _get(client, ModelSession, response.json()["id"])
    roles = {name: role["columns"] for name, role in session.column_roles.items()}
    assert roles == {
        "time_index": ["date"],
        "series": ["sales"],
        "exogenous": ["promo"],
    }


def test_a_series_off_its_grid_fails_before_anything_is_fitted(
    client, tmp_path, monkeypatch
):
    # A guard, green before the cuts too: preparing the dataset already
    # validated the grid. It pins that the cuts keep that order.
    fits = []
    monkeypatch.setattr(
        SessionPreprocessor, "fit_transform", lambda self, split: fits.append(split)
    )
    frame = _monthly().assign(promo=np.arange(48, dtype=float))
    frame.loc[5, "date"] = frame.loc[4, "date"]

    response = _create(client, tmp_path, frame, CV, ROLLING)

    session = _get(client, ModelSession, response.json()["id"])
    assert session.preprocessing_status == "failed"
    # The task's own message, the one a run gives inside its JobError (D5).
    assert session.preprocessing_error.startswith(
        "The time index repeats 1 date(s): 2020-05-01."
    )
    assert fits == []


def test_a_session_package_carries_every_cut(client, tmp_path):
    from DashAI.back.session_package.export import build_session_package
    from DashAI.back.session_package.load import import_session_package

    container = client.app.container
    response = _create(client, tmp_path, _frame(), CV, ROLLING)
    assert response.status_code == 201, response.text
    session_id = response.json()["id"]
    # A recipe is enough: the artifacts belong to the session, not the run.
    run_id = _create_run(client, session_id, "NaiveForecaster")
    package = tmp_path / "cuts.dashai"
    build_session_package(
        session_id,
        [run_id],
        False,
        package,
        container["session_factory"],
        container["component_registry"],
    )

    result = import_session_package(
        package,
        container["session_factory"],
        container["component_registry"],
        container["config"],
        container["job_queue"],
    )

    imported = _get(client, ModelSession, result["session_id"])
    assert imported.preprocessing_status == "ready"
    assert sorted(os.listdir(imported.preprocessing_artifacts_path)) == [
        "final.pkl",
        "origin_0.pkl",
        "origin_1.pkl",
        "origin_2.pkl",
        "test.pkl",
    ]
