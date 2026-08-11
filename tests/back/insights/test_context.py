import pytest

from DashAI.back.insights.context import AnalysisContext


def test_analysis_context_stores_consumer_type_and_data():
    context = AnalysisContext(
        consumer_type="explainer",
        data={"feature": "age", "target": "income"},
    )

    assert context.consumer_type == "explainer"
    assert context.data == {"feature": "age", "target": "income"}
    assert context.metadata is None


def test_analysis_context_accepts_optional_metadata():
    context = AnalysisContext(
        consumer_type="explainer",
        data={"feature": "age"},
        metadata={"run_id": 1},
    )

    assert context.metadata == {"run_id": 1}


def test_analysis_context_is_immutable():
    context = AnalysisContext(consumer_type="explainer", data={})

    with pytest.raises(AttributeError):
        context.consumer_type = "other"
