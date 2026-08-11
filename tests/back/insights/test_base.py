from DashAI.back.insights.base import BaseInsightAnalyzer, import_analyzer
from DashAI.back.insights.context import AnalysisContext


class _DummyAnalyzer(BaseInsightAnalyzer):
    def build_prompt(self, context):
        return [{"role": "user", "content": f"analyze {context.data}"}]


class _DummyProvider:
    def __init__(self):
        self.received_messages = None

    def complete(self, messages):
        self.received_messages = messages
        return "a generated insight"


def test_analyze_builds_prompt_and_calls_provider():
    analyzer = _DummyAnalyzer()
    provider = _DummyProvider()
    context = AnalysisContext(consumer_type="dummy", data={"x": 1})

    result = analyzer.analyze(context, provider)

    assert result == "a generated insight"
    assert provider.received_messages == [
        {"role": "user", "content": "analyze {'x': 1}"}
    ]


def test_import_analyzer_resolves_dotted_path():
    resolved = import_analyzer("tests.back.insights.test_base._DummyAnalyzer")

    assert resolved is _DummyAnalyzer
