"""How the categorical encoders treat a category they did not see in fit.

A session fits its converters on the training rows only, so a category that
appears only in validation, in test or in the rows to predict reaches an
encoder that never saw it. A session treats it by default, never refitting:
one-hot gives a row of zeros, ordinal and label give -1. Those defaults are
the session's own (``SESSION_PARAMS``): the encoders themselves stay strict,
as the notebook uses them. A user who chose "error" keeps it, and gets a
message that names the converter, the column and the values.
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


def _from_the_notebook(cls, **params):
    """Built as the notebook builds it: every schema field, defaults included."""
    return cls(**{**schema_placeholder_defaults(cls), **params})


def _from_the_wizard(cls, **params):
    """Built as the session wizard builds it: the schema fields, with the
    session's own defaults seeded over them."""
    return cls(**{**schema_placeholder_defaults(cls), **cls.SESSION_PARAMS, **params})


def _bare(cls, **params):
    return cls(**params)


@pytest.mark.parametrize("build", [_bare, _from_the_notebook])
@pytest.mark.parametrize("cls", [OneHotEncoder, OrdinalEncoder])
def test_an_encoder_refuses_an_unseen_category_by_default(cls, build):
    converter = build(cls)
    converter.fit(_scope(["a", "b", "a"]))

    assert converter.raises_on_unseen()
    with pytest.raises(ValueError, match="unknown categories"):
        converter.transform(_scope(["a", "z"]))


def test_one_hot_in_a_session_gives_zeros_to_an_unseen_category():
    converter = _from_the_wizard(OneHotEncoder)
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["a", "z"]) == [[1, 0], [0, 0]]


def test_ordinal_in_a_session_gives_minus_one_to_an_unseen_category():
    converter = _from_the_wizard(OrdinalEncoder)
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["a", "b", "z"]) == [[0], [1], [-1]]


def test_label_gives_minus_one_to_an_unseen_category():
    converter = LabelEncoder()
    converter.fit(_scope(["a", "b", "a"]))

    assert _encoded(converter, ["a", "b", "z"]) == [[0], [1], [-1]]


def test_ordinal_set_to_error_from_the_form_still_fits():
    """The session form sends its unknown value along with "error"."""
    converter = _from_the_wizard(OrdinalEncoder, handle_unknown="error")
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


def _fitted(converter_name, params):
    preprocessor = _session(converter_name, params)
    preprocessor.fit_transform({"train": _dataset(["a", "b", "a"])})
    return preprocessor


HINTS = {
    "OneHotEncoder": 'set "handle_unknown" to "ignore"',
    "OrdinalEncoder": 'set "handle_unknown" to "use_encoded_value"',
}


@pytest.mark.parametrize("converter_name", sorted(HINTS))
def test_error_at_training_names_what_only_appears_outside_the_train(
    converter_name,
):
    preprocessor = _session(converter_name, {"handle_unknown": "error"})

    with pytest.raises(ValueError, match="cannot encode values") as error:
        preprocessor.fit_transform(
            {"train": _dataset(["a", "b", "a"]), "test": _dataset(["a", "z", "w"])}
        )

    message = str(error.value)
    assert f"{converter_name} (step 1)" in message
    assert "column 'c'" in message
    assert "'w', 'z'" in message
    assert "only appear outside the training rows" in message
    assert HINTS[converter_name] in message


@pytest.mark.parametrize("converter_name", sorted(HINTS))
def test_error_at_prediction_names_what_was_not_in_the_training_data(
    converter_name,
):
    preprocessor = _fitted(converter_name, {"handle_unknown": "error"})

    with pytest.raises(ValueError, match="cannot encode values") as error:
        preprocessor.transform_dataset(_dataset(["a", "z"]))

    message = str(error.value)
    assert f"{converter_name} (step 1)" in message
    assert "column 'c'" in message
    assert "'z'" in message
    assert "were not in the training data" in message
    assert HINTS[converter_name] in message


@pytest.mark.parametrize("converter_name", sorted(ENCODERS))
def test_predicting_never_refits_the_encoder(converter_name):
    import pickle

    preprocessor = _fitted(converter_name, {})
    before = pickle.dumps(preprocessor.fitted_converters)

    preprocessor.transform_dataset(_dataset(["z", "a", "q"]))

    assert pickle.dumps(preprocessor.fitted_converters) == before


@pytest.mark.parametrize("converter_name", sorted(ENCODERS))
def test_predicting_records_what_each_encoder_did_not_see(converter_name):
    preprocessor = _fitted(converter_name, {})
    unseen = []

    preprocessor.transform_dataset(_dataset(["z", "a", "q", "z"]), unseen=unseen)

    assert unseen == [
        {
            "source": f"{converter_name} (step 1)",
            "column": "c",
            "values": ["q", "z"],
            "count": 2,
        }
    ]


def test_the_record_keeps_a_bounded_sample_of_the_values():
    preprocessor = _fitted("OneHotEncoder", {})
    new = [f"n{i:03d}" for i in range(150)]
    unseen = []

    preprocessor.transform_dataset(_dataset(new), unseen=unseen)

    assert unseen[0]["count"] == 150
    assert unseen[0]["values"] == new[:20]


@pytest.mark.parametrize("converter_name", sorted(ENCODERS))
def test_an_encoder_never_reaches_the_target(converter_name):
    """The API refuses a step scoped on the target (``target_in_scope``), but
    an imported session package is refitted without that check, so the
    preprocessor refuses it too: treating an unknown label of the target
    would invent a class."""
    sequence = ConverterSequence(
        steps=[
            ConverterStep(
                converter=converter_name,
                params={},
                scope=[RawColumnRef(name="c"), RawColumnRef(name="y")],
            )
        ]
    )
    registry = {name: {"class": cls} for name, cls in ENCODERS.items()}
    preprocessor = SessionPreprocessor(sequence, registry, target_columns=["y"])

    with pytest.raises(ValueError, match=r"step 1\) has the target column 'y'"):
        preprocessor.fit_transform({"train": _dataset(["a", "b"], ["p", "q"])})
