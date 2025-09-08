from typing import Any, List, Optional

import torch
from diffusers import DiffusionPipeline
from huggingface_hub import login

from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.models.text_to_image_generation_model import (
    TextToImageGenerationTaskModel,
)

if torch.cuda.is_available():
    DEVICE_ENUM = [f"cuda:{i}" for i in range(torch.cuda.device_count())] + ["cpu"]
    DEVICE_PLACEHOLDER = "cuda:0"
else:
    DEVICE_ENUM = ["cpu"]
    DEVICE_PLACEHOLDER = "cpu"


class StableDiffusionSchema(BaseSchema):
    """Schema for Stable Diffusion V3 image generation."""

    model_name: schema_field(
        enum_field(
            enum=[
                "stabilityai/stable-diffusion-3-medium-diffusers",
                "stabilityai/stable-diffusion-3.5-medium",
                "stabilityai/stable-diffusion-3.5-large",
                "stabilityai/stable-diffusion-3.5-large-turbo",
            ]
        ),
        placeholder="stabilityai/stable-diffusion-3-medium-diffusers",
        description="The specific Stable Diffusion model version to use.",
    )  # type: ignore

    huggingface_key: schema_field(
        string_field(),
        placeholder="",
        description="Hugging Face API key for private models.",
    )  # type: ignore

    negative_prompt: Optional[
        schema_field(
            string_field(),
            placeholder="",
            description="Text prompt for elements to avoid in the image.",
        )  # type: ignore
    ]

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=15,
        description=(
            "Number of denoising steps. Higher usually leads to better quality but "
            "slower inference."
        ),
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=3.5,
        description=(
            "How strongly the model follows the prompt. Higher = closer to prompt, "
            "but may reduce image quality."
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description="Device for generation. Use 'cuda' if GPU is available.",
    )  # type: ignore

    seed: schema_field(
        int_field(),
        placeholder=-1,
        description=(
            "Random seed for reproducibility. Use negative value for random seed."
        ),
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


class StableDiffusionV3Model(TextToImageGenerationTaskModel):
    """Wrapper model for all Stable Diffusion 3.x models from stability.ai."""

    SCHEMA = StableDiffusionSchema

    def __init__(self, **kwargs):
        """Initialize the model."""
        kwargs = self.validate_and_transform(kwargs)
        self.device = kwargs.get("device")
        self.model_name = kwargs.get(
            "model_name", "stabilityai/stable-diffusion-3-medium-diffusers"
        )
        self.huggingface_key = kwargs.get("huggingface_key")

        if self.huggingface_key:
            try:
                login(token=self.huggingface_key)
            except Exception as e:
                raise ValueError(
                    "Failed to login to Hugging Face. Please check your API key."
                ) from e

        try:
            self.model = DiffusionPipeline.from_pretrained(
                self.model_name,
            ).to(self.device)
        except Exception as e:
            raise ValueError(f"Failed to load model {self.model_name}. {e}") from e

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

    def generate(self, input: str) -> List[Any]:
        """Generate output from a generative model.

        Parameters
        ----------
        input : str
            Input data to be generated

        Returns
        -------
        List[Any]
            Generated output images in a list

        """
        generator = None
        if self.seed is not None and self.seed > 0:
            generator = torch.Generator(device=self.device).manual_seed(self.seed)

        # Base parameters for all models
        params = {
            "prompt": input,
            "negative_prompt": self.negative_prompt,
            "num_inference_steps": self.num_inference_steps,
            "guidance_scale": self.guidance_scale,
            "width": self.width,
            "height": self.height,
            "generator": generator,
            "num_images_per_prompt": self.num_images_per_prompt,
        }

        # Generate images
        output = self.model(**params)

        return output.images
