from typing import Any

import torch
from diffusers import DiffusionPipeline

from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    float_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.models.image_generation_model import ImageGenerationModel


class StableDiffusionSchema(BaseSchema):
    """Schema for Stable Diffusion image generation."""

    negative_prompt: schema_field(
        string_field(),
        placeholder="",
        description="Text prompt for elements to avoid in the image.",
    )  # type: ignore

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=10,
        description="Number of denoising steps. Higher usually leads to better quality but slower inference.",
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=7.5,
        description="How strongly the model follows the prompt. Higher = closer to prompt, but may reduce image quality.",
    )  # type: ignore

    device: schema_field(
        enum_field(enum=["cuda", "cpu"]),
        placeholder="cuda",
        description="Device for generation. Use 'cuda' if GPU is available.",
    )  # type: ignore

    seed: schema_field(
        int_field(),
        placeholder=42,
        description="Random seed for reproducibility. Use negative value for random seed.",
    )  # type: ignore

    width: schema_field(
        int_field(ge=64, le=2048),
        placeholder=512,
        description="Width of the generated image. Must be a multiple of 8.",
    )  # type: ignore

    height: schema_field(
        int_field(ge=64, le=2048),
        placeholder=512,
        description="Height of the generated image. Must be a multiple of 8.",
    )  # type: ignore

    num_images_per_prompt: schema_field(
        int_field(ge=1),
        placeholder=1,
        description="Number of images to generate per prompt.",
    )  # type: ignore


class StableDiffusionModel(ImageGenerationModel):
    """Class for models associated to StableDiffusionProcess."""

    SCHEMA = StableDiffusionSchema

    def __init__(self, **kwargs):
        """Initialize the model."""
        kwargs = self.validate_and_transform(kwargs)
        self.device = kwargs.get("device")
        self.model_name = "stabilityai/stable-diffusion-2-1"

        self.model = DiffusionPipeline.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32,
        ).to(self.device)

        self.negative_prompt = kwargs.get("negative_prompt")
        self.num_inference_steps = kwargs.get("num_inference_steps")
        self.guidance_scale = kwargs.get("guidance_scale")
        self.seed = kwargs.get("seed")
        self.width = kwargs.get("width")
        self.height = kwargs.get("height")
        self.num_images_per_prompt = kwargs.get("num_images_per_prompt")

    def generate(self, input: Any) -> Any:
        """Generate output from a generative model.

        input (Any): Input to the generative model.
        """
        generator = None
        if self.seed is not None and self.seed > 0:
            generator = torch.Generator(device=self.device).manual_seed(self.seed)

        output = self.model(
            prompt=input,
            negative_prompt=self.negative_prompt,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=self.guidance_scale,
            width=self.width,
            height=self.height,
            generator=generator,
            num_images_per_prompt=self.num_images_per_prompt,
        )

        return output.images[0]
