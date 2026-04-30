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
    """Configuration schema for Stable Diffusion V3 text-to-image generation.

    Configures the checkpoint variant (``model_name``), HuggingFace access key
    (``huggingface_key``), prompt conditioning (``negative_prompt``),
    denoising schedule (``num_inference_steps``), prompt adherence
    (``guidance_scale``), output dimensions (``width``, ``height``),
    reproducibility (``seed``), hardware target (``device``), and batch size
    (``num_images_per_prompt``) for ``StableDiffusionV3Model``.
    """

    model_name: schema_field(
        enum_field(
            enum=[
                "stabilityai/stable-diffusion-3-medium-diffusers",
                "stabilityai/stable-diffusion-3.5-medium",
                "stabilityai/stable-diffusion-3.5-large",
                "stabilityai/stable-diffusion-3.5-large-turbo",
            ]
        ),
        placeholder="stabilityai/stable-diffusion-3-medium-diffusers",
        description=MultilingualString(
            en=(
                "The SD3/SD3.5 checkpoint to load. 'sd-3-medium' is the baseline "
                "2B-parameter model. 'sd-3.5-medium' improves quality at similar "
                "speed. 'sd-3.5-large' (8B) delivers the highest quality but needs "
                "more VRAM. 'sd-3.5-large-turbo' is a distilled large model that "
                "requires far fewer steps (4-8) for fast high-quality generation. "
                "All variants target 1024x1024 px natively."
            ),
            es=(
                "El checkpoint SD3/SD3.5 a cargar. 'sd-3-medium' es el modelo base "
                "de 2B parámetros. 'sd-3.5-medium' mejora la calidad a velocidad "
                "similar. 'sd-3.5-large' (8B) ofrece la mayor calidad pero necesita "
                "más VRAM. 'sd-3.5-large-turbo' es un modelo large destilado que "
                "requiere muchos menos pasos (4-8) para generación rápida de alta "
                "calidad. Todas las variantes apuntan a 1024x1024 px de forma nativa."
            ),
        ),
        alias=MultilingualString(en="Model name", es="Nombre del modelo"),
    )  # type: ignore

    huggingface_key: schema_field(
        string_field(),
        placeholder="",
        description=MultilingualString(
            en=(
                "Hugging Face read-access token required to download these gated "
                "models. To obtain one: accept the model license on "
                "huggingface.co/stabilityai, then go to Settings → Access Tokens "
                "and generate a token with 'Read' scope."
            ),
            es=(
                "Token de acceso de lectura de Hugging Face necesario para descargar "
                "estos modelos protegidos. Para obtenerlo: acepte la licencia del "
                "modelo en huggingface.co/stabilityai, luego vaya a "
                "Configuración → Tokens de Acceso y genere un token con alcance "
                "'Read'."
            ),
        ),
        alias=MultilingualString(en="Hugging Face key", es="Clave Hugging Face"),
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
        placeholder=15,
        description=MultilingualString(
            en=(
                "Number of denoising steps to run. More steps refine the image but "
                "increase generation time. Typical range: 20-40 for standard models; "
                "use only 4-8 steps with 'large-turbo'. Values above 50 rarely "
                "improve output for SD3/SD3.5."
            ),
            es=(
                "Número de pasos de eliminación de ruido a ejecutar. Más pasos "
                "refinan la imagen pero aumentan el tiempo de generación. Rango "
                "típico: 20-40 para modelos estándar; use solo 4-8 pasos con "
                "'large-turbo'. Valores superiores a 50 raramente mejoran el "
                "resultado en SD3/SD3.5."
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
                "image follows the text prompt. SD3.5 works well at 3.5-4.5. "
                "The 'large-turbo' variant is designed for guidance_scale=1 "
                "(no CFG). Higher values enforce the prompt but may introduce "
                "oversaturation or artifacts."
            ),
            es=(
                "Escala de Classifier-Free Guidance (CFG). Controla qué tan "
                "estrictamente la imagen sigue el prompt. SD3.5 funciona bien con "
                "3.5-4.5. La variante 'large-turbo' está diseñada para "
                "guidance_scale=1 (sin CFG). Valores más altos refuerzan el prompt "
                "pero pueden introducir sobresaturación o artefactos."
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
                "SD3/SD3.5 models are natively trained at 1024x1024 px; using "
                "that resolution yields the best quality."
            ),
            es=(
                "Ancho de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "Los modelos SD3/SD3.5 se entrenan de forma nativa a 1024x1024 px; "
                "usar esa resolución produce la mejor calidad."
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
                "SD3/SD3.5 models are natively trained at 1024x1024 px; using "
                "that resolution yields the best quality."
            ),
            es=(
                "Altura de la imagen de salida en píxeles. Debe ser múltiplo de 8. "
                "Los modelos SD3/SD3.5 se entrenan de forma nativa a 1024x1024 px; "
                "usar esa resolución produce la mejor calidad."
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


class StableDiffusionV3Model(TextToImageGenerationTaskModel):
    """Multimodal Diffusion Transformer model for high-quality text-to-image generation.

    Wraps the Stable Diffusion 3 and 3.5 family of checkpoints from
    Stability AI. These models use a Multimodal Diffusion Transformer (MMDiT)
    architecture that jointly processes text and image tokens, delivering
    significantly improved prompt adherence, typography, and overall image
    quality compared to U-Net-based predecessors.

    Four variants are supported: SD3 Medium (2B), SD3.5 Medium (2B, improved),
    SD3.5 Large (8B, best quality), and SD3.5 Large Turbo (distilled, 4-8
    steps). All produce images natively at 1024 x 1024 px. Access to these
    gated models requires a HuggingFace API key.

    References
    ----------
    - [1] Esser et al., "Scaling Rectified Flow Transformers for
           High-Resolution Image Synthesis", 2024.
           https://arxiv.org/abs/2403.03206
    - [2] https://huggingface.co/stabilityai/stable-diffusion-3-medium-diffusers
    """

    SCHEMA = StableDiffusionSchema
    COLOR: str = "#6a1b9a"
    TAGS: list = ["diffusers", "Stability AI"]
    DISPLAY_NAME: str = MultilingualString(
        en="Stable Diffusion V3",
        es="Stable Diffusion V3",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Stable Diffusion 3 and 3.5 are next-generation text-to-image models by "
            "Stability AI using a Multimodal Diffusion Transformer (MMDiT) "
            "architecture, offering improved prompt adherence, typography, and image "
            "quality over previous versions. Supports SD3 Medium, SD3.5 Medium, "
            "SD3.5 Large, and SD3.5 Large Turbo variants. A Hugging Face API key is "
            "required to access these gated models. Models are available at "
            "https://huggingface.co/stabilityai."
        ),
        es=(
            "Stable Diffusion 3 y 3.5 son modelos de texto a imagen de nueva "
            "generación de Stability AI que utilizan una arquitectura Multimodal "
            "Diffusion Transformer (MMDiT), ofreciendo mayor fidelidad al prompt, "
            "tipografía y calidad de imagen respecto a versiones anteriores. Soporta "
            "las variantes SD3 Medium, SD3.5 Medium, SD3.5 Large y SD3.5 Large "
            "Turbo. Se requiere una clave API de Hugging Face para acceder a estos "
            "modelos protegidos. Los modelos están disponibles en "
            "https://huggingface.co/stabilityai."
        ),
    )

    def __init__(self, **kwargs):
        """Initialize the model."""

        import torch
        from diffusers import DiffusionPipeline
        from huggingface_hub import login

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )
        self.model_name = kwargs.get(
            "model_name", "stabilityai/stable-diffusion-3-medium-diffusers"
        )
        self.huggingface_key = kwargs.get("huggingface_key")

        if self.huggingface_key:
            try:
                login(token=self.huggingface_key)
            except Exception as e:
                raise ValueError(
                    "Failed to login to Hugging Face. Please check your API key."
                ) from e

        try:
            self.model = DiffusionPipeline.from_pretrained(
                self.model_name,
            ).to(self.device)
        except Exception as e:
            raise ValueError(f"Failed to load model {self.model_name}. {e}") from e

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
