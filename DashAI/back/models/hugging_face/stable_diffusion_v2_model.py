from typing import Any, List, Optional

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
                "sd2-community/stable-diffusion-2",
                "sd2-community/stable-diffusion-2-base",
                "sd2-community/stable-diffusion-2-1",
                "sd2-community/stable-diffusion-2-1-base",
            ]
        ),
        placeholder="sd2-community/stable-diffusion-2",
        description=MultilingualString(
            en=(
                "The specific Stable Diffusion 2.x checkpoint to load. "
                "The '-base' variants are trained at 512x512 px and are faster; "
                "the non-base variants target 768x768 px and produce sharper detail. "
                "The '2-1' variants are fine-tuned further "
                "and generally outperform '2'."
            ),
            es=(
                "El checkpoint específico de Stable Diffusion 2.x a cargar. "
                "Las variantes '-base' se entrenan a 512x512 px y son más rápidas; "
                "las variantes sin '-base' apuntan a 768x768 px "
                "y producen mayor detalle. "
                "Las variantes '2-1' están más ajustadas "
                "y generalmente superan a '2'."
            ),
        ),
        alias=MultilingualString(en="Model name", es="Nombre del modelo"),
    )  # type: ignore

    negative_prompt: Optional[
        schema_field(
            string_field(),
            placeholder="",
            description=MultilingualString(
                en=(
                    "Text describing what to exclude from the generated image. "
                    "Common values: 'blurry, low quality, distorted, watermark'. "
                    "Leave empty to skip negative conditioning."
                ),
                es=(
                    "Texto que describe qué excluir de la imagen generada. "
                    "Valores comunes: 'borroso, baja calidad, distorsionado, "
                    "marca de agua'. Dejar vacío para omitir "
                    "el condicionamiento negativo."
                ),
            ),
            alias=MultilingualString(en="Negative prompt", es="Prompt negativo"),
        )  # type: ignore
    ]

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=15,
        description=MultilingualString(
            en=(
                "Number of denoising steps to run. More steps refine the image but "
                "increase generation time. Typical range: 15-30 for fast results, "
                "40-50 for higher quality. Values above 100 rarely improve output."
            ),
            es=(
                "Número de pasos de eliminación de ruido a ejecutar. Más pasos refinan "
                "la imagen pero aumentan el tiempo de generación. Rango típico: 15-30 "
                "para resultados rápidos, 40-50 para mayor calidad. Valores superiores "
                "a 100 raramente mejoran el resultado."
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
                "Classifier-Free Guidance (CFG) scale. Controls how strictly the "
                "image follows the text prompt. Low values (1-4) allow creative "
                "freedom; medium values (5-9) balance quality and adherence; "
                "high values (10+) enforce the prompt but may produce artifacts."
            ),
            es=(
                "Escala de Classifier-Free Guidance (CFG). Controla qué tan "
                "estrictamente la imagen sigue el prompt de texto. Valores bajos "
                "(1-4) permiten libertad creativa; valores medios (5-9) equilibran "
                "calidad y adherencia; valores altos (10+) refuerzan el prompt pero "
                "pueden producir artefactos."
            ),
        ),
        alias=MultilingualString(en="Guidance scale", es="Escala de guía"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware device for inference. Select a GPU option for hardware "
                "acceleration, which is strongly recommended for diffusion models. "
                "Select 'CPU' on systems without a compatible GPU, but expect "
                "significantly longer generation times."
            ),
            es=(
                "Dispositivo de hardware para la inferencia. Seleccione una opción "
                "de GPU para aceleración por hardware, muy recomendado para modelos "
                "de difusión. Seleccione 'CPU' en sistemas sin GPU compatible, pero "
                "espere tiempos de generación significativamente más largos."
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
                "Use un valor negativo (ej. -1) para una semilla aleatoria en cada "
                "ejecución."
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
                "Native resolution is 512 for '-base' variants and 768 for others. "
                "Using the native resolution produces the best quality results."
            ),
            es=(
                "Ancho de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "La resolución nativa es 512 para variantes '-base' y 768 para las "
                "demás. Usar la resolución nativa produce los mejores resultados."
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
                "Native resolution is 512 for '-base' variants and 768 for others. "
                "Using the native resolution produces the best quality results."
            ),
            es=(
                "Altura de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "La resolución nativa es 512 para variantes '-base' y 768 para las "
                "demás. Usar la resolución nativa produce los mejores resultados."
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
                "Increasing this value is more efficient than running multiple "
                "sessions, but requires proportionally more GPU memory."
            ),
            es=(
                "Cuántas imágenes generar desde un solo prompt en un lote. "
                "Aumentar este valor es más eficiente que ejecutar varias sesiones, "
                "pero requiere proporcionalmente más memoria GPU."
            ),
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
            "to produce detailed images from text prompts. "
            "Supports stable-diffusion-2, "
            "stable-diffusion-2-base, stable-diffusion-2-1, and "
            "stable-diffusion-2-1-base variants. Models are served from the "
            "sd2-community organization (https://huggingface.co/sd2-community), "
            "a community mirror of the original Stability AI weights which have been "
            "deprecated and removed from https://huggingface.co/stabilityai."
        ),
        es=(
            "Stable Diffusion 2.x es un modelo de difusión latente de Stability AI "
            "para generación de imágenes de alta resolución a partir de texto. Utiliza "
            "un denoiser U-Net condicionado en embeddings de texto CLIP y un "
            "autoencoder variacional (VAE) para producir imágenes detalladas. Soporta "
            "las variantes stable-diffusion-2, stable-diffusion-2-base, "
            "stable-diffusion-2-1 y stable-diffusion-2-1-base. Los modelos se sirven "
            "desde la organización sd2-community "
            "(https://huggingface.co/sd2-community), un espejo comunitario de los "
            "pesos originales de Stability AI que han sido deprecados y eliminados de "
            "https://huggingface.co/stabilityai."
        ),
    )

    def __init__(self, **kwargs):
        """Initialize the model."""
        import torch
        from diffusers import DiffusionPipeline

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )
        self.model_name = kwargs.get("model_name", "sd2-community/stable-diffusion-2")

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
        import torch

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
