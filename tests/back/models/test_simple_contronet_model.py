import PIL
import PIL.Image
import pytest

from DashAI.back.models.hugging_face.simple_controlnet_model import (
    SimpleControlNetModel,
)


@pytest.fixture(scope="module", name="sample_model")
def sample_model():
    model = SimpleControlNetModel(
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


def test_generate(sample_model, sample_image):
    input_text = "A beautiful landscape with mountains and a river"
    output_images = sample_model.generate((sample_image, input_text))

    assert isinstance(output_images, list)
    assert len(output_images) == 1
    assert isinstance(output_images[0], PIL.Image.Image)
    assert output_images[0].size == sample_image.size
