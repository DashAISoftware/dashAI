# flake8: noqa: ERA001
import pytest

from DashAI.back.models.hugging_face.stable_diffusion_v2_model import (
    StableDiffusionV2Model,
)


@pytest.fixture(scope="module", name="sample_model")
def sample_model():
    model = StableDiffusionV2Model(
        model_name="stabilityai/stable-diffusion-2",
        negative_prompt="",
        num_inference_steps=1,
        guidance_scale=6.0,
        device="cpu",
        seed=42,
        width=256,
        height=256,
        num_images_per_prompt=1,
    )
    return model


def test_model_initialization(sample_model):
    assert sample_model.model is not None
    assert sample_model.model_name == "stabilityai/stable-diffusion-2"
    assert sample_model.negative_prompt == ""
    assert sample_model.num_inference_steps == 1
    assert sample_model.guidance_scale == 6.0
    assert sample_model.device == "cpu"
    assert sample_model.seed == 42
    assert sample_model.width == 256
    assert sample_model.height == 256
    assert sample_model.num_images_per_prompt == 1


# def test_generate(sample_model):
#     input_text = "A beautiful landscape with mountains and a river"
#     output_images = sample_model.generate(input_text)

#     assert isinstance(output_images, list)
#     assert len(output_images) == sample_model.num_images_per_prompt
#     assert all(isinstance(img, PIL.Image.Image) for img in output_images)
#     assert all(
#         img.size == (sample_model.width, sample_model.height) for img in output_images
#     )
