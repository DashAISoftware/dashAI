from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.unsupervised_task import UnsupervisedTask
from DashAI.back.types.value_types import Float, Integer


class ClusteringTask(UnsupervisedTask):
    """Task for grouping samples into clusters without target labels.

    Clustering tasks discover groups directly from numeric input features.
    Unlike supervised tasks, they do not require output columns and are
    evaluated with internal clustering metrics computed from the feature matrix
    and the cluster labels produced by the model.
    """

    DESCRIPTION: str = MultilingualString(
        en="Group similar samples from numeric features without target labels.",
        es="Agrupa muestras similares desde variables numericas sin etiquetas.",
    )
    DISPLAY_NAME: str = MultilingualString(en="Clustering", es="Agrupamiento")

    SCORING_PROFILES = {
        "cluster_separation": {
            "description": "Cluster Separation",
            "weights": {"Silhouette": 0.6, "CalinskiHarabasz": 0.4},
        },
        "cluster_compactness": {
            "description": "Cluster Compactness",
            "weights": {
                "Silhouette": 0.4,
                "DaviesBouldin": 0.4,
                "CalinskiHarabasz": 0.2,
            },
        },
    }

    metadata: dict = {
        "inputs_types": [Float, Integer],
        "outputs_types": [],
        "inputs_cardinality": "n",
        "outputs_cardinality": 0,
    }

    SESSION_CONFIG_SCHEMA = {
        **UnsupervisedTask.SESSION_CONFIG_SCHEMA,
        "split_strategy": "full_dataset",
    }
