from typing import Any, List, Optional

from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.text_to_image_generation_model import (
    TextToImageGenerationTaskModel,
)
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


class SDXLTurboSchema(BaseSchema):
    """Schema for SDXL Turbo image generation."""

    negative_prompt: Optional[
        schema_field(
            string_field(),
            placeholder="",
            description=MultilingualString(
                en=(
                    "Text describing what to exclude from the generated image. "
                    "Note: SDXL Turbo uses distillation training and "
                    "guidance_scale=0, so negative prompts have minimal effect. "
                    "Leave empty for best results."
                ),
                es=(
                    "Texto que describe qué excluir de la imagen generada. "
                    "Nota: SDXL Turbo usa entrenamiento por destilación y "
                    "guidance_scale=0, por lo que los prompts negativos tienen "
                    "efecto mínimo. "
                    "Dejar vacío para mejores resultados."
                ),
            ),
            alias=MultilingualString(en="Negative prompt", es="Prompt negativo"),
        )  # type: ignore
    ]

    num_inference_steps: schema_field(
        int_field(ge=1, le=10),
        placeholder=1,
        description=MultilingualString(
            en=(
                "Number of denoising steps. SDXL Turbo is a distilled model that "
                "generates high-quality images in just 1-4 steps. Using 1 step is "
                "fastest; 2-4 steps improve quality slightly. Values above 4 provide "
                "diminishing returns for this model."
            ),
            es=(
                "Número de pasos de eliminación de ruido. SDXL Turbo es un modelo "
                "destilado que genera imágenes de alta calidad en solo 1-4 pasos. "
                "Usar 1 paso es lo más rápido; 2-4 pasos mejoran la calidad "
                "ligeramente. Valores superiores a 4 tienen rendimientos "
                "decrecientes para este modelo."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps", es="Número de pasos de inferencia"
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware device for inference. SDXL Turbo is fast enough that CPU "
                "inference is feasible (30-60 seconds per image). GPU is still "
                "recommended for real-time or batch generation."
            ),
            es=(
                "Dispositivo de hardware para inferencia. SDXL Turbo es lo "
                "suficientemente rápido como para que la inferencia en CPU sea "
                "factible (30-60 segundos por imagen). La GPU sigue siendo "
                "recomendada para generación en tiempo real o por lotes."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore

    seed: schema_field(
        int_field(),
        placeholder=-1,
        description=MultilingualString(
            en=(
                "Random seed for reproducible generation. A fixed positive integer "
                "will always produce the same image for identical settings. "
                "Use a negative value (e.g. -1) for a random seed on each run."
            ),
            es=(
                "Semilla aleatoria para generación reproducible. Un entero positivo "
                "fijo siempre producirá la misma imagen con configuraciones idénticas. "
                "Use un valor negativo (ej. -1) para una semilla aleatoria en "
                "cada ejecución."
            ),
        ),
        alias=MultilingualString(en="Seed", es="Semilla"),
    )  # type: ignore

    width: schema_field(
        int_field(ge=64, le=2048),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Width of the output image in pixels. Must be a multiple of 8. "
                "SDXL Turbo's optimal resolution is 512x512 px. Larger resolutions "
                "may reduce quality as the model was trained at 512 px."
            ),
            es=(
                "Ancho de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "La resolución óptima de SDXL Turbo es 512x512 px. Resoluciones más "
                "grandes pueden reducir la calidad ya que el modelo fue entrenado "
                "a 512 px."
            ),
        ),
        alias=MultilingualString(en="Width", es="Ancho"),
    )  # type: ignore

    height: schema_field(
        int_field(ge=64, le=2048),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Height of the output image in pixels. Must be a multiple of 8. "
                "SDXL Turbo's optimal resolution is 512x512 px."
            ),
            es=(
                "Altura de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "La resolución óptima de SDXL Turbo es 512x512 px."
            ),
        ),
        alias=MultilingualString(en="Height", es="Altura"),
    )  # type: ignore

    num_images_per_prompt: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en=(
                "How many images to generate from a single prompt in one batch. "
                "Since SDXL Turbo is fast, generating multiple images per prompt "
                "is very efficient."
            ),
            es=(
                "Cuántas imágenes generar desde un solo prompt en un lote. "
                "Como SDXL Turbo es rápido, generar múltiples imágenes por prompt "
                "es muy eficiente."
            ),
        ),
        alias=MultilingualString(
            en="Num images per prompt", es="Número de imágenes por prompt"
        ),
    )  # type: ignore


class SDXLTurboModel(TextToImageGenerationTaskModel):
    """SDXL Turbo model for fast single-step text-to-image generation."""

    SCHEMA = SDXLTurboSchema
    COLOR: str = "#b71c1c"
    DISPLAY_NAME: str = MultilingualString(
        en="SDXL Turbo",
        es="SDXL Turbo",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "SDXL Turbo is a distilled version of Stable Diffusion XL by Stability AI "
            "that generates high-quality images in a single denoising step using "
            "Adversarial Diffusion Distillation (ADD). It produces photorealistic "
            "images at 512x512 px resolution up to 30x faster than standard SDXL. "
            "Ideal for interactive and real-time applications. Note: does not use "
            "classifier-free guidance (guidance_scale=0 internally). Model available "
            "at https://huggingface.co/stabilityai/sdxl-turbo."
        ),
        es=(
            "SDXL Turbo es una versión destilada de Stable Diffusion XL por "
            "Stability AI que genera imágenes de alta calidad en un solo paso "
            "de eliminación de ruido "
            "usando Destilación de Difusión Adversarial (ADD). Produce imágenes "
            "fotorrealistas a 512x512 px hasta 30x más rápido que el SDXL estándar. "
            "Ideal para aplicaciones interactivas y en tiempo real. Nota: no usa guía "
            "libre de clasificador (guidance_scale=0 internamente). Modelo "
            "disponible en "
            "https://huggingface.co/stabilityai/sdxl-turbo."
        ),
    )

    def __init__(self, **kwargs):
        """Initialize the model."""
        import torch
        from diffusers import AutoPipelineForText2Image

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )

        self.model = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=torch.float16 if use_gpu else torch.float32,
            variant="fp16" if use_gpu else None,
        ).to(self.device)

        self.negative_prompt = kwargs.get("negative_prompt")
        self.num_inference_steps = kwargs.get("num_inference_steps", 1)
        self.seed = kwargs.get("seed")
        self.width = kwargs.get("width")
        self.height = kwargs.get("height")
        self.num_images_per_prompt = kwargs.get("num_images_per_prompt")

    def generate(self, input: str) -> List[Any]:
        """Generate images from a text prompt using single-step distillation.

        Parameters
        ----------
        input : str
            Text prompt to generate an image from.

        Returns
        -------
        List[Any]
            Generated output images in a list.
        """
        import torch

        generator = None
        if self.seed is not None and self.seed > 0:
            generator = torch.Generator(device=self.device).manual_seed(self.seed)

        output = self.model(
            prompt=input,
            negative_prompt=self.negative_prompt,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=0.0,
            width=self.width,
            height=self.height,
            generator=generator,
            num_images_per_prompt=self.num_images_per_prompt,
        )
        return output.images
