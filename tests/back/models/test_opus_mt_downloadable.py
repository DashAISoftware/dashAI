"""Tests that OpusMtTransformerMixin subclasses expose download metadata."""

import pytest
from kink import di

from DashAI.back.dependencies.downloads.downloadable import HFDownloadableMixin
from DashAI.back.models.hugging_face.opus_mt_en_es_transformer import (
    OpusMtEnESTransformer,
)


@pytest.fixture
def component_root(tmp_path):
    """Inject a temporary COMPONENT_PATH into the kink DI container."""
    sentinel = object()
    old = di["config"] if "config" in di else sentinel  # noqa: SIM401
    di["config"] = {"COMPONENT_PATH": str(tmp_path)}
    yield tmp_path
    if old is sentinel:
        del di["config"]
    else:
        di["config"] = old


def test_opus_mt_is_downloadable():
    assert issubclass(OpusMtEnESTransformer, HFDownloadableMixin)
    assert OpusMtEnESTransformer.REQUIRES_DOWNLOAD is True
    assert OpusMtEnESTransformer.DOWNLOAD_SIZE_BYTES is not None


def test_opus_mt_hf_repos_derived_from_model_name():
    assert OpusMtEnESTransformer.hf_repos() == [("Helsinki-NLP/opus-mt-en-es", "model")]


def test_opus_mt_metadata_flags_download():
    meta = OpusMtEnESTransformer.get_metadata()
    assert meta["requires_download"] is True
    assert meta["download_size_bytes"] == OpusMtEnESTransformer.DOWNLOAD_SIZE_BYTES


def test_opus_mt_is_downloaded_uses_component_dir(component_root):
    assert OpusMtEnESTransformer.is_downloaded() is False

    repo_dir = component_root / "OpusMtEnESTransformer" / "opus-mt-en-es"
    repo_dir.mkdir(parents=True)
    (repo_dir / "config.json").write_text("{}")
    assert OpusMtEnESTransformer.is_downloaded() is True
