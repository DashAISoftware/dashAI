import pytest
from kink import di
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.core.enums.status import InsightStatus
from DashAI.back.dependencies.database.models import Base, InsightResult
from DashAI.back.job.base_job import JobError
from DashAI.back.job.insight_generation_job import InsightGenerationJob

ANALYZER_PATH = (
    "DashAI.back.insights.analyzers.explainer_insights.PartialDependenceInsightAnalyzer"
)

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


class _DummyGenerativeModel:
    REQUIRES_DOWNLOAD = False

    def __init__(self, **kwargs):
        pass

    def generate(self, messages):
        return ["a generated insight"]


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    di["session_factory"] = factory
    yield factory
    del di["session_factory"]


@pytest.fixture
def fake_registry():
    registry = {"DummyGenerativeModel": {"class": _DummyGenerativeModel}}
    di["component_registry"] = registry
    yield registry
    del di["component_registry"]


def _create_result(session_factory, **overrides) -> int:
    defaults = {
        "consumer_type": "global_explainer",
        "consumer_id": 1,
        "context_data": FACTS,
        "context_metadata": {"language": "en"},
        "analyzer_path": ANALYZER_PATH,
        "provider_kind": "local",
        "provider_params": {"model_name": "DummyGenerativeModel"},
    }
    defaults.update(overrides)
    with session_factory() as db:
        result = InsightResult(**defaults)
        db.add(result)
        db.commit()
        return result.id


def test_run_generates_and_persists_the_insight_text(session_factory, fake_registry):
    insight_result_id = _create_result(session_factory)

    job = InsightGenerationJob(insight_result_id=insight_result_id)
    job.run()

    with session_factory() as db:
        result = db.get(InsightResult, insight_result_id)
        assert result.status == InsightStatus.FINISHED
        assert result.result_text == "a generated insight"
        assert [m["role"] for m in result.prompt] == ["system", "user"]
        assert result.error_message is None


def test_run_raises_and_marks_error_for_an_unknown_analyzer(
    session_factory, fake_registry
):
    insight_result_id = _create_result(
        session_factory,
        analyzer_path="DashAI.back.insights.analyzers.explainer_insights.NoSuchClass",
    )

    job = InsightGenerationJob(insight_result_id=insight_result_id)
    with pytest.raises(JobError):
        job.run()

    with session_factory() as db:
        result = db.get(InsightResult, insight_result_id)
        assert result.status == InsightStatus.ERROR
        assert result.error_message is not None


def test_run_raises_and_marks_error_for_a_not_yet_implemented_remote_provider(
    session_factory, fake_registry
):
    insight_result_id = _create_result(
        session_factory, provider_kind="remote", provider_params={}
    )

    job = InsightGenerationJob(insight_result_id=insight_result_id)
    with pytest.raises(JobError):
        job.run()

    with session_factory() as db:
        result = db.get(InsightResult, insight_result_id)
        assert result.status == InsightStatus.ERROR
        assert "not implemented" in result.error_message


def test_run_raises_when_the_insight_result_does_not_exist(
    session_factory, fake_registry
):
    job = InsightGenerationJob(insight_result_id=31415)

    with pytest.raises(JobError):
        job.run()


def test_set_status_as_delivered_updates_the_row(session_factory):
    insight_result_id = _create_result(session_factory)

    job = InsightGenerationJob(insight_result_id=insight_result_id)
    job.set_status_as_delivered()

    with session_factory() as db:
        result = db.get(InsightResult, insight_result_id)
        assert result.status == InsightStatus.DELIVERED
        assert result.delivery_time is not None


def test_get_job_name_mentions_the_consumer(session_factory):
    insight_result_id = _create_result(session_factory)

    job = InsightGenerationJob(insight_result_id=insight_result_id)

    assert "global_explainer" in job.get_job_name()
    assert "1" in job.get_job_name()
