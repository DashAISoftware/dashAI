"""Tests for the per family model artifact mixins."""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.core.artifacts import normalize_artifacts
from DashAI.back.models.model_artifact_context import ModelArtifactContext
from DashAI.back.models.scikit_learn.decision_tree_classifier import (
    DecisionTreeClassifier,
)
from DashAI.back.models.scikit_learn.k_neighbors_classifier import KNeighborsClassifier
from DashAI.back.models.scikit_learn.k_neighbors_regression import KNeighborsRegression
from DashAI.back.models.scikit_learn.mlp_classifier import MLPClassifier
from DashAI.back.models.scikit_learn.model_artifact_mixins import MAX_PLOTTED_TREES
from DashAI.back.models.scikit_learn.random_forest_classifier import (
    RandomForestClassifier,
)


@pytest.fixture
def context():
    rng = np.random.default_rng(0)
    x = pd.DataFrame({"a": rng.normal(0, 3, 80), "b": rng.normal(0, 1, 80)})
    y = (x["a"] > 0).astype(int).to_numpy()
    return ModelArtifactContext(
        x_train=x, y_train=y, feature_names=["a", "b"], class_names=["no", "yes"]
    )


def _fitted(model_class, context, target=None, **params):
    model = model_class(**params)
    model.fit(context.x_train, context.y_train if target is None else target)
    return model


def _types(artifacts):
    return [getattr(item, "type", None) for item in artifacts]


def test_unfitted_model_returns_no_artifacts(context):
    assert DecisionTreeClassifier(max_depth=3).get_model_artifacts(context) == []


def test_decision_tree_returns_tree_and_importances(context):
    artifacts = _fitted(
        DecisionTreeClassifier, context, max_depth=3
    ).get_model_artifacts(context)
    assert _types(artifacts) == ["plotly", "plotly"]
    assert normalize_artifacts(artifacts)[0]["index"] == 0


def test_forest_groups_its_trees_and_states_the_truncation(context):
    artifacts = _fitted(
        RandomForestClassifier, context, n_estimators=30, max_depth=2
    ).get_model_artifacts(context)
    grouped = [item for item in artifacts if getattr(item, "type", None) == "grouped"]
    assert len(grouped) == 1
    assert len(grouped[0].groups) == MAX_PLOTTED_TREES
    assert "text" in _types(artifacts)


def test_small_forest_is_not_truncated(context):
    artifacts = _fitted(
        RandomForestClassifier, context, n_estimators=3, max_depth=2
    ).get_model_artifacts(context)
    grouped = [item for item in artifacts if getattr(item, "type", None) == "grouped"]
    assert len(grouped[0].groups) == 3
    assert "text" not in _types(artifacts)


def test_mlp_groups_its_layers(context):
    artifacts = _fitted(
        MLPClassifier, context, hidden_layer_size=4, max_iter=20
    ).get_model_artifacts(context)
    grouped = [item for item in artifacts if getattr(item, "type", None) == "grouped"]
    assert len(grouped[0].groups) == 2


def test_k_neighbors_classifier_returns_a_decision_surface(context):
    artifacts = _fitted(
        KNeighborsClassifier, context, n_neighbors=3
    ).get_model_artifacts(context)
    assert _types(artifacts) == ["plotly"]


def test_k_neighbors_regression_returns_a_curve(context):
    regression_context = ModelArtifactContext(
        x_train=context.x_train,
        y_train=context.y_train.astype(float),
        feature_names=context.feature_names,
        class_names=None,
    )
    artifacts = _fitted(
        KNeighborsRegression,
        regression_context,
        target=regression_context.y_train,
        n_neighbors=3,
    ).get_model_artifacts(regression_context)
    assert _types(artifacts) == ["plotly"]


def test_every_mixin_output_normalizes(context):
    models = (
        _fitted(DecisionTreeClassifier, context, max_depth=3),
        _fitted(RandomForestClassifier, context, n_estimators=5, max_depth=2),
        _fitted(MLPClassifier, context, hidden_layer_size=4, max_iter=20),
        _fitted(KNeighborsClassifier, context, n_neighbors=3),
    )
    for model in models:
        items = normalize_artifacts(model.get_model_artifacts(context))
        assert items
        for item in items:
            assert item["type"] in {"plotly", "table", "text", "image", "grouped"}


def test_xgboost_dumps_its_trees(context):
    from DashAI.back.models.scikit_learn.xgboost_classifier import XGBClassifier

    model = _fitted(XGBClassifier, context, n_estimators=3, max_depth=2)
    artifacts = model.get_model_artifacts(context)
    grouped = [item for item in artifacts if getattr(item, "type", None) == "grouped"]
    assert grouped
    assert grouped[0].groups[0].artifacts[0].type == "text"


def test_boosted_trees_keep_get_params_working(context):
    """The artifact mixin must not become a third base of the concrete class.

    ``xgboost`` and ``lightgbm`` read ``type(self).__bases__`` directly and
    assume exactly two entries, so the mixin is folded into the intermediate
    DashAI class instead.
    """
    from DashAI.back.models.scikit_learn.lightgbm_classifier import LGBMClassifier
    from DashAI.back.models.scikit_learn.xgboost_classifier import XGBClassifier

    for model_class in (XGBClassifier, LGBMClassifier):
        assert len(model_class.__bases__) == 2
        assert model_class(n_estimators=2).get_params()


def test_wired_models_report_support():
    from DashAI.back.models.scikit_learn.lightgbm_classifier import LGBMClassifier
    from DashAI.back.models.scikit_learn.xgboost_classifier import XGBClassifier

    for model_class in (
        DecisionTreeClassifier,
        RandomForestClassifier,
        MLPClassifier,
        KNeighborsClassifier,
        KNeighborsRegression,
        XGBClassifier,
        LGBMClassifier,
    ):
        assert model_class.supports_model_artifacts() is True
