"""The Clustering converter labels the rows it transforms, not the ones it fit.

A session fits its preprocessing on some rows and applies it to others: the
validation and test splits of an x/y session, the steps of a forecasting cut
after its origin, the rows to predict. The labels of the rows the algorithm
was fitted on say nothing about those.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.converters.clustering.clustering import Clustering
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)

# The converter finds its algorithms among the imported ClusteringModel classes.
from DashAI.back.models.scikit_learn.dbscan_clustering import (  # noqa: F401
    DBSCANClustering,
)
from DashAI.back.models.scikit_learn.kmeans_clustering import (  # noqa: F401
    KMeansClustering,
)

CENTRES = [(0.0, 0.0), (10.0, 10.0)]


def _numbers(frame):
    schema = {name: {"type": "Float", "dtype": "float64"} for name in frame.columns}
    return transform_dataset_with_schema(to_dashai_dataset(frame), schema)


def _blobs(per_centre, seed=0):
    rng = np.random.default_rng(seed)
    points = np.vstack(
        [rng.normal(loc=c, scale=0.1, size=(per_centre, 2)) for c in CENTRES]
    )
    return _numbers(pd.DataFrame({"x": points[:, 0], "y": points[:, 1]}))


def _converter(algorithm, **params):
    return Clustering(
        algorithm=algorithm,
        algorithm_params=params,
        output_column_name="cluster",
    )


def test_an_algorithm_that_labels_new_rows_labels_the_rows_it_transforms():
    converter = _converter("KMeansClustering", n_clusters=2, random_state=0)
    converter.fit(_blobs(20))

    # Fewer rows than the fit, one near each centre: each gets its own.
    new_rows = _numbers(pd.DataFrame({"x": [0.1, 9.9], "y": [0.0, 10.1]}))
    labels = converter.transform(new_rows).to_pandas()["cluster"].tolist()

    assert len(labels) == 2
    assert labels[0] != labels[1]


def test_the_rows_it_was_fitted_on_keep_the_labels_of_the_fit():
    data = _blobs(20)
    converter = _converter("KMeansClustering", n_clusters=2, random_state=0)
    converter.fit(data)

    labels = converter.transform(data).to_pandas()["cluster"].to_numpy()

    np.testing.assert_array_equal(labels, converter._labels)


def test_an_algorithm_that_only_labels_its_fit_says_so_on_other_rows():
    converter = _converter("DBSCANClustering")
    converter.fit(_blobs(20))

    with pytest.raises(ValueError, match="cannot assign labels to unseen samples"):
        converter.transform(_blobs(5, seed=1))
