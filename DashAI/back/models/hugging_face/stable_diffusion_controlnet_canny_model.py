from typing import Any, List, Tuple

import cv2
import PIL
import PIL.Image
import torch
import torchvision.transforms.functional as f
from diffusers import SD3ControlNetModel, StableDiffusion3ControlNetPipeline
from diffusers.image_processor import VaeImageProcessor
from huggingface_hub import login

from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.models.controlnet_model import ControlNetModel


class StableDiffusionControlNetCannySchema(BaseSchema):
    """Schema for Stable Diffusion ControlNet with canny model."""

    huggingface_key: schema_field(
        string_field(),
        placeholder="",
        description="Hugging Face API key for private models.",
    )  # type: ignore

    negative_prompt: schema_field(
        string_field(),
        placeholder="",
        description="Text prompt for elements to avoid in the image.",
    )  # type: ignore

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
        enum_field(enum=["cuda", "cpu"] if torch.cuda.is_available() else ["cpu"]),
        placeholder="cuda" if torch.cuda.is_available() else "cpu",
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

    controlnet_conditioning_scale: schema_field(
        float_field(ge=0.0),
        placeholder=1.0,
        description=(
            "Scale for the ControlNet conditioning. Higher values make the model "
            "follow the controlnet more closely."
        ),
    )  # type: ignore


class SD3CannyImageProcessor(VaeImageProcessor):
    def __init__(self):
        super().__init__(do_normalize=False)

    def preprocess(self, image, **kwargs):
        image = super().preprocess(image, **kwargs)
        image = image * 255 * 0.5 + 0.5
        return image

    def postprocess(self, image, do_denormalize=True, **kwargs):
        do_denormalize = [True] * image.shape[0]
        image = super().postprocess(image, **kwargs, do_denormalize=do_denormalize)
        return image


class StableDiffusionControlNetCannyModel(ControlNetModel):
    """Model for Stable Diffusion ControlNet using canny as preprocessor."""

    SCHEMA = StableDiffusionControlNetCannySchema

    def __init__(self, **kwargs):
        """Initialize the model."""
        kwargs = self.validate_and_transform(kwargs)
        self.device = kwargs.get("device")
        self.model_name = kwargs.get("model_name")
        self.huggingface_key = kwargs.get("huggingface_key")

        if self.huggingface_key:
            try:
                login(token=self.huggingface_key)
            except Exception as e:
                raise ValueError(
                    "Failed to login to Hugging Face. Please check your API key."
                ) from e

        try:
            self.controlnet = SD3ControlNetModel.from_pretrained(
                "stabilityai/stable-diffusion-3.5-large-controlnet-canny",
                torch_dtype=torch.float16,
            )

            self.model = StableDiffusion3ControlNetPipeline.from_pretrained(
                "stabilityai/stable-diffusion-3.5-large",
                controlnet=self.controlnet,
                torch_dtype=torch.float16,
            ).to(self.device)

            self.model.image_processor = SD3CannyImageProcessor()
        except Exception as e:
            raise ValueError(f"Failed to load model {self.model_name}. {e}") from e

        self.negative_prompt = kwargs.get("negative_prompt")
        self.num_inference_steps = kwargs.get("num_inference_steps")
        self.guidance_scale = kwargs.get("guidance_scale")
        self.seed = kwargs.get("seed")
        self.width = kwargs.get("width")
        self.height = kwargs.get("height")
        self.controlnet_conditioning_scale = kwargs.get("controlnet_conditioning_scale")
        self.num_images_per_prompt = kwargs.get("num_images_per_prompt")

    def generate(self, input: Tuple[PIL.Image.Image, str]) -> List[Any]:
        """Generate output from a generative model.

        Parameters
        ----------
        input : List[PIL.Image.Image, str]
            Input data to be generated. The first element is the input image and the
            second element is the prompt.

        Returns
        -------
        List[Any]
            Generated output images in a list

        """

        generator = None
        if self.seed is not None and self.seed > 0:
            generator = torch.Generator(device=self.device).manual_seed(self.seed)

        image = input[0]
        prompt = input[1]

        image = f.to_tensor(image)
        image = cv2.cvtColor(image.transpose(1, 2, 0), cv2.COLOR_RGB2GRAY)
        image = cv2.Canny(image, 100, 200)

        # Base parameters for all models
        params = {
            "prompt": prompt,
            "control_image": image,
            "controlnet_conditioning_scale": self.controlnet_conditioning_scale,
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
