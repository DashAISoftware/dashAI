"""Component references in a session's configuration are read strictly.

An empty reference (``{}`` or ``{"component": "", "params": {}}``) names nothing
and describes as a custom configuration. A reference that names no component,
or whose component is not a string, is malformed and raises ValueError rather
than being read as an empty component.
"""

import pytest

from DashAI.back.services.RAG.session_configuration_service import (
    SessionConfigurationService,
)


def _service() -> SessionConfigurationService:
    """Return a service with no database and no registered components."""
    return SessionConfigurationService(db=None, registry={})


def test_an_empty_retriever_reference_describes_as_custom():
    section = _service()._describe_retriever({})

    assert section["preset_key"] is None
    assert section["component"] == ""


def test_an_empty_component_with_empty_params_describes_as_custom():
    section = _service()._describe_retriever({"component": "", "params": {}})

    assert section["preset_key"] is None


def test_an_empty_chunking_reference_describes_without_a_summary():
    section = _service()._describe_chunking({"component": "", "params": {}})

    assert section["preset_key"] is None
    assert "summary" not in section


@pytest.mark.parametrize(
    "reference",
    [{"params": {"top_k": 3}}, {"component": None, "params": {}}, {"component": 7}],
    ids=["missing-component", "null-component", "numeric-component"],
)
def test_a_malformed_retriever_reference_raises(reference):
    with pytest.raises(ValueError, match="component"):
        _service()._describe_retriever(reference)


def test_a_malformed_chunking_reference_raises():
    with pytest.raises(ValueError, match="component"):
        _service()._describe_chunking({"params": {"chunk_size": 10}})


def test_a_malformed_generation_reference_raises():
    with pytest.raises(ValueError, match="component"):
        _service()._describe_generation({"params": {}})


def test_a_malformed_transformation_reference_raises():
    with pytest.raises(ValueError, match="component"):
        _service()._describe_transformation({"params": {}})


def test_an_absent_transformation_reference_is_disabled():
    section = _service()._describe_transformation({})

    assert section["enabled"] is False


def test_a_retriever_contract_error_is_not_swallowed():
    """A malformed ``children`` list reaches the caller from preset matching."""
    reference = {"component": "ParallelRetriever", "params": {"children": "nope"}}

    with pytest.raises(ValueError, match="children"):
        _service()._describe_retriever(reference)
