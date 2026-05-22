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


class PixArtSigmaSchema(BaseSchema):
    """Configuration schema for PixArt-Sigma text-to-image generation.

    Configures the checkpoint variant (``model_name``), prompt conditioning
    (``negative_prompt``), denoising schedule (``num_inference_steps``),
    classifier-free guidance strength (``guidance_scale``), output dimensions
    (``width``, ``height``), reproducibility (``seed``), hardware target
    (``device``), and batch size (``num_images_per_prompt``) for
    ``PixArtSigmaModel``.
    """

    model_name: schema_field(
        enum_field(
            enum=[
                "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS",
                "PixArt-alpha/PixArt-Sigma-XL-2-512-MS",
            ]
        ),
        placeholder="PixArt-alpha/PixArt-Sigma-XL-2-1024-MS",
        description=MultilingualString(
            en=(
                "The PixArt-Sigma checkpoint to load. "
                "'PixArt-Sigma-XL-2-1024-MS' is the high-resolution variant "
                "trained at 1024px with multi-scale support, delivering the best "
                "image quality. "
                "'PixArt-Sigma-XL-2-512-MS' is the 512px variant, faster and lighter "
                "while still producing sharp results."
            ),
            es=(
                "El checkpoint PixArt-Sigma a cargar. "
                "'PixArt-Sigma-XL-2-1024-MS' es la variante de alta resolución "
                "entrenada a 1024px con soporte multi-escala, entregando la mejor "
                "calidad de imagen. "
                "'PixArt-Sigma-XL-2-512-MS' es la variante de 512px, más rápida y "
                "ligera manteniendo resultados nítidos."
            ),
            pt=(
                "O checkpoint PixArt-Sigma a carregar. "
                "'PixArt-Sigma-XL-2-1024-MS' é a variante de alta resolução "
                "treinada a 1024px com suporte multi-escala, entregando a melhor "
                "qualidade de imagem. "
                "'PixArt-Sigma-XL-2-512-MS' é a variante de 512px, mais rápida e "
                "leve, mantendo resultados nítidos."
            ),
        ),
        alias=MultilingualString(
            en="Model name", es="Nombre del modelo", pt="Nome do modelo"
        ),
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
                pt=(
                    "Texto descrevendo o que excluir da imagem gerada. "
                    "Valores comuns: 'borrado, baixa qualidade, distorcido, "
                    "marca d'água'. "
                    "Deixe vazio para omitir o condicionamento negativo."
                ),
            ),
            alias=MultilingualString(
                en="Negative prompt", es="Prompt negativo", pt="Prompt negativo"
            ),
        )  # type: ignore
    ]

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=20,
        description=MultilingualString(
            en=(
                "Number of denoising steps. PixArt-Sigma achieves good quality with "
                "14-25 steps due to its efficient transformer architecture. "
                "More steps refine details but increase generation time."
            ),
            es=(
                "Número de pasos de eliminación de ruido. PixArt-Sigma logra buena "
                "calidad con 14-25 pasos gracias a su eficiente arquitectura "
                "transformer. Más pasos refinan detalles pero aumentan el tiempo."
            ),
            pt=(
                "Número de etapas de inferência. PixArt-Sigma atinge boa qualidade "
                "com 14-25 etapas graças à sua eficiente arquitetura transformer. "
                "Mais etapas refinam detalhes, mas aumentam o tempo de geração."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps",
            es="Número de pasos de inferencia",
            pt="Número de etapas de inferência",
        ),
    )  # type: ignore

    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=4.5,
        description=MultilingualString(
            en=(
                "Classifier-Free Guidance (CFG) scale. PixArt-Sigma works best "
                "with lower values (3.5-5.5) compared to U-Net models. "
                "Higher values enforce the prompt more strictly but may saturate "
                "colors. The default of 4.5 is recommended."
            ),
            es=(
                "Escala de Classifier-Free Guidance (CFG). PixArt-Sigma funciona "
                "mejor con valores más bajos (3.5-5.5) comparado con modelos U-Net. "
                "Valores más altos refuerzan el prompt pero pueden saturar colores. "
                "El valor por defecto de 4.5 es recomendado."
            ),
            pt=(
                "Escala de Classifier-Free Guidance (CFG). PixArt-Sigma funciona "
                "melhor com valores mais baixos (3.5-5.5) em comparação com modelos "
                "U-Net. Valores mais altos reforçam o prompt, mas podem saturar as "
                "cores. O valor padrão de 4.5 é recomendado."
            ),
        ),
        alias=MultilingualString(
            en="Guidance scale", es="Escala de guía", pt="Escala de orientação"
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware device for inference. GPU is strongly recommended. "
                "PixArt-Sigma uses a DiT (Diffusion Transformer) architecture "
                "with T5 text encoding, which is faster than U-Net on GPU."
            ),
            es=(
                "Dispositivo de hardware para inferencia. Se recomienda GPU. "
                "PixArt-Sigma usa una arquitectura DiT (Diffusion Transformer) "
                "con codificación de texto T5, más rápida que U-Net en GPU."
            ),
            pt=(
                "Dispositivo de hardware para inferência. GPU é fortemente "
                "recomendada. PixArt-Sigma usa uma arquitetura DiT (Diffusion "
                "Transformer) com codificação de texto T5, mais rápida que U-Net "
                "na GPU."
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
                "always produces the same image. Use -1 for a random seed."
            ),
            es=(
                "Semilla aleatoria para generación reproducible. Un entero positivo "
                "fijo siempre produce la misma imagen. Use -1 para semilla aleatoria."
            ),
            pt=(
                "Semente aleatória para geração reproduzível. Um inteiro positivo "
                "fixo sempre produz a mesma imagem. Use -1 para uma semente aleatória."
            ),
        ),
        alias=MultilingualString(en="Seed", es="Semilla", pt="Semente"),
    )  # type: ignore

    width: schema_field(
        int_field(ge=64, le=2048),
        placeholder=1024,
        description=MultilingualString(
            en=(
                "Width of the output image in pixels. Must be a multiple of 8. "
                "PixArt-Sigma supports flexible resolutions up to 2048px."
            ),
            es=(
                "Ancho de la imagen en píxeles. Debe ser múltiplo de 8. "
                "PixArt-Sigma soporta resoluciones flexibles hasta 2048px."
            ),
            pt=(
                "Largura da imagem em pixels. Deve ser múltiplo de 8. "
                "PixArt-Sigma suporta resoluções flexíveis até 2048px."
            ),
        ),
        alias=MultilingualString(en="Width", es="Ancho", pt="Largura"),
    )  # type: ignore

    height: schema_field(
        int_field(ge=64, le=2048),
        placeholder=1024,
        description=MultilingualString(
            en=(
                "Height of the output image in pixels. Must be a multiple of 8. "
                "PixArt-Sigma supports flexible resolutions up to 2048px."
            ),
            es=(
                "Altura de la imagen en píxeles. Debe ser múltiplo de 8. "
                "PixArt-Sigma soporta resoluciones flexibles hasta 2048px."
            ),
            pt=(
                "Altura da imagem em pixels. Deve ser múltiplo de 8. "
                "PixArt-Sigma suporta resoluções flexíveis até 2048px."
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
                "Requires proportionally more GPU memory per additional image."
            ),
            es=(
                "Cuántas imágenes generar desde un solo prompt en un lote. "
                "Requiere proporcionalmente más memoria GPU por imagen adicional."
            ),
            pt=(
                "Quantas imagens gerar a partir de um único prompt em um lote. "
                "Requer proporcionalmente mais memória GPU por imagem adicional."
            ),
        ),
        alias=MultilingualString(
            en="Num images per prompt",
            es="Número de imágenes por prompt",
            pt="Número de imagens por prompt",
        ),
    )  # type: ignore


