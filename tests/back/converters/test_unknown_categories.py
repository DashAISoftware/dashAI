"""How the categorical encoders treat a category they did not see in fit.

A session fits its converters on the training rows only, so a category that
appears only in validation, in test or in the rows to predict reaches an
encoder that never saw it. By default it is treated, never refitted: one-hot
gives a row of zeros, ordinal and label give -1. A user who chose "error"
keeps it, and gets a message that names the converter, the column and the
values.
"""

import pandas as pd
import pytest

from DashAI.back.converters.scikit_learn.label_encoder import LabelEncoder
from DashAI.back.converters.scikit_learn.one_hot_encoder import OneHotEncoder
from DashAI.back.converters.scikit_learn.ordinal_encoder import OrdinalEncoder
from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from DashAI.back.dataloaders.classes.dashai_dataset import (
    to_dashai_dataset,
    transform_dataset_with_schema,
)
from DashAI.back.preprocessing.column_ref import (
    ConverterSequence,
    ConverterStep,
    RawColumnRef,
)
from DashAI.back.preprocessing.session_preprocessor import SessionPreprocessor

SCHEMA = {
    "c": {"type": "Categorical", "dtype": "string"},
    "y": {"type": "Categorical", "dtype": "string"},
}

ENCODERS = {
    "OneHotEncoder": OneHotEncoder,
    "OrdinalEncoder": OrdinalEncoder,
    "LabelEncoder": LabelEncoder,
}


def _dataset(values, target=None):
    target = target if target is not None else ["p"] * len(values)
    return transform_dataset_with_schema(
        to_dashai_dataset(pd.DataFrame({"c": values, "y": target})), SCHEMA
    )


def _scope(values):
    return _dataset(values).select_columns(["c"])


def _encoded(converter, values):
    """The encoded columns the converter appends for the rows, as lists."""
    transformed = converter.transform(_scope(values)).to_pandas()
    added = [name for name in transformed.columns if name != "c"]
    return transformed[added].to_numpy().tolist()


def _from_the_form(cls, **params):
    """Built as the wizard builds it: every schema field, defaults included."""
    return cls(**{**schema_placeholder_defaults(cls), **params})


@pytest.mark.parametrize("build", [OneHotEncoder, _from_the_form])
def test_one_hot_gives_zeros_to_an_unseen_category_by_default(build):
    converter = build(OneHotEncoder) if build is _from_the_form else build()
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["a", "z"]) == [[1, 0], [0, 0]]


@pytest.mark.parametrize("build", [OrdinalEncoder, _from_the_form])
def test_ordinal_gives_minus_one_to_an_unseen_category_by_default(build):
    converter = build(OrdinalEncoder) if build is _from_the_form else build()
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["a", "b", "z"]) == [[0], [1], [-1]]


def test_label_gives_minus_one_to_an_unseen_category():
    converter = LabelEncoder()
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["a", "b", "z"]) == [[0], [1], [-1]]


def test_ordinal_set_to_error_from_the_form_still_fits():
    """The form sends the default unknown value along with "error"."""
    converter = _from_the_form(OrdinalEncoder, handle_unknown="error")
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["b", "a"]) == [[1], [0]]


def _session(converter_name, params=None):
    sequence = ConverterSequence(
        steps=[
            ConverterStep(
                converter=converter_name,
                params=params or {},
                scope=[RawColumnRef(name="c")],
            )
        ]
    )
    registry = {name: {"class": cls} for name, cls in ENCODERS.items()}
    return SessionPreprocessor(sequence, registry, target_columns=["y"])


@pytest.mark.parametrize("converter_name", sorted(ENCODERS))
def test_a_category_only_in_test_does_not_stop_the_fit(converter_name):
    preprocessor = _session(converter_name)

    transformed, _ = preprocessor.fit_transform(
        {"train": _dataset(["a", "b", "a"]), "test": _dataset(["a", "z"])}
    )

    assert transformed["test"].num_rows == 2
