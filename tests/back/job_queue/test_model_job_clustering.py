"""Regression tests for the target free branch of ``ModelJob``.

Clustering runs take a different route through the job than every other task:
no splitter, no optimiser, no evaluation strategy, and metrics scored over the
whole dataset. These cover the two things that route gets wrong when left
alone: handing the models unscaled columns, and finishing a run that produced
nothing to report.
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.dependencies.database.models import Base, Metric
from DashAI.back.job.base_job import JobError
from DashAI.back.job.model_job import ModelJob
from DashAI.back.metrics.clustering.calinski_harabasz import CalinskiHarabasz
from DashAI.back.metrics.clustering.davies_bouldin import DaviesBouldin
from DashAI.back.metrics.clustering.silhouette import Silhouette
from DashAI.back.models.scikit_learn.dbscan_clustering import DBSCANClustering
from DashAI.back.models.scikit_learn.kmeans_clustering import KMeansClustering

METRICS = [Silhouette, CalinskiHarabasz, DaviesBouldin]


@pytest.fixture(name="db")
def fixture_db():
    """A throwaway session. Only the metric writes are exercised here, so the
    run is a stand in for its id rather than a real row."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def _mixed_scales(rows=60, seed=0):
    """Columns whose units are as far apart as a real tabular dataset's.

    ``score`` spans sixty units while ``hours`` spans ten, which is enough for
    the wider column to dominate every distance the models measure.
    """
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "hours": rng.uniform(1.0, 11.0, rows),
            "score": rng.uniform(40.0, 100.0, rows),
            "constant": np.ones(rows),
        }
    )
    # Spelled out rather than inferred: a dataset built without a schema
    # carries no DashAI types, and the task refuses to prepare one.
    return transform_dataset_with_schema(
        to_dashai_dataset(frame),
        {name: {"type": "Float", "dtype": "float64"} for name in frame.columns},
    )


def _blobs(per_centre=30, seed=0):
    rng = np.random.default_rng(seed)
    points = np.vstack(
        [
            rng.normal(loc=c, scale=0.1, size=(per_centre, 2))
            for c in [(0.0, 0.0), (10.0, 10.0)]
        ]
    )
    return to_dashai_dataset(pd.DataFrame({"x": points[:, 0], "y": points[:, 1]}))


def _preparation(model, x):
    return {"X": x, "factory": SimpleNamespace(model=model), "metrics": METRICS}


# --- the features the models are handed --------------------------------------


def test_every_numeric_column_is_centred_and_scaled():
    scaled = ModelJob._standardise_features(_mixed_scales()).to_pandas()

    for column in ("hours", "score"):
        assert scaled[column].mean() == pytest.approx(0.0, abs=1e-12)
        assert scaled[column].std(ddof=0) == pytest.approx(1.0)


def test_a_column_without_variance_is_left_where_it_is():
    """Dividing it by a zero standard deviation is what produces the NaNs the
    models then refuse, so it is skipped rather than scaled."""
    scaled = ModelJob._standardise_features(_mixed_scales()).to_pandas()

    assert (scaled["constant"] == 1.0).all()


def test_a_dataset_with_nothing_to_scale_is_returned_unchanged():
    x = to_dashai_dataset(pd.DataFrame({"constant": np.ones(5)}))

    assert ModelJob._standardise_features(x) is x


def test_the_row_and_column_shape_survives_scaling():
    x = _mixed_scales()

    scaled = ModelJob._standardise_features(x)

    assert scaled.to_pandas().shape == x.to_pandas().shape
    assert list(scaled.to_pandas().columns) == list(x.to_pandas().columns)


def test_scaling_is_what_lets_dbscan_find_anything_on_mixed_units():
    """The failure this guards against: with raw columns the default eps is far
    smaller than the spread of the widest one, so every row comes back noise."""
    x = _mixed_scales()

    raw = np.asarray(DBSCANClustering().train(x).get_cluster_labels(x))
    scaled_x = ModelJob._standardise_features(x)
    scaled = np.asarray(DBSCANClustering().train(scaled_x).get_cluster_labels(scaled_x))

    assert (raw == -1).all()
    assert (scaled != -1).any()


