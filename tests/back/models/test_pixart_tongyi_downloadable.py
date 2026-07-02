"""Tests that PixArt-Sigma / Tongyi Z-Image models expose download metadata."""

import pytest

from DashAI.back.dependencies.downloads.downloadable import HFPretrainedDownloadMixin
from DashAI.back.models.hugging_face.pixart_sigma_model import (
    PixArtSigma512,
    PixArtSigma1024,
)
from DashAI.back.models.hugging_face.tongyi_z_image_model import (
    TongyiZImage,
    TongyiZImageTurbo,
)

_CASES = [
    (PixArtSigma1024, "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"),
    (PixArtSigma512, "PixArt-alpha/PixArt-Sigma-XL-2-512-MS"),
    (TongyiZImage, "Tongyi-MAI/Z-Image"),
    (TongyiZImageTurbo, "Tongyi-MAI/Z-Image-Turbo"),
]


@pytest.mark.parametrize(("model_cls", "repo_id"), _CASES)
def test_is_downloadable(model_cls, repo_id):
    assert issubclass(model_cls, HFPretrainedDownloadMixin)
    assert model_cls.REQUIRES_DOWNLOAD is True
    assert model_cls.DOWNLOAD_SIZE_BYTES is not None
    assert model_cls.hf_repos() == [(repo_id, "model")]


@pytest.mark.parametrize(("model_cls", "repo_id"), _CASES)
def test_metadata_flags_download(model_cls, repo_id):
    meta = model_cls.get_metadata()
    assert meta["requires_download"] is True
    assert meta["download_size_bytes"] == model_cls.DOWNLOAD_SIZE_BYTES
