from typing import Any, List, Tuple

import numpy as np
import torch
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
from PIL import Image
from transformers import DPTForDepthEstimation, DPTImageProcessor

from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.controlnet_model import ControlNetModel as BaseControlNetModel
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


class SD15DepthControlNetSchema(BaseSchema):
    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=20,
        description=MultilingualString(
            en=(
                "Number of denoising steps to run. More steps refine the image but "
                "increase generation time. Typical range: 20-30 for fast results, "
                "40-50 for higher quality."
            ),
            es=(
                "Número de pasos de eliminación de ruido. Más pasos refinan la imagen "
                "pero aumentan el tiempo de generación. Rango típico: 20-30 para "
                "resultados rápidos, 40-50 para mayor calidad."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps", es="Número de pasos de inferencia"
        ),
    )  # type: ignore

    controlnet_conditioning_scale: schema_field(
        float_field(ge=0.0),
        placeholder=1.0,
        description=MultilingualString(
            en=(
                "Weight of the ControlNet depth conditioning relative to the base "
                "diffusion pipeline (range 0.0-2.0). At 0.0 the depth map has no "
                "effect; at 1.0 the output closely follows the input structure; "
                "above 1.5 depth dominates and may produce rigid results."
            ),
            es=(
                "Peso del condicionamiento de profundidad ControlNet (rango 0.0-2.0). "
                "En 0.0 el mapa de profundidad no tiene efecto; en 1.0 la salida sigue "
                "la estructura de la entrada; por encima de 1.5 domina la profundidad "
                "y puede producir resultados rígidos."
            ),
        ),
        alias=MultilingualString(
            en="ControlNet conditioning scale",
            es="Escala de condicionamiento ControlNet",
        ),
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=7.5,
        description=MultilingualString(
            en=(
                "Classifier-Free Guidance (CFG) scale. Controls how strictly the "
                "image follows the text prompt. Values 7-9 are typical for SD 1.5."
            ),
            es=(
                "Escala de Classifier-Free Guidance (CFG). Controla qué tan "
                "estrictamente la imagen sigue el prompt. Valores 7-9 son típicos "
                "para SD 1.5."
            ),
        ),
        alias=MultilingualString(en="Guidance scale", es="Escala de guía"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware device for inference. GPU is strongly recommended for "
                "diffusion models. CPU inference is possible but very slow."
            ),
            es=(
                "Dispositivo de hardware para inferencia. Se recomienda GPU para "
                "modelos de difusión. La inferencia en CPU es posible pero muy lenta."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


def get_depth_map_sd15(image, device):
    depth_estimator = DPTForDepthEstimation.from_pretrained(
        "Intel/dpt-hybrid-midas"
    ).to(device)
    feature_extractor = DPTImageProcessor.from_pretrained("Intel/dpt-hybrid-midas")

    pixel_values = feature_extractor(images=image, return_tensors="pt").pixel_values.to(
        device
    )

    with torch.no_grad(), torch.autocast(device, dtype=torch.float16):
        depth_map = depth_estimator(pixel_values).predicted_depth

    depth_map = torch.nn.functional.interpolate(
        depth_map.unsqueeze(1),
        size=(512, 512),
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


class SD15DepthControlNetModel(BaseControlNetModel):
    """ControlNet with depth preprocessing and Stable Diffusion 1.5 as pipeline."""

    SCHEMA = SD15DepthControlNetSchema
    COLOR: str = "#4e342e"
    DISPLAY_NAME: str = MultilingualString(
        en="SD 1.5 Depth ControlNet",
        es="SD 1.5 ControlNet de Profundidad",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Combines ControlNet depth conditioning with Stable Diffusion 1.5 for "
            "structure-aware image generation. Takes an input image and a text prompt: "
            "a depth map is extracted using Intel's DPT-Hybrid-MiDaS model, then used "
            "as a spatial condition to guide image synthesis at 512x512 px. Uses "
            "lllyasviel/sd-controlnet-depth "
            "(https://huggingface.co/lllyasviel/sd-controlnet-depth) and "
            "runwayml/stable-diffusion-v1-5 "
            "(https://huggingface.co/runwayml/stable-diffusion-v1-5)."
        ),
        es=(
            "Combina el condicionamiento de profundidad de ControlNet con Stable "
            "Diffusion 1.5 para generación de imágenes con conciencia de estructura. "
            "Recibe una imagen y un prompt de texto: se extrae un mapa de profundidad "
            "usando DPT-Hybrid-MiDaS de Intel y se usa como condición espacial a "
            "512x512 px. Utiliza lllyasviel/sd-controlnet-depth "
            "(https://huggingface.co/lllyasviel/sd-controlnet-depth) y "
            "runwayml/stable-diffusion-v1-5 "
            "(https://huggingface.co/runwayml/stable-diffusion-v1-5)."
        ),
    )

    def __init__(self, **kwargs: Any):
        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )

        controlnet = ControlNetModel.from_pretrained(
            "lllyasviel/sd-controlnet-depth",
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            controlnet=controlnet,
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.controlnet_conditioning_scale = kwargs.get("controlnet_conditioning_scale")
        self.num_inference_steps = kwargs.get("num_inference_steps")
        self.guidance_scale = kwargs.get("guidance_scale")

        self.pipe.enable_model_cpu_offload()

    def generate(self, input: Tuple[Image.Image, str]) -> List[Any]:
        """Generate output from a generative model.

        Parameters
        ----------
        input : Tuple[Image.Image, str]
            Input image and text prompt.

        Returns
        -------
        List[Any]
            Generated output images in a list.
        """
        image = input[0]
        prompt = input[1]

        depth_map = get_depth_map_sd15(image, self.device)
        output = self.pipe(
            prompt=prompt,
            image=depth_map,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=self.guidance_scale,
            controlnet_conditioning_scale=self.controlnet_conditioning_scale,
        )
        return output.images
