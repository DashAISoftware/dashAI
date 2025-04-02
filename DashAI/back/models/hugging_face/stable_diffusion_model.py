from typing import Any

import torch
from diffusers import DiffusionPipeline

from DashAI.back.models.image_generation_model import ImageGenerationModel


class StableDiffusionModel(ImageGenerationModel):
    """Class for models associated to StableDiffusionProcess."""

    def __init__(self, **kwargs):
        """Initialize the model."""
        super().__init__(**kwargs)

        self.model_name = "stabilityai/stable-diffusion-2-1"
        self.model = DiffusionPipeline.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32 if self.device == "cuda" else torch.float16,
        ).to(self.device)

    def generate(self, input: Any) -> Any:
        """Generate output from a generative model.

        input (Any): Input to the generative model.
        """
        image = self.model(
            input,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=self.guidance_scale,
        ).images[0]
        return image
