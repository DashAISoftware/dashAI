"""How a model's own categorical encoders treat a category they did not see.

Tabular models encode their categorical features themselves
(``CategoricalEncoderMixin``): label encoding for the columns that ask for it,
one-hot for the rest. At prediction time a feature value outside the stored
encoding is treated like the session encoders treat it, -1 for label and zeros
for one-hot, and reported. The target is never treated: an unknown label of
the output still fails, because decoding it would invent a class.
"""

import pyarrow as pa
import pytest

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.models.categorical_encoder_mixin import CategoricalEncoderMixin
from DashAI.back.types.categorical import Categorical


class _Model(CategoricalEncoderMixin):
    def __init__(self):
        self._setup_categorical_encoders()


def _dataset(values, encoder="one_hot"):
    categories = sorted(set(values))
    return DashAIDataset(
        pa.table({"c": values}),
        types={"c": Categorical(categories, encoder=encoder)},
    )


def _fitted(encoder):
    model = _Model()
    model.prepare_dataset(_dataset(["a", "b", "a"], encoder), is_fit=True)
    return model


def test_a_label_encoded_feature_gives_minus_one_to_an_unseen_value():
    model = _fitted("label")

    prepared = model.prepare_dataset(_dataset(["a", "z", "b"], "label"))

    assert prepared["c"] == [0, -1, 1]


@pytest.mark.parametrize("encoder", ["label", "one_hot"])
def test_the_model_reports_the_feature_values_it_did_not_see(encoder):
    model = _fitted(encoder)

    unseen = model.unseen_categories(_dataset(["a", "z", "q", "z"], encoder))

    assert unseen == [
        {"source": "_Model (model)", "column": "c", "values": ["q", "z"], "count": 2}
    ]


@pytest.mark.parametrize("encoder", ["label", "one_hot"])
def test_nothing_is_reported_when_every_value_was_seen(encoder):
    model = _fitted(encoder)

    assert model.unseen_categories(_dataset(["b", "a"], encoder)) == []


def test_an_unseen_label_of_the_target_still_fails():
    model = _Model()
    model.prepare_output(_dataset(["yes", "no"], "label"), is_fit=True)

    with pytest.raises(ValueError, match="'maybe' not found in encoding"):
        model.prepare_output(_dataset(["yes", "maybe"], "label"))


def test_the_label_encoding_is_strict_unless_the_caller_treats_unknowns():
    """The text transformers hand features and target to one call, which
    therefore has to stay strict."""
    from DashAI.back.dataloaders.classes.dashai_dataset_utils import (
        apply_categorical_label_encoder,
    )

    encodings = {"c": {"a": 0, "b": 1}}

    with pytest.raises(ValueError, match="'z' not found in encoding"):
        apply_categorical_label_encoder(_dataset(["a", "z"], "label"), encodings)
