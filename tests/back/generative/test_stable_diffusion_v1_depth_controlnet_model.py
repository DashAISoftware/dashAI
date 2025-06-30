import PIL
import PIL.Image
import pytest

from DashAI.back.models.hugging_face.stable_diffusion_v1_depth_controlnet import (
    StableDiffusionXLV1ControlNet,
)


@pytest.fixture(scope="module", name="sample_model")
def sample_model():
    model = StableDiffusionXLV1ControlNet(
        num_inference_steps=1,
        device="cpu",
        controlnet_conditioning_scale=1,
    )
    return model


@pytest.fixture(scope="module", name="sample_image")
def sample_image():
    return PIL.Image.new("RGB", (256, 256), color=(255, 255, 255))


def test_model_initialization(sample_model):
    assert sample_model.num_inference_steps == 1
    assert sample_model.device == "cpu"
    assert sample_model.controlnet_conditioning_scale == 1
    assert sample_model.pipe is not None
    assert sample_model.controlnet is not None
    assert sample_model.vae is not None
