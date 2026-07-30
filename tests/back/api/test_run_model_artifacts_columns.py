"""The run row can carry a generated model artifacts file."""

from DashAI.back.dependencies.database.models import Run, RunStatus


def test_run_has_model_artifact_columns():
    columns = Run.__table__.columns
    assert "model_artifacts_path" in columns
    assert "model_artifacts_status" in columns
    assert columns["model_artifacts_path"].nullable
    assert columns["model_artifacts_status"].nullable


def test_model_artifacts_status_uses_run_status_enum():
    enum_type = Run.__table__.columns["model_artifacts_status"].type
    assert enum_type.enum_class is RunStatus