class PixArtSigmaModel(TextToImageGenerationTaskModel):
    """Diffusion Transformer model for high-efficiency text-to-image generation.

    Wraps the PixArt-Sigma pipeline, which replaces the U-Net backbone used
    in Stable Diffusion with a scalable Diffusion Transformer (DiT)
    architecture. Text conditioning is provided by a T5-XXL encoder,
    enabling richer semantic understanding than CLIP-based models.

    PixArt-Sigma achieves state-of-the-art image quality with 14-25 denoising
    steps (compared to 20-50 for comparable U-Net models) and supports
    flexible multi-scale resolutions up to 2048 px. Two checkpoint sizes are
    available: 512 px (lighter) and 1024 px (best quality).

    References
    ----------
    - [1] Chen et al., "PixArt-Sigma: Weak-to-Strong Training of Diffusion
           Transformer for 4K Text-to-Image Generation", 2024.
           https://arxiv.org/abs/2403.04692
    - [2] https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS
    """

    SCHEMA = PixArtSigmaSchema
    COLOR: str = "#6a1b9a"
    DISPLAY_NAME: str = MultilingualString(
        en="PixArt-Sigma",
        es="PixArt-Sigma",
        pt="PixArt-Sigma",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "PixArt-Sigma is a high-efficiency Diffusion Transformer (DiT) model for "
            "text-to-image generation, developed by the PixArt team. It uses a T5 "
            "text encoder for rich semantic understanding and achieves "
            "state-of-the-art image quality with fewer inference steps than "
            "U-Net models. Supports "
            "flexible multi-scale resolutions up to 2048px. Available in 512px and "
            "1024px variants. Significantly more parameter-efficient than comparable "
            "models. Models at "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS and "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS."
        ),
        es=(
            "PixArt-Sigma es un modelo Diffusion Transformer (DiT) de alta eficiencia "
            "para generación de imágenes a partir de texto, desarrollado por el equipo "
            "PixArt. Usa un codificador de texto T5 para rica comprensión semántica y "
            "logra calidad de imagen de última generación con menos pasos de "
            "inferencia que los modelos U-Net. Soporta resoluciones multi-escala "
            "flexibles hasta "
            "2048px. Disponible en variantes de 512px y 1024px. "
            "Significativamente más eficiente en parámetros que modelos comparables. "
            "Modelos en "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS y "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS."
        ),
        pt=(
            "PixArt-Sigma é um modelo Diffusion Transformer (DiT) de alta eficiência "
            "para geração de imagens a partir de texto, desenvolvido pela equipe "
            "PixArt. Usa um codificador de texto T5 para rica compreensão semântica e "
            "atinge qualidade de imagem de última geração com menos etapas de "
            "inferência do que modelos U-Net. Suporta resoluções multi-escala "
            "flexíveis até "
            "2048px. Disponível nas variantes de 512px e 1024px. "
            "Significativamente mais eficiente em parâmetros do que modelos "
            "comparáveis. Modelos em "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS e "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise the PixArt-Sigma pipeline.

        Downloads the selected checkpoint from HuggingFace Hub via
        ``PixArtSigmaPipeline.from_pretrained`` and moves the pipeline to
        the requested device.  When a GPU is available, weights are loaded
        in ``float16`` to halve memory consumption; CPU inference uses
        ``float32``.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace model ID.  Must be one of the two
                ``PixArt-alpha`` checkpoints defined in
                ``PixArtSigmaSchema``.
                Defaults to ``"PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"``.
            negative_prompt : str or None, optional
                Text describing content to suppress in the output image.
            num_inference_steps : int
                Number of denoising steps.  14-25 is sufficient for this
                model due to its efficient DiT architecture.
            guidance_scale : float
                Classifier-Free Guidance (CFG) scale.  PixArt-Sigma performs
                best with values in the 3.5-5.5 range.
            device : str
                Target device string from ``DEVICE_ENUM``.  Mapped to a
                ``cuda:<index>`` string or ``"cpu"`` via ``DEVICE_TO_IDX``.
            seed : int
                Fixed seed for reproducible outputs.  Values ≤ 0 disable
                seeding.
            width : int
                Output image width in pixels (multiple of 8).
            height : int
                Output image height in pixels (multiple of 8).
            num_images_per_prompt : int
                Number of images to generate per prompt call.
        """
        import torch
        from diffusers import PixArtSigmaPipeline

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )
        self.model_name = kwargs.get(
            "model_name", "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
        )

        self.model = PixArtSigmaPipeline.from_pretrained(
            self.model_name,
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
