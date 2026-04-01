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


class StableDiffusionXLSchema(BaseSchema):
    """Configuration schema for Stable Diffusion XL text-to-image generation.

    Configures the checkpoint variant (``model_name``), prompt conditioning
    (``negative_prompt``), denoising schedule (``num_inference_steps``),
    classifier-free guidance strength (``guidance_scale``), output dimensions
    (``width``, ``height``), reproducibility (``seed``), hardware target
    (``device``), and batch size (``num_images_per_prompt``) for
    ``StableDiffusionXLModel``.
    """

    model_name: schema_field(
        enum_field(
            enum=[
                "stabilityai/stable-diffusion-xl-base-1.0",
                "SG161222/RealVisXL_V4.0",
            ]
        ),
        placeholder="stabilityai/stable-diffusion-xl-base-1.0",
        description=MultilingualString(
            en=(
                "The Stable Diffusion XL checkpoint to load. "
                "'stable-diffusion-xl-base-1.0' is the official base model trained "
                "at 1024x1024 px for high-quality photorealistic generation. "
                "'RealVisXL_V4.0' is a popular community fine-tune of SDXL "
                "optimized for realistic portraits and photography."
            ),
            es=(
                "El checkpoint Stable Diffusion XL a cargar. "
                "'stable-diffusion-xl-base-1.0' es el modelo base oficial entrenado "
                "a 1024x1024 px para generación fotorrealista de alta calidad. "
                "'RealVisXL_V4.0' es un popular fine-tune comunitario de SDXL "
                "optimizado para retratos realistas y fotografía."
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
                    "marca de agua'. "
                    "Dejar vacío para omitir el condicionamiento negativo."
                ),
            ),
            alias=MultilingualString(en="Negative prompt", es="Prompt negativo"),
        )  # type: ignore
    ]

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=25,
        description=MultilingualString(
            en=(
                "Number of denoising steps to run. More steps refine the image but "
                "increase generation time. Typical range: 20-30 for fast results, "
                "40-50 for higher quality. SDXL achieves good results with 25-40 steps."
            ),
            es=(
                "Número de pasos de eliminación de ruido a ejecutar. Más pasos refinan "
                "la imagen pero aumentan el tiempo de generación. Rango típico: 20-30 "
                "para resultados rápidos, 40-50 para mayor calidad. SDXL logra buenos "
                "resultados con 25-40 pasos."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps", es="Número de pasos de inferencia"
        ),
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=7.0,
        description=MultilingualString(
            en=(
                "Classifier-Free Guidance (CFG) scale. Controls how strictly the "
                "image follows the text prompt. Low values (1-4) allow creative "
                "freedom; medium values (5-9) balance quality and adherence; "
                "high values (10+) enforce the prompt but may produce artifacts. "
                "SDXL works well with values between 5-9."
            ),
            es=(
                "Escala de Classifier-Free Guidance (CFG). Controla qué tan "
                "estrictamente la imagen sigue el prompt. Valores bajos (1-4) permiten "
                "libertad creativa; valores medios (5-9) equilibran calidad y "
                "adherencia; valores altos (10+) refuerzan el prompt pero pueden "
                "producir artefactos. "
                "SDXL funciona bien con valores entre 5-9."
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
                "acceleration, strongly recommended for SDXL. CPU inference is very "
                "slow for this large model; expect 10-30 minutes per image on CPU."
            ),
            es=(
                "Dispositivo de hardware para la inferencia. Seleccione GPU para "
                "aceleración por hardware, muy recomendado para SDXL. La inferencia "
                "en CPU es muy lenta para este modelo grande; espere 10-30 minutos "
                "por imagen en CPU."
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
        placeholder=1024,
        description=MultilingualString(
            en=(
                "Width of the output image in pixels. Must be a multiple of 8. "
                "SDXL's native resolution is 1024x1024 px. Using non-native "
                "resolutions may reduce quality."
            ),
            es=(
                "Ancho de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "La resolución nativa de SDXL es 1024x1024 px. Usar resoluciones no "
                "nativas puede reducir la calidad."
            ),
        ),
        alias=MultilingualString(en="Width", es="Ancho"),
    )  # type: ignore

    height: schema_field(
        int_field(ge=64, le=2048),
        placeholder=1024,
        description=MultilingualString(
            en=(
                "Height of the output image in pixels. Must be a multiple of 8. "
                "SDXL's native resolution is 1024x1024 px."
            ),
            es=(
                "Altura de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "La resolución nativa de SDXL es 1024x1024 px."
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


class StableDiffusionXLModel(TextToImageGenerationTaskModel):
    """Latent diffusion model for high-resolution 1024 px text-to-image generation.

    Wraps Stable Diffusion XL (SDXL) checkpoints. SDXL scales the standard
    SD architecture with a larger U-Net backbone and a two-text-encoder
    conditioning stack (OpenCLIP-ViT/G + CLIP-ViT/L), enabling significantly
    better prompt following and photorealism at 1024 x 1024 px compared to
    SD 1.x/2.x.

    Two checkpoints are supported: the official
    ``stabilityai/stable-diffusion-xl-base-1.0`` and
    ``SG161222/RealVisXL_V4.0``, a popular community fine-tune optimised for
    realistic portraits and photography.

    References
    ----------
    - [1] Podell et al., "SDXL: Improving Latent Diffusion Models for
           High-Resolution Image Synthesis", 2023. https://arxiv.org/abs/2307.01952
    - [2] https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
    """

    SCHEMA = StableDiffusionXLSchema
    COLOR: str = "#0d47a1"
    DISPLAY_NAME: str = MultilingualString(
        en="Stable Diffusion XL",
        es="Stable Diffusion XL",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Stable Diffusion XL (SDXL) is a latent diffusion model by Stability AI "
            "for high-resolution text-to-image generation at 1024x1024 px. It features "
            "a larger U-Net backbone and a second text encoder (OpenCLIP ViT-bigG) "
            "that significantly improves image quality, text rendering, and "
            "compositional accuracy compared to earlier SD versions. Also includes "
            "RealVisXL V4.0, a community fine-tune optimized for photorealistic "
            "portraits and photography. Base model at "
            "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0."
        ),
        es=(
            "Stable Diffusion XL (SDXL) es un modelo de difusión latente de "
            "Stability AI para generación de imágenes de alta resolución a "
            "1024x1024 px. Presenta una arquitectura U-Net más grande y un segundo "
            "codificador de texto (OpenCLIP ViT-bigG) que mejora significativamente "
            "la calidad de imagen, el renderizado de texto y la precisión "
            "composicional respecto a versiones anteriores de SD. También incluye "
            "RealVisXL V4.0, un fine-tune comunitario optimizado para retratos "
            "fotorrealistas y fotografía. Modelo base en "
            "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0."
        ),
    )

    def __init__(self, **kwargs):
        """Initialize the model."""
        import torch
        from diffusers import StableDiffusionXLPipeline

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )
        self.model_name = kwargs.get(
            "model_name", "stabilityai/stable-diffusion-xl-base-1.0"
        )

        self.model = StableDiffusionXLPipeline.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if use_gpu else torch.float32,
            use_safetensors=True,
            variant="fp16" if use_gpu else None,
        ).to(self.device)

        self.negative_prompt = kwargs.get("negative_prompt")
        self.num_inference_steps = kwargs.get("num_inference_steps")
        self.guidance_scale = kwargs.get("guidance_scale")
        self.seed = kwargs.get("seed")
        self.width = kwargs.get("width")
        self.height = kwargs.get("height")
        self.num_images_per_prompt = kwargs.get("num_images_per_prompt")

    def generate(self, input: str) -> List[Any]:
        """Generate images from a text prompt.

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

        output = self.model(**params)
        return output.images
