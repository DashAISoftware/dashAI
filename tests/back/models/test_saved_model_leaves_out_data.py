"""A saved model carries the model, not the data it was scored on.

Whoever fits a model points ``x_data`` and ``y_data`` at its splits so the
metric methods can read them. Models that save themselves by pickling used to
write those datasets into the artifact as well, which made the save grow with
the dataset: a large one took about a minute to write.
"""

import pickle

import numpy as np
import pandas as pd
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.models.faiss.faiss_kmeans_clustering import FaissKMeansClustering
from DashAI.back.models.scikit_learn.kmeans_clustering import KMeansClustering

# One model that pickles itself through scikit-learn's state and one with its
# own ``__getstate__`` (the FAISS index), which has to defer to the base one.
MODELS = [KMeansClustering, FaissKMeansClustering]


def _data(rows=300, seed=0):
    rng = np.random.default_rng(seed)
    return to_dashai_dataset(
        pd.DataFrame({"x": rng.normal(size=rows), "y": rng.normal(size=rows)})
    )


def _fitted(model_class):
    x = _data()
    model = model_class(n_clusters=3, random_state=0)
    model.train(x)
    model.x_data = {"train": x, "validation": x, "test": x}
    model.y_data = {"train": x, "validation": x, "test": x}
    return model


@pytest.mark.parametrize("model_class", MODELS)
def test_the_saved_model_does_not_carry_its_data(model_class, tmp_path):
    model = _fitted(model_class)
    path = tmp_path / "model.joblib"

    model.save(str(path))
    restored = model_class.load(str(path))

    assert restored.x_data is None
    assert restored.y_data is None


@pytest.mark.parametrize("model_class", MODELS)
def test_the_saved_model_size_does_not_grow_with_the_data(model_class, tmp_path):
    model = _fitted(model_class)
    small, large = tmp_path / "small.joblib", tmp_path / "large.joblib"

    model.save(str(small))
    # Fifty thousand rows of two float64 columns: 800 KB per split, so either
    # attribute leaking into the artifact would dwarf the tolerance below.
    big = _data(rows=50_000)
    model.x_data = {"train": big, "validation": big, "test": big}
    model.y_data = {"train": big, "validation": big, "test": big}
    model.save(str(large))

    assert large.stat().st_size < small.stat().st_size + 10_000


def test_a_model_without_attributes_can_still_be_pickled():
    """``object.__getstate__`` gives None, not a dict, for an empty instance."""
    model = FaissKMeansClustering.__new__(FaissKMeansClustering)

    restored = pickle.loads(pickle.dumps(model))

    assert restored.x_data is None


@pytest.mark.parametrize("model_class", MODELS)
def test_saving_leaves_the_live_model_pointed_at_its_data(model_class, tmp_path):
    model = _fitted(model_class)
    x_data = model.x_data

    model.save(str(tmp_path / "model.joblib"))

    assert model.x_data is x_data


@pytest.mark.parametrize("model_class", MODELS)
def test_the_restored_model_still_predicts_the_same(model_class, tmp_path):
    model = _fitted(model_class)
    x = _data()
    expected = list(np.asarray(model.get_cluster_labels(x)))

    model.save(str(tmp_path / "model.joblib"))
    restored = model_class.load(str(tmp_path / "model.joblib"))

    assert list(np.asarray(restored.get_cluster_labels(x))) == expected
