"""Helpers that read a model session's stored fields, without a database."""

from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("preprocessing", "has_steps"),
    [
        (None, False),
        ({}, False),
        ({"steps": []}, False),
        ({"steps": [{"converter": "StandardScaler"}]}, True),
    ],
)
def test_a_session_preprocesses_when_it_declares_steps(preprocessing, has_steps):
    """The one reader of "does this session preprocess": training, prediction
    and the model package ask it, so they cannot disagree."""
    from DashAI.back.tasks.session_roles import session_has_steps

    session = SimpleNamespace(preprocessing=preprocessing)

    assert session_has_steps(session) is has_steps
