from DashAI.back.insights.analyzers.explainer_insights import (
    EXPLAINER_INSIGHT_ANALYZERS,
    PartialDependenceInsightAnalyzer,
)
from DashAI.back.insights.context import AnalysisContext

FACTS = {
    "feature": "age",
    "target": "yes",
    "trend": "increases",
    "start_value": 20,
    "end_value": 65,
    "start_pred": 0.1,
    "end_pred": 0.5,
    "min_pred": 0.1,
    "max_pred": 0.5,
}


def test_build_prompt_returns_a_system_and_a_user_message():
    context = AnalysisContext(consumer_type="explainer", data=FACTS)
    analyzer = PartialDependenceInsightAnalyzer()

    messages = analyzer.build_prompt(context)

    assert [m["role"] for m in messages] == ["system", "user"]


def test_build_prompt_mentions_the_facts_in_the_user_message():
    context = AnalysisContext(consumer_type="explainer", data=FACTS)
    analyzer = PartialDependenceInsightAnalyzer()

    user_message = analyzer.build_prompt(context)[1]["content"]

    assert "age" in user_message
    assert "yes" in user_message
    assert "increases" in user_message
    assert "20" in user_message
    assert "65" in user_message


def test_build_prompt_defaults_to_english_without_metadata():
    context = AnalysisContext(consumer_type="explainer", data=FACTS)
    analyzer = PartialDependenceInsightAnalyzer()

    system_message = analyzer.build_prompt(context)[0]["content"]

    assert "answer in en" in system_message


def test_build_prompt_uses_the_requested_language():
    context = AnalysisContext(
        consumer_type="explainer", data=FACTS, metadata={"language": "es"}
    )
    analyzer = PartialDependenceInsightAnalyzer()

    system_message = analyzer.build_prompt(context)[0]["content"]

    assert "answer in es" in system_message


def test_analyze_delegates_to_provider_with_the_built_prompt():
    class _DummyProvider:
        def complete(self, messages):
            return f"received {len(messages)} messages"

    context = AnalysisContext(consumer_type="explainer", data=FACTS)
    analyzer = PartialDependenceInsightAnalyzer()

    assert analyzer.analyze(context, _DummyProvider()) == "received 2 messages"


def test_explainer_insight_analyzers_maps_partial_dependence():
    assert (
        EXPLAINER_INSIGHT_ANALYZERS["PartialDependence"]
        is PartialDependenceInsightAnalyzer
    )
