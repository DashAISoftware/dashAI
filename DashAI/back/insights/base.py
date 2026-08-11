import importlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Type

from DashAI.back.insights.context import AnalysisContext

if TYPE_CHECKING:
    from DashAI.back.insights.providers import InsightProvider


class BaseInsightAnalyzer(ABC):
    """Consumer-specific strategy for turning an AnalysisContext into text.

    Knows how to phrase the prompt for its consumer (e.g. a partial
    dependence curve); has no opinion on which model answers it.
    """

    @abstractmethod
    def build_prompt(self, context: AnalysisContext) -> List[Dict[str, str]]:
        raise NotImplementedError

    def analyze(self, context: AnalysisContext, provider: "InsightProvider") -> str:
        return provider.complete(self.build_prompt(context))


def import_analyzer(dotted_path: str) -> Type[BaseInsightAnalyzer]:
    """Resolve a ``"module.path.ClassName"`` string into its class.

    Lets ``InsightGenerationJob`` load the right analyzer for a stored
    ``InsightResult`` without importing any consumer-specific module itself.
    """
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)
