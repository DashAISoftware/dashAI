"""SHAP must not be handed a bound method of the model.

``shap.utils._legacy.convert_to_model`` suppresses scikit-learn's "X does not
have valid feature names" warning by blanking ``feature_names_in_`` on the
object the callable is bound to, reached through ``__self__``. It assumes that
attribute is writable.

Two of the models DashAI ships inherit ``feature_names_in_`` from their upstream
estimator as a read-only ``property``, so that assignment raises and the
explanation dies before it starts:

    AttributeError: property 'feature_names_in_' of 'LGBMClassifier' object has
    no setter

(on Python 3.10 the same failure reads ``can't set attribute
'feature_names_in_'``).

``as_shap_predictor`` hands over a plain closure instead, which has no
``__self__``, so SHAP skips the step. These tests pin both halves: that the
wrappers really are read-only (otherwise the fix guards nothing), and that the
handover survives ``convert_to_model``.
"""

import numpy as np
import pandas as pd
import pytest

from DashAI.back.explainability.model_input import as_shap_predictor
from DashAI.back.models.scikit_learn.lightgbm_classifier import LGBMClassifier
from DashAI.back.models.scikit_learn.xgboost_classifier import XGBClassifier

#: The models whose ``feature_names_in_`` cannot be assigned to. Every other
#: model stores it as a plain instance attribute, which is settable.
READ_ONLY_FEATURE_NAMES = [LGBMClassifier, XGBClassifier]


@pytest.fixture(name="frame")
def fixture_frame():
    rng = np.random.default_rng(0)
    return pd.DataFrame({"a": rng.random(40), "b": rng.random(40)}), rng.integers(
        0, 2, 40
    )


@pytest.mark.parametrize(
    "model_class", READ_ONLY_FEATURE_NAMES, ids=lambda c: c.__name__
)
def test_these_models_really_do_expose_feature_names_read_only(model_class, frame):
    """Guards the premise: without this the tests below prove nothing.

    If an upstream release ever makes the attribute writable, this fails and the
    workaround can be reconsidered.
    """
    x, y = frame
    model = model_class()
    model.fit(x, y)

    assert hasattr(model, "feature_names_in_")
    # CPython worded this differently before 3.11 ("can't set attribute").
    with pytest.raises(AttributeError, match="no setter|can't set attribute"):
        model.feature_names_in_ = None


@pytest.mark.parametrize(
    "model_class", READ_ONLY_FEATURE_NAMES, ids=lambda c: c.__name__
)
def test_a_bound_predict_breaks_shaps_model_conversion(model_class, frame):
    """The failure this exists to prevent, reproduced directly.

    Pinned so the regression is recognisable if anyone reverts the handover to
    ``model=self.model.predict``.
    """
    from shap.utils._legacy import convert_to_model

    x, y = frame
    model = model_class()
    model.fit(x, y)

    with pytest.raises(AttributeError, match="feature_names_in_"):
        convert_to_model(model.predict)


@pytest.mark.parametrize(
    "model_class", READ_ONLY_FEATURE_NAMES, ids=lambda c: c.__name__
)
def test_the_wrapped_predictor_survives_shaps_model_conversion(model_class, frame):
    from shap.utils._legacy import convert_to_model

    x, y = frame
    model = model_class()
    model.fit(x, y)

    converted = convert_to_model(as_shap_predictor(model))

    assert converted.f is not None
    # The model itself must be left alone: SHAP deep-copies before blanking the
    # attribute, but only on the branch we now skip.
    assert list(model.feature_names_in_) == ["a", "b"]


def test_the_wrapped_predictor_forwards_to_predict_positionally():
    """SHAP calls the model with one positional argument; that must not change."""
    seen = {}

    class Model:
        def predict(self, x):
            seen["arg"] = x
            return [0]

    predictor = as_shap_predictor(Model())
    assert predictor("the frame") == [0]
    assert seen["arg"] == "the frame"


def test_the_wrapped_predictor_hides_the_model_from_shap():
    """The whole mechanism: no ``__self__`` means SHAP never reaches the model."""

    class Model:
        def predict(self, x):
            return [0]

    model = Model()
    assert getattr(model.predict, "__self__", None) is model
    assert getattr(as_shap_predictor(model), "__self__", None) is None
