from typing import Any, List, Tuple

import torch
from diffusers import ControlNetModel, StableDiffusionControlNetPipeline
from PIL import Image

try:
    from controlnet_aux import OpenposeDetector
except ImportError:
    OpenposeDetector = None

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


class SD15OpenPoseControlNetSchema(BaseSchema):
    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=20,
        description=MultilingualString(
            en=(
                "Number of denoising steps. Typical range: 20-30 for fast results, "
                "40-50 for higher quality."
            ),
            es=(
                "Número de pasos de eliminación de ruido. Rango típico: 20-30 para "
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
                "Weight of the ControlNet pose conditioning (range 0.0-2.0). "
                "At 1.0 the output closely follows the input pose. Lower values "
                "allow more creative freedom while preserving the general pose."
            ),
            es=(
                "Peso del condicionamiento de pose ControlNet (rango 0.0-2.0). "
                "En 1.0 la salida sigue de cerca la pose de entrada. Valores menores "
                "permiten más libertad creativa manteniendo la pose general."
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
                "Classifier-Free Guidance (CFG) scale. Controls prompt adherence. "
                "Values 7-9 are typical for SD 1.5."
            ),
            es=(
                "Escala CFG. Controla la adherencia al prompt. "
                "Valores 7-9 son típicos para SD 1.5."
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
                "Dispositivo de hardware para inferencia. Se recomienda GPU. "
                "La inferencia en CPU es posible pero muy lenta."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class SD15OpenPoseControlNetModel(BaseControlNetModel):
    """ControlNet with OpenPose preprocessing and Stable Diffusion 1.5 pipeline."""

    SCHEMA = SD15OpenPoseControlNetSchema
    COLOR: str = "#880e4f"
    DISPLAY_NAME: str = MultilingualString(
        en="SD 1.5 OpenPose ControlNet",
        es="SD 1.5 ControlNet OpenPose",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Combines ControlNet pose conditioning with Stable Diffusion 1.5 for "
            "pose-guided image generation. Takes an input image and a text prompt: "
            "human poses are detected using OpenposeDetector from controlnet_aux, "
            "then used as spatial conditions for image synthesis. Ideal for "
            "generating images with specific human poses or body positions. Uses "
            "lllyasviel/sd-controlnet-openpose "
            "(https://huggingface.co/lllyasviel/sd-controlnet-openpose) and "
            "runwayml/stable-diffusion-v1-5 "
            "(https://huggingface.co/runwayml/stable-diffusion-v1-5). "
            "Requires the controlnet_aux library: pip install controlnet_aux."
        ),
        es=(
            "Combina el condicionamiento de pose de ControlNet con Stable "
            "Diffusion 1.5 para generación de imágenes guiada por pose. "
            "Recibe una imagen y un prompt: las poses humanas se detectan "
            "usando OpenposeDetector de controlnet_aux y se usan como "
            "condiciones espaciales. Ideal para generar imágenes con poses "
            "humanas específicas. Utiliza lllyasviel/sd-controlnet-openpose "
            "(https://huggingface.co/lllyasviel/sd-controlnet-openpose) y "
            "runwayml/stable-diffusion-v1-5 "
            "(https://huggingface.co/runwayml/stable-diffusion-v1-5). "
            "Requiere la librería controlnet_aux: pip install controlnet_aux."
        ),
    )

    def __init__(self, **kwargs: Any):
        if OpenposeDetector is None:
            raise RuntimeError(
                "controlnet_aux is not installed. "
                "Please install it with: pip install controlnet_aux"
            )

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )

        self.pose_detector = OpenposeDetector.from_pretrained("lllyasviel/Annotators")

        controlnet = ControlNetModel.from_pretrained(
            "lllyasviel/sd-controlnet-openpose",
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

        pose_image = self.pose_detector(image)
        output = self.pipe(
            prompt=prompt,
            image=pose_image,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=self.guidance_scale,
            controlnet_conditioning_scale=self.controlnet_conditioning_scale,
        )
        return output.images
