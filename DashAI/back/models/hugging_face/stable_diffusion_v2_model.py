from typing import Any, List, Optional

import torch
from diffusers import DiffusionPipeline

from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
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


class StableDiffusionSchema(BaseSchema):
    """Schema for Stable Diffusion V2 image generation."""

    model_name: schema_field(
        enum_field(
            enum=[
                "stabilityai/stable-diffusion-2",
                "stabilityai/stable-diffusion-2-base",
                "stabilityai/stable-diffusion-2-1",
                "stabilityai/stable-diffusion-2-1-base",
            ]
        ),
        placeholder="stabilityai/stable-diffusion-2",
        description=MultilingualString(
            en="The specific Stable Diffusion model version to use.",
            es="La versión específica del modelo Stable Diffusion a usar.",
        ),
        alias=MultilingualString(en="Model name", es="Nombre del modelo"),
    )  # type: ignore

    negative_prompt: Optional[
        schema_field(
            string_field(),
            placeholder="",
            description=MultilingualString(
                en="Text prompt for elements to avoid in the image.",
                es="Prompt de texto para elementos a evitar en la imagen.",
            ),
            alias=MultilingualString(en="Negative prompt", es="Prompt negativo"),
        )  # type: ignore
    ]

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=15,
        description=MultilingualString(
            en=(
                "Number of denoising steps. Higher usually leads to better quality "
                "but slower inference."
            ),
            es=(
                "Número de pasos de eliminación de ruido. Más alto generalmente "
                "lleva a mejor calidad pero inferencia más lenta."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps", es="Número de pasos de inferencia"
        ),
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=3.5,
        description=MultilingualString(
            en=(
                "How strongly the model follows the prompt. Higher = closer to "
                "prompt, but may reduce image quality."
            ),
            es=(
                "Qué tan fuertemente el modelo sigue el prompt. Mayor = más cercano "
                "al prompt, pero puede reducir la calidad de imagen."
            ),
        ),
        alias=MultilingualString(en="Guidance scale", es="Escala de guía"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en="Device for generation. Use 'cuda' if GPU is available.",
            es="Dispositivo para generación. Use 'cuda' si GPU está disponible.",
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore

    seed: schema_field(
        int_field(),
        placeholder=-1,
        description=MultilingualString(
            en=("Random seed for reproducibility. Use negative value for random seed."),
            es=(
                "Semilla aleatoria para reproducibilidad. Use valor negativo para "
                "semilla aleatoria."
            ),
        ),
        alias=MultilingualString(en="Seed", es="Semilla"),
    )  # type: ignore

    width: schema_field(
        int_field(ge=64, le=2048),
        placeholder=512,
        description=MultilingualString(
            en="Width of the generated image. Must be a multiple of 8.",
            es="Ancho de la imagen generada. Debe ser múltiplo de 8.",
        ),
        alias=MultilingualString(en="Width", es="Ancho"),
    )  # type: ignore

    height: schema_field(
        int_field(ge=64, le=2048),
        placeholder=512,
        description=MultilingualString(
            en="Height of the generated image. Must be a multiple of 8.",
            es="Altura de la imagen generada. Debe ser múltiplo de 8.",
        ),
        alias=MultilingualString(en="Height", es="Altura"),
    )  # type: ignore

    num_images_per_prompt: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en="Number of images to generate per prompt.",
            es="Número de imágenes a generar por prompt.",
        ),
        alias=MultilingualString(
            en="Num images per prompt", es="Número de imágenes por prompt"
        ),
    )  # type: ignore


class StableDiffusionV2Model(TextToImageGenerationTaskModel):
    """Wrapper model for all Stable Diffusion 2.x models from stability.ai."""

    SCHEMA = StableDiffusionSchema
    COLOR: str = "#1565c0"
    DISPLAY_NAME: str = MultilingualString(
        en="Stable Diffusion V2",
        es="Stable Diffusion V2",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Stable Diffusion 2.x is a latent diffusion model by Stability AI for "
            "high-resolution text-to-image generation. It uses a U-Net denoiser "
            "conditioned on CLIP text embeddings and a variational autoencoder (VAE) "
            "to produce detailed images from text prompts. Supports stable-diffusion-2, "
            "stable-diffusion-2-base, stable-diffusion-2-1, and "
            "stable-diffusion-2-1-base variants. Models are available at "
            "https://huggingface.co/stabilityai."
        ),
        es=(
            "Stable Diffusion 2.x es un modelo de difusión latente de Stability AI "
            "para generación de imágenes de alta resolución a partir de texto. Utiliza "
            "un denoiser U-Net condicionado en embeddings de texto CLIP y un "
            "autoencoder variacional (VAE) para producir imágenes detalladas. Soporta "
            "las variantes stable-diffusion-2, stable-diffusion-2-base, "
            "stable-diffusion-2-1 y stable-diffusion-2-1-base. Los modelos están "
            "disponibles en https://huggingface.co/stabilityai."
        ),
    )

    def __init__(self, **kwargs):
        """Initialize the model."""
        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )
        self.model_name = kwargs.get("model_name", "stabilityai/stable-diffusion-2")

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
