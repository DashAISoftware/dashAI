"""Tests for the optional model artifact hook on BaseModel."""

from DashAI.back.core.artifacts import TextArtifact
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.model_artifact_context import ModelArtifactContext


class _PlainModel(BaseModel):
    """A model that does not visualise itself."""

    def save(self, filename):
        """Do nothing."""

    def load(self, filename):
        """Do nothing."""

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        """Do nothing."""


class _VisualModel(_PlainModel):
    """A model that overrides the artifact hook."""

    def get_model_artifacts(self, context):
        """Return one text artifact naming the features."""
        return [TextArtifact(payload=",".join(context.feature_names))]


def _context():
    return ModelArtifactContext(feature_names=["a", "b"], class_names=["no", "yes"])


def test_plain_model_does_not_support_artifacts():
    assert _PlainModel.supports_model_artifacts() is False
    assert _PlainModel().get_model_artifacts(_context()) == []


def test_overriding_model_supports_artifacts():
    assert _VisualModel.supports_model_artifacts() is True
    artifacts = _VisualModel().get_model_artifacts(_context())
    assert [a.payload for a in artifacts] == ["a,b"]


def test_metadata_exposes_support_flag():
    assert _PlainModel.get_metadata()["supports_model_artifacts"] is False
    assert _VisualModel.get_metadata()["supports_model_artifacts"] is True
