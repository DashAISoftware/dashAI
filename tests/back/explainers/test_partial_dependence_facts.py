from DashAI.back.core.artifacts import ArtifactGroup
from DashAI.back.explainability.explainers.partial_dependence import (
    PartialDependence,
    _partial_dependence_curve_facts,
)

BINARY_METADATA = {"metadata": {"target_names": ["no", "yes"]}}


def _explanation_for(feature: str, grid_values: list, values: list) -> dict:
    return {
        **BINARY_METADATA,
        feature: {"grid_values": grid_values, "average": [values]},
    }


def test_facts_return_none_for_a_non_group_artifact():
    explanation = _explanation_for("age", [20, 65], [0.2, 0.2])

    assert _partial_dependence_curve_facts(explanation, object()) is None


def test_facts_return_none_when_title_does_not_match_the_expected_pattern():
    explanation = _explanation_for("age", [20, 65], [0.2, 0.2])
    group = ArtifactGroup(title="Not a curve title", artifacts=[])

    assert _partial_dependence_curve_facts(explanation, group) is None


def test_facts_classify_a_flat_curve():
    explanation = _explanation_for("age", [20, 30, 40, 50, 65], [0.2] * 5)
    group = ArtifactGroup(title="Feature: age - Class: yes", artifacts=[])

    facts = _partial_dependence_curve_facts(explanation, group)

    assert facts == {
        "feature": "age",
        "target": "yes",
        "trend": "flat",
        "start_value": 20,
        "end_value": 65,
        "start_pred": 0.2,
        "end_pred": 0.2,
        "min_pred": 0.2,
        "max_pred": 0.2,
    }


def test_facts_classify_an_increasing_curve():
    explanation = _explanation_for(
        "age", [20, 30, 40, 50, 65], [0.1, 0.2, 0.3, 0.4, 0.5]
    )
    group = ArtifactGroup(title="Feature: age - Class: yes", artifacts=[])

    facts = _partial_dependence_curve_facts(explanation, group)

    assert facts["trend"] == "increases"
    assert facts["start_pred"] == 0.1
    assert facts["end_pred"] == 0.5


def test_facts_classify_a_decreasing_curve():
    explanation = _explanation_for(
        "age", [20, 30, 40, 50, 65], [0.5, 0.4, 0.3, 0.2, 0.1]
    )
    group = ArtifactGroup(title="Feature: age - Class: yes", artifacts=[])

    facts = _partial_dependence_curve_facts(explanation, group)

    assert facts["trend"] == "decreases"
    assert facts["start_pred"] == 0.5
    assert facts["end_pred"] == 0.1


def test_facts_classify_a_non_monotonic_curve():
    explanation = _explanation_for(
        "age", [20, 30, 40, 50, 65], [0.1, 0.5, 0.2, 0.6, 0.1]
    )
    group = ArtifactGroup(title="Feature: age - Class: yes", artifacts=[])

    facts = _partial_dependence_curve_facts(explanation, group)

    assert facts["trend"] == "non_monotonic"
    assert facts["min_pred"] == 0.1
    assert facts["max_pred"] == 0.6


def test_story_phrases_a_flat_curve_using_the_shared_facts():
    explanation = _explanation_for("age", [20, 30, 40, 50, 65], [0.2] * 5)
    group = ArtifactGroup(title="Feature: age - Class: yes", artifacts=[])
    explainer = PartialDependence(model=None)

    story = explainer.story(explanation, group)

    assert "age" in story.en
    assert "does not noticeably affect" in story.en


def test_insight_facts_returns_the_same_raw_data_as_the_shared_helper():
    explanation = _explanation_for(
        "age", [20, 30, 40, 50, 65], [0.1, 0.2, 0.3, 0.4, 0.5]
    )
    group = ArtifactGroup(title="Feature: age - Class: yes", artifacts=[])
    explainer = PartialDependence(model=None)

    assert explainer.insight_facts(explanation, group) == (
        _partial_dependence_curve_facts(explanation, group)
    )


def test_insight_facts_returns_none_when_the_artifact_does_not_match():
    explanation = _explanation_for("age", [20, 65], [0.2, 0.2])
    explainer = PartialDependence(model=None)

    assert explainer.insight_facts(explanation, object()) is None
