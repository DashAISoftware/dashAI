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
    """Configuration schema for SDXL Turbo text-to-image generation.

    Configures the prompt conditioning (``negative_prompt``), number of
    denoising steps (``num_inference_steps``; 1-4 is optimal for this
    distilled model), output dimensions (``width``, ``height``),
    reproducibility (``seed``), hardware target (``device``), and batch size
    (``num_images_per_prompt``) for ``SDXLTurboModel``.

    Note: ``guidance_scale`` is not exposed because SDXL Turbo always runs
    with ``guidance_scale=0`` due to its Adversarial Diffusion Distillation
    (ADD) training.
    """

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
                pt=(
                    "Texto descrevendo o que excluir da imagem gerada. "
                    "Nota: SDXL Turbo usa treinamento por destilação e "
                    "guidance_scale=0, portanto os prompts negativos têm "
                    "efeito mínimo. "
                    "Deixe vazio para melhores resultados."
                ),
            ),
            alias=MultilingualString(
                en="Negative prompt", es="Prompt negativo", pt="Prompt negativo"
            ),
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
            pt=(
                "Número de etapas de inferência. SDXL Turbo é um modelo destilado "
                "que gera imagens de alta qualidade em apenas 1-4 etapas. Usar "
                "1 etapa é o mais rápido; 2-4 etapas melhoram ligeiramente a "
                "qualidade. Valores acima de 4 têm retornos decrescentes para "
                "este modelo."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps",
            es="Número de pasos de inferencia",
            pt="Número de etapas de inferência",
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
            pt=(
                "Dispositivo de hardware para inferência. SDXL Turbo é rápido o "
                "suficiente para que a inferência em CPU seja viável (30-60 segundos "
                "por imagem). GPU ainda é recomendada para geração em tempo real "
                "ou em lote."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo", pt="Dispositivo"),
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
            pt=(
                "Semente aleatória para geração reproduzível. Um inteiro positivo "
                "fixo sempre produzirá a mesma imagem com configurações idênticas. "
                "Use um valor negativo (ex.: -1) para uma semente aleatória a "
                "cada execução."
            ),
        ),
        alias=MultilingualString(en="Seed", es="Semilla", pt="Semente"),
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
            pt=(
                "Largura da imagem de saída em pixels. Deve ser múltiplo de 8. "
                "A resolução ideal do SDXL Turbo é 512x512 px. Resoluções maiores "
                "podem reduzir a qualidade, pois o modelo foi treinado a 512 px."
            ),
        ),
        alias=MultilingualString(en="Width", es="Ancho", pt="Largura"),
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
            pt=(
                "Altura da imagem de saída em pixels. Deve ser múltiplo de 8. "
                "A resolução ideal do SDXL Turbo é 512x512 px."
            ),
        ),
        alias=MultilingualString(en="Height", es="Altura", pt="Altura"),
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
            pt=(
                "Quantas imagens gerar a partir de um único prompt em um lote. "
                "Como o SDXL Turbo é rápido, gerar múltiplas imagens por prompt "
                "é muito eficiente."
            ),
        ),
        alias=MultilingualString(
            en="Num images per prompt",
            es="Número de imágenes por prompt",
            pt="Número de imagens por prompt",
        ),
    )  # type: ignore


class SDXLTurboModel(TextToImageGenerationTaskModel):
    """Distilled SDXL model for near-real-time text-to-image generation.

    Wraps ``stabilityai/sdxl-turbo``, a version of Stable Diffusion XL
    trained with Adversarial Diffusion Distillation (ADD) by Stability AI.
    ADD transfers knowledge from a large teacher model into a student that
    can produce photorealistic 512 px images in as few as one denoising step,
    up to 30x faster than standard SDXL.

    Because ADD bakes guidance directly into the model weights, classifier-free
    guidance is disabled (``guidance_scale=0`` is enforced internally) and
    negative prompts have minimal effect.

    Ideal for interactive and real-time applications where latency matters
    more than absolute peak quality.

    References
    ----------
    - [1] Sauer et al., "Adversarial Diffusion Distillation", 2023.
           https://arxiv.org/abs/2311.17042
    - [2] https://huggingface.co/stabilityai/sdxl-turbo
    """

    SCHEMA = SDXLTurboSchema
    COLOR: str = "#b71c1c"
    DISPLAY_NAME: str = MultilingualString(
        en="SDXL Turbo",
        es="SDXL Turbo",
        pt="SDXL Turbo",
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
        pt=(
            "SDXL Turbo é uma versão destilada do Stable Diffusion XL pela "
            "Stability AI que gera imagens de alta qualidade em uma única etapa "
            "de remoção de ruído "
            "usando Destilação por Difusão Adversarial (ADD). Produz imagens "
            "fotorrealistas a 512x512 px até 30x mais rápido que o SDXL padrão. "
            "Ideal para aplicações interativas e em tempo real. Nota: não usa "
            "orientação livre de classificador (guidance_scale=0 internamente). "
            "Modelo disponível em "
            "https://huggingface.co/stabilityai/sdxl-turbo."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise the SDXL Turbo pipeline.

        Downloads ``stabilityai/sdxl-turbo`` from HuggingFace Hub via
        ``AutoPipelineForText2Image.from_pretrained`` and moves the pipeline
        to the requested device.  When a GPU is available, the ``fp16``
        variant is loaded to halve memory usage; CPU inference uses
        ``float32``.

        Parameters
        ----------
        **kwargs : dict
            negative_prompt : str or None, optional
                Text describing content to suppress.  Has minimal effect
                because SDXL Turbo uses ADD training with ``guidance_scale=0``.
            num_inference_steps : int, optional
                Number of denoising steps (1-4 recommended).  Defaults to
                ``1``.  Values above 4 provide diminishing returns.
            device : str
                Target device string from ``DEVICE_ENUM``.  Mapped to a
                ``cuda:<index>`` string or ``"cpu"`` via ``DEVICE_TO_IDX``.
            seed : int
                Fixed seed for reproducible outputs.  Values ≤ 0 disable
                seeding.
            width : int
                Output image width in pixels (multiple of 8).  Optimal is
                512 px.
            height : int
                Output image height in pixels (multiple of 8).  Optimal is
                512 px.
            num_images_per_prompt : int
                Number of images to generate per prompt call.
        """
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
