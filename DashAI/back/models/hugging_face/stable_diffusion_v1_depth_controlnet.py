from typing import Any, List, Tuple

import numpy as np
import torch
from diffusers import (
    AutoencoderKL,
    ControlNetModel,
    StableDiffusionXLControlNetPipeline,
)
from PIL import Image
from transformers import DPTFeatureExtractor, DPTForDepthEstimation

from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.models.controlnet_model import ControlNetModel as BaseControlNetModel

if torch.cuda.is_available():
    DEVICE_ENUM = [f"cuda:{i}" for i in range(torch.cuda.device_count())] + ["cpu"]
    DEVICE_PLACEHOLDER = "cuda:0"
else:
    DEVICE_ENUM = ["cpu"]
    DEVICE_PLACEHOLDER = "cpu"


class StableDiffusionXLV1ControlNetSchema(BaseSchema):
    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=15,
        description=(
            "Number of denoising steps. Higher usually leads to better quality but "
            "slower inference."
        ),
    )  # type: ignore

    controlnet_conditioning_scale: schema_field(
        float_field(ge=0.0),
        placeholder=1.0,
        description=(
            "Scale for the ControlNet conditioning. Higher values make the model "
            "follow the controlnet more closely."
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description="Device for generation. Use 'cuda' if GPU is available.",
    )  # type: ignore


def get_depth_map(image, device):
    depth_estimator = DPTForDepthEstimation.from_pretrained(
        "Intel/dpt-hybrid-midas"
    ).to(device)
    feature_extractor = DPTFeatureExtractor.from_pretrained(
        "Intel/dpt-hybrid-midas", device=device
    )

    image = feature_extractor(images=image, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad(), torch.autocast(device, dtype=torch.float16):
        depth_map = depth_estimator(image).predicted_depth

    depth_map = torch.nn.functional.interpolate(
        depth_map.unsqueeze(1),
        size=(1024, 1024),
        mode="bicubic",
        align_corners=False,
    )
    depth_min = torch.amin(depth_map, dim=[1, 2, 3], keepdim=True)
    depth_max = torch.amax(depth_map, dim=[1, 2, 3], keepdim=True)
    depth_map = (depth_map - depth_min) / (depth_max - depth_min)
    image = torch.cat([depth_map] * 3, dim=1)

    image = image.permute(0, 2, 3, 1).cpu().numpy()[0]
    image = Image.fromarray((image * 255.0).clip(0, 255).astype(np.uint8))
    return image


class StableDiffusionXLV1ControlNet(BaseControlNetModel):
    """A wrapper implementation of ControlNet with depth preprocessing and stable
    diffusion xl 1.0 as pipeline."""

    SCHEMA = StableDiffusionXLV1ControlNetSchema

    def __init__(self, **kwargs: Any):
        """Initialize the generative model."""
        kwargs = self.validate_and_transform(kwargs)
        self.device = kwargs.get("device")

        self.controlnet = ControlNetModel.from_pretrained(
            "diffusers/controlnet-depth-sdxl-1.0-small",
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.vae = AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix",
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            controlnet=self.controlnet,
            vae=self.vae,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.controlnet_conditioning_scale = kwargs.get("controlnet_conditioning_scale")
        self.num_inference_steps = kwargs.get("num_inference_steps")

        self.pipe.enable_model_cpu_offload()

    def generate(self, input: Tuple[Image.Image, str]) -> List[Any]:
        """Generate output from a generative model.

        Parameters
        ----------
        input : Tuple[Image.Image, str]
            Input data to be generated

        Returns
        -------
        List[Any]
            Generated output data in a list
        """
        image = input[0]
        prompt = input[1]

        depth_map = get_depth_map(image, self.device)
        image = self.pipe(
            prompt=prompt,
            image=depth_map,
            num_inference_steps=self.num_inference_steps,
            controlnet_conditioning_scale=self.controlnet_conditioning_scale,
            height=image.size[1],
            width=image.size[0],
        ).images

        return image
