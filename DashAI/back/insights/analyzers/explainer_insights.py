from typing import Dict, List, Type

from DashAI.back.insights.base import BaseInsightAnalyzer
from DashAI.back.insights.context import AnalysisContext


class PartialDependenceInsightAnalyzer(BaseInsightAnalyzer):
    """Turns a partial dependence curve's raw facts into a prompt.

    Consumes the dict produced by
    ``DashAI.back.explainability.explainers.partial_dependence.PartialDependence.insight_facts``
    (feature, target, trend, values) and asks a generative model for a
    brief analysis in the requested language.
    """

    def build_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        facts = context.data
        language = (context.metadata or {}).get("language", "en")
        return [
            {
                "role": "system",
                "content": (
                    "You are an assistant that explains machine learning "
                    "explainability results to data scientists. Be concise "
                    f"and answer in {language}."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"A partial dependence curve for feature '{facts['feature']}' "
                    f"on class '{facts['target']}' goes from "
                    f"{facts['start_value']} to {facts['end_value']}, with "
                    f"predicted probability going from {facts['start_pred']} to "
                    f"{facts['end_pred']} (trend classified as "
                    f"'{facts['trend']}', ranging between {facts['min_pred']} "
                    f"and {facts['max_pred']}). Give a brief analysis of what "
                    "this could mean."
                ),
            },
        ]


EXPLAINER_INSIGHT_ANALYZERS: Dict[str, Type[BaseInsightAnalyzer]] = {
    "PartialDependence": PartialDependenceInsightAnalyzer,
}