def test_the_prepare_step_scales_before_the_model_is_built(monkeypatch):
    """The helper above is only useful if the job actually calls it. Deleting
    the one line in ``_prepare_without_target`` is otherwise invisible, since
    nothing downstream fails, the results just get quietly worse.
    """
    from DashAI.back.tasks.clustering_task import ClusteringTask

    seen = []
    monkeypatch.setattr(
        ModelJob,
        "_standardise_features",
        staticmethod(lambda x: seen.append(x) or x),
    )

    class _Registry:
        """Answers the metric lookup and nothing else.

        The model lookup that follows the scaling is left to fail on purpose:
        by the time it does, the call under test has either happened or never
        will, so the job does not need to run any further than this.
        """

        @staticmethod
        def get_related_components(_task_name):
            return [{"name": m.__name__, "type": "Metric"} for m in METRICS]

        def __getitem__(self, name):
            return {"class": next(m for m in METRICS if m.__name__ == name)}

    # An instance without __init__: the method reaches the helper through self,
    # and nothing else on the job is touched before it does.
    job = ModelJob.__new__(ModelJob)

    with pytest.raises(JobError):
        job._prepare_without_target(
            run=SimpleNamespace(id=1, model_name="absent", parameters={}),
            model_session=SimpleNamespace(
                task_name="ClusteringTask", input_columns=["hours", "score"]
            ),
            dataset=SimpleNamespace(id=1),
            loaded_dataset=_mixed_scales(),
            task=ClusteringTask(),
            component_registry=_Registry(),
        )

    assert seen, "_prepare_without_target no escaló las columnas"


# --- runs that produced nothing to report ------------------------------------


def test_a_run_where_every_point_is_noise_fails_instead_of_finishing_empty(db):
    """Left alone the metrics answer None one by one, no row is written and the
    run reports success with an empty table and no reason given."""
    x = _mixed_scales()

    with pytest.raises(JobError, match="at least two clusters"):
        ModelJob._train_without_target(
            None, _preparation(DBSCANClustering(), x), run=SimpleNamespace(id=1), db=db
        )

    assert db.query(Metric).count() == 0


def test_the_failure_names_the_model_and_counts_the_noise(db):
    x = _mixed_scales()

    with pytest.raises(JobError) as raised:
        ModelJob._train_without_target(
            None, _preparation(DBSCANClustering(), x), run=SimpleNamespace(id=1), db=db
        )

    message = str(raised.value)
    assert "DBSCANClustering" in message
    assert "60 samples" in message
    assert "60 of them labelled as noise" in message


def test_a_run_that_finds_a_single_cluster_fails_too(db):
    """Not a noise problem: k means asked for one group has nothing to compare."""
    with pytest.raises(JobError, match="at least two clusters"):
        ModelJob._train_without_target(
            None,
            _preparation(KMeansClustering(n_clusters=1, random_state=0), _blobs()),
            run=SimpleNamespace(id=1),
            db=db,
        )


# --- runs that worked --------------------------------------------------------


def test_a_healthy_clustering_writes_one_row_per_metric(db):
    ModelJob._train_without_target(
        None,
        _preparation(KMeansClustering(n_clusters=2, random_state=0), _blobs()),
        run=SimpleNamespace(id=1),
        db=db,
    )

    rows = db.query(Metric).all()

    assert {row.name for row in rows} == {m.__name__ for m in METRICS}
    assert all(row.split == SplitEnum.FULL for row in rows)
    assert all(row.level == LevelEnum.LAST for row in rows)
    assert all(row.step == 0 for row in rows)


def test_the_fitted_model_is_handed_back_for_the_job_to_save(db):
    model = KMeansClustering(n_clusters=2, random_state=0)

    returned = ModelJob._train_without_target(
        None, _preparation(model, _blobs()), run=SimpleNamespace(id=1), db=db
    )

    assert returned is model


def test_training_again_replaces_the_previous_values_rather_than_adding_rows(db):
    x = _blobs()

    for seed in (0, 1):
        ModelJob._train_without_target(
            None,
            _preparation(KMeansClustering(n_clusters=2, random_state=seed), x),
            run=SimpleNamespace(id=1),
            db=db,
        )

    assert db.query(Metric).count() == len(METRICS)


def test_two_runs_of_the_same_session_keep_their_own_rows(db):
    x = _blobs()

    for run_id in (1, 2):
        ModelJob._train_without_target(
            None,
            _preparation(KMeansClustering(n_clusters=2, random_state=0), x),
            run=SimpleNamespace(id=run_id),
            db=db,
        )

    assert db.query(Metric).count() == 2 * len(METRICS)
