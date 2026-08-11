from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.core.enums.status import InsightStatus
from DashAI.back.dependencies.database.models import Base, InsightResult


def _session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _new_result() -> InsightResult:
    return InsightResult(
        consumer_type="global_explainer",
        consumer_id=1,
        context_data={"feature": "age"},
        analyzer_path="pkg.module.Class",
        provider_kind="local",
    )


def test_insight_result_defaults_to_not_started():
    session_factory = _session_factory()
    with session_factory() as db:
        result = _new_result()
        db.add(result)
        db.commit()
        db.refresh(result)

        assert result.status == InsightStatus.NOT_STARTED
        assert result.consumer_ref is None
        assert result.result_text is None
        assert result.error_message is None


def test_insight_result_status_transitions_set_timestamps():
    session_factory = _session_factory()
    with session_factory() as db:
        result = _new_result()
        db.add(result)
        db.commit()

        result.set_status_as_delivered()
        assert result.status == InsightStatus.DELIVERED
        assert result.delivery_time is not None

        result.set_status_as_started()
        assert result.status == InsightStatus.STARTED
        assert result.start_time is not None

        result.set_status_as_finished()
        assert result.status == InsightStatus.FINISHED
        assert result.end_time is not None

        db.commit()


def test_insight_result_status_error_keeps_the_error_message():
    session_factory = _session_factory()
    with session_factory() as db:
        result = _new_result()
        db.add(result)
        db.commit()

        result.error_message = "the provider is not downloaded"
        result.set_status_as_error()
        db.commit()
        db.refresh(result)

        assert result.status == InsightStatus.ERROR
        assert result.error_message == "the provider is not downloaded"
