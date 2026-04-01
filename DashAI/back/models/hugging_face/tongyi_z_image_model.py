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


class TongyiZImageSchema(BaseSchema):
    """Configuration schema for Tongyi Z-Image text-to-image generation.

    Configures the checkpoint variant (``model_name``), prompt conditioning
    (``negative_prompt``), denoising schedule (``num_inference_steps``),
    classifier-free guidance strength (``guidance_scale``), output dimensions
    (``width``, ``height``), reproducibility (``seed``), hardware target
    (``device``), and batch size (``num_images_per_prompt``) for
    ``TongyiZImageModel``.
    """

    model_name: schema_field(
        enum_field(enum=["Tongyi-MAI/Z-Image", "Tongyi-MAI/Z-Image-Turbo"]),
        placeholder="Tongyi-MAI/Z-Image",
        description=MultilingualString(
            en=(
                "The Tongyi Z-Image checkpoint to load. "
                "'Tongyi-Z-Image' is Alibaba's 6B-parameter text-to-image model "
                "using a unique S3-DiT (Sparse Spatial-Spectral Diffusion Transformer) "
                "architecture, one of the most downloaded models on "
                "Hugging Face. It outperforms previous open-source state-of-the-art "
                "models at a fraction of their parameter count."
            ),
            es=(
                "El checkpoint Tongyi Z-Image a cargar. "
                "'Tongyi-Z-Image' es el modelo de texto a imagen de 6B parámetros de "
                "Alibaba que usa una arquitectura S3-DiT única (Sparse "
                "Spatial-Spectral Diffusion Transformer), uno de los "
                "más descargados en "
                "Hugging Face. Supera a modelos de última generación anteriores con "
                "una fracción de su cantidad de parámetros."
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
        placeholder=20,
        description=MultilingualString(
            en=(
                "Number of denoising steps. Tongyi Z-Image achieves high-quality "
                "results with 20-30 steps. More steps refine detail at the cost "
                "of generation time."
            ),
            es=(
                "Número de pasos de eliminación de ruido. Tongyi Z-Image logra "
                "resultados de alta calidad con 20-30 pasos. Más pasos refinan "
                "el detalle a costa de tiempo de generación."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps", es="Número de pasos de inferencia"
        ),
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=5.0,
        description=MultilingualString(
            en=(
                "Classifier-Free Guidance (CFG) scale. Controls how strictly the "
                "image follows the text prompt. Values 4-7 work well for "
                "Tongyi Z-Image."
            ),
            es=(
                "Escala de Classifier-Free Guidance (CFG). Controla qué tan "
                "estrictamente la imagen sigue el prompt. Valores 4-7 funcionan "
                "bien para Tongyi Z-Image."
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
                "this 6B-parameter model. CPU inference is possible but very slow."
            ),
            es=(
                "Dispositivo de hardware para inferencia. Se recomienda GPU para "
                "este modelo de 6B parámetros. La inferencia en CPU es posible "
                "pero muy lenta."
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
                "always produces the same image. Use -1 for a random seed."
            ),
            es=(
                "Semilla aleatoria para generación reproducible. Un entero positivo "
                "fijo siempre produce la misma imagen. Use -1 para semilla aleatoria."
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
                "Tongyi Z-Image natively targets 1024x1024 px."
            ),
            es=(
                "Ancho de la imagen en píxeles. Debe ser múltiplo de 8. "
                "Tongyi Z-Image apunta nativamente a 1024x1024 px."
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
                "Tongyi Z-Image natively targets 1024x1024 px."
            ),
            es=(
                "Altura de la imagen en píxeles. Debe ser múltiplo de 8. "
                "Tongyi Z-Image apunta nativamente a 1024x1024 px."
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
                "Requires proportionally more GPU memory per additional image."
            ),
            es=(
                "Cuántas imágenes generar desde un solo prompt en un lote. "
                "Requiere proporcionalmente más memoria GPU por imagen adicional."
            ),
        ),
        alias=MultilingualString(
            en="Num images per prompt", es="Número de imágenes por prompt"
        ),
    )  # type: ignore


class TongyiZImageModel(TextToImageGenerationTaskModel):
    """Tongyi Z-Image S3-DiT model for high-quality text-to-image generation.

    Wraps Alibaba's 6B-parameter Tongyi Z-Image pipeline. The model uses a
    novel Sparse Spatial-Spectral Diffusion Transformer (S3-DiT) architecture
    that processes image tokens in both spatial and spectral domains for
    efficient high-fidelity generation. It outperforms previous open-source
    state-of-the-art models while being more parameter-efficient, and excels
    at photorealism, diverse artistic styles, and accurate text rendering.

    References
    ----------
    .. [1] https://huggingface.co/Tongyi-MAI/Z-Image
    """

    SCHEMA = TongyiZImageSchema
    COLOR: str = "#e65100"
    DISPLAY_NAME: str = MultilingualString(
        en="Tongyi Z-Image",
        es="Tongyi Z-Image",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Tongyi Z-Image is Alibaba's 6B-parameter text-to-image model using a "
            "novel S3-DiT (Sparse Spatial-Spectral Diffusion Transformer) "
            "architecture. It is currently one of the most downloaded models on "
            "Hugging Face and "
            "outperforms previous open-source state-of-the-art models at a fraction "
            "of their size. Excels at photorealistic image generation, diverse styles, "
            "and accurate text rendering. Model available at "
            "https://huggingface.co/Tongyi-AI/Tongyi-Z-Image."
        ),
        es=(
            "Tongyi Z-Image es el modelo de texto a imagen de 6B parámetros de "
            "Alibaba que utiliza una novedosa arquitectura S3-DiT (Sparse "
            "Spatial-Spectral Diffusion Transformer). Es actualmente uno de los "
            "modelos más descargados en Hugging Face y supera a modelos de última "
            "generación anteriores con una fracción de su tamaño. Destaca en "
            "generación fotorrealista, estilos diversos y renderizado preciso de "
            "texto. Modelo disponible en "
            "https://huggingface.co/Tongyi-AI/Tongyi-Z-Image."
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

        self.model = DiffusionPipeline.from_pretrained(
            kwargs.get("model_name"),
            torch_dtype=torch.float16 if use_gpu else torch.float32,
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

        output = self.model(
            prompt=input,
            negative_prompt=self.negative_prompt,
            num_inference_steps=self.num_inference_steps,
            guidance_scale=self.guidance_scale,
            width=self.width,
            height=self.height,
            generator=generator,
            num_images_per_prompt=self.num_images_per_prompt,
        )
        return output.images
