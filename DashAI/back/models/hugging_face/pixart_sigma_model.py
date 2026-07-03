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
from DashAI.back.dependencies.downloads.downloadable import (
    HFPretrainedDownloadMixin,
)
from DashAI.back.models.text_to_image_generation_model import (
    TextToImageGenerationTaskModel,
)
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


class PixArtSigmaSchema(BaseSchema):
    """Configuration schema for PixArt-Sigma text-to-image generation.

    Configures the checkpoint variant (``model_name``), prompt conditioning
    (``negative_prompt``), denoising schedule (``num_inference_steps``),
    classifier free guidance strength (``guidance_scale``), output dimensions
    (``width``, ``height``), reproducibility (``seed``), hardware target
    (``device``), and batch size (``num_images_per_prompt``) for
    ``PixArtSigmaModel``.
    """

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
                de=(
                    "Text, der beschreibt, was aus dem generierten Bild ausgeschlossen "
                    "werden soll. Häufige Werte: 'unscharf, geringe Qualität, verzerrt,"
                    "Wasserzeichen'. Leer lassen, um die negative Konditionierung zu "
                    "überspringen."
                ),
                zh=(
                    "描述要从生成图像中排除的内容的文本。"
                    "常用值：'模糊、低质量、失真、水印'。"
                    "留空以跳过负向条件引导。"
                ),
            ),
            alias=MultilingualString(
                en="Negative prompt",
                es="Prompt negativo",
                pt="Prompt negativo",
                de="Negativer Prompt",
                zh="负向提示词",
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
            de=(
                "Anzahl der Entrauschungsschritte. PixArt-Sigma erreicht dank seiner "
                "effizienten Transformer-Architektur mit 14-25 Schritten gute Qualität."
                "Mehr Schritte verfeinern Details, erhöhen aber die Generierungszeit."
            ),
            zh=(
                "去噪步数。PixArt-Sigma 凭借其高效的 Transformer 架构，"
                "使用 14-25 步即可获得良好质量。"
                "步数越多，细节越精细，但生成时间也会增加。"
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps",
            es="Número de pasos de inferencia",
            pt="Número de etapas de inferência",
            de="Anzahl Inferenzschritte",
            zh="推理步数",
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
            de=(
                "Classifier-Free Guidance (CFG)-Skala. PixArt-Sigma funktioniert "
                "am besten mit niedrigeren Werten (3,5-5,5) im Vergleich zu "
                "U-Net-Modellen. "
                "Höhere Werte erzwingen den Prompt stärker, können aber Farben "
                "übersättigen. "
                "Der Standardwert 4,5 wird empfohlen."
            ),
            zh=(
                "无分类器引导（CFG）缩放值。与 U-Net 模型相比，PixArt-Sigma "
                "在较低值（3.5-5.5）下效果最佳。"
                "较高的值会更严格地执行提示词，但可能导致颜色过饱和。"
                "推荐使用默认值 4.5。"
            ),
        ),
        alias=MultilingualString(
            en="Guidance scale",
            es="Escala de guía",
            pt="Escala de orientação",
            de="Führungsskala",
            zh="引导缩放值",
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
            de=(
                "Hardware-Gerät für die Inferenz. GPU wird dringend empfohlen. "
                "PixArt-Sigma verwendet eine DiT (Diffusion Transformer)-Architektur "
                "mit T5-Textkodierung, die auf GPU schneller als U-Net ist."
            ),
            zh=(
                "推理所用硬件设备。强烈推荐使用 GPU。"
                "PixArt-Sigma 采用 DiT（扩散 Transformer）架构"
                "和 T5 文本编码，在 GPU 上比 U-Net 更快。"
            ),
        ),
        alias=MultilingualString(
            en="Device", es="Dispositivo", pt="Dispositivo", de="Gerät", zh="设备"
        ),
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
            de=(
                "Zufalls-Seed für reproduzierbare Generierung. Ein fester positiver "
                "Integer erzeugt stets dasselbe Bild. Verwenden Sie -1 für einen "
                "zufälligen Seed."
            ),
            zh=(
                "用于可复现生成的随机种子。"
                "固定的正整数始终生成相同的图像。使用 -1 表示随机种子。"
            ),
        ),
        alias=MultilingualString(
            en="Seed", es="Semilla", pt="Semente", de="Seed", zh="随机种子"
        ),
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
            de=(
                "Breite des Ausgabebildes in Pixeln. Muss ein Vielfaches von 8 sein. "
                "PixArt-Sigma unterstützt flexible Auflösungen bis zu 2048px."
            ),
            zh=(
                "输出图像的宽度（像素）。必须是 8 的倍数。"
                "PixArt-Sigma 支持最高 2048px 的灵活分辨率。"
            ),
        ),
        alias=MultilingualString(
            en="Width", es="Ancho", pt="Largura", de="Breite", zh="宽度"
        ),
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
            de=(
                "Höhe des Ausgabebildes in Pixeln. Muss ein Vielfaches von 8 sein. "
                "PixArt-Sigma unterstützt flexible Auflösungen bis zu 2048px."
            ),
            zh=(
                "输出图像的高度（像素）。必须是 8 的倍数。"
                "PixArt-Sigma 支持最高 2048px 的灵活分辨率。"
            ),
        ),
        alias=MultilingualString(
            en="Height", es="Altura", pt="Altura", de="Höhe", zh="高度"
        ),
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
            de=(
                "Wie viele Bilder aus einem einzelnen Prompt in einem Stapel generiert "
                "werden sollen. Erfordert proportional mehr GPU-Speicher pro "
                "zusätzlichem Bild."
            ),
            zh=(
                "单批次从一个提示词生成的图像数量。"
                "每增加一张图像，GPU 显存需求成比例增加。"
            ),
        ),
        alias=MultilingualString(
            en="Num images per prompt",
            es="Número de imágenes por prompt",
            pt="Número de imagens por prompt",
            de="Bilder pro Prompt",
            zh="每提示词图像数",
        ),
    )  # type: ignore


class PixArtSigmaGenerationModel(
    HFPretrainedDownloadMixin, TextToImageGenerationTaskModel
):
    """Diffusion Transformer model for high efficiency text-to-image generation.

    Wraps the PixArt-Sigma pipeline, which replaces the U-Net backbone used
    in Stable Diffusion with a scalable Diffusion Transformer (DiT)
    architecture. Text conditioning is provided by a T5-XXL encoder,
    enabling richer semantic understanding than CLIP-based models.

    PixArt-Sigma achieves state of the art image quality with 14-25 denoising
    steps (compared to 20-50 for comparable U-Net models) and supports
    flexible multiscale resolutions up to 2048 px. Two checkpoint sizes are
    available: 512 px (lighter) and 1024 px (best quality).

    References
    ----------
    - [1] Chen et al., "PixArt-Sigma: Weak-to-Strong Training of Diffusion
           Transformer for 4K Text-to-Image Generation", 2024.
           https://arxiv.org/abs/2403.04692
    - [2] https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS
    """

    SCHEMA = PixArtSigmaSchema
    MODEL_NAME: str = ""
    COLOR: str = "#6a1b9a"
    DISPLAY_NAME: str = MultilingualString(
        en="PixArt-Sigma",
        es="PixArt-Sigma",
        pt="PixArt-Sigma",
        de="PixArt-Sigma",
        zh="PixArt-Sigma",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "PixArt-Sigma is a high efficiency Diffusion Transformer (DiT) model for "
            "text-to-image generation, developed by the PixArt team. It uses a T5 "
            "text encoder for rich semantic understanding and achieves "
            "state of the art image quality with fewer inference steps than "
            "U-Net models. Supports "
            "flexible multiscale resolutions up to 2048px. Available in 512px and "
            "1024px variants. Significantly more parameter efficient than comparable "
            "models. Models at "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS and "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS."
        ),
        es=(
            "PixArt-Sigma es un modelo Diffusion Transformer (DiT) de alta eficiencia "
            "para generación de imágenes a partir de texto, desarrollado por el equipo "
            "PixArt. Usa un codificador de texto T5 para rica comprensión semántica y "
            "logra calidad de imagen de última generación con menos pasos de "
            "inferencia que los modelos U-Net. Soporta resoluciones multiescala "
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
            "inferência do que modelos U-Net. Suporta resoluções multiescala "
            "flexíveis até "
            "2048px. Disponível nas variantes de 512px e 1024px. "
            "Significativamente mais eficiente em parâmetros do que modelos "
            "comparáveis. Modelos em "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS e "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS."
        ),
        de=(
            "PixArt-Sigma ist ein hocheffizienter Diffusion Transformer (DiT) für "
            "Text-zu-Bild-Generierung, entwickelt vom PixArt-Team. Es verwendet einen "
            "T5-Textcodierer für reiches semantisches Verständnis und erreicht "
            "Bildqualität auf neuestem Stand mit weniger Inferenzschritten als "
            "U-Net-Modelle. Unterstützt flexible Multi-Skalen-Auflösungen bis 2048px. "
            "Verfügbar in den Varianten 512px und 1024px. Deutlich parametereffizienter"
            "als vergleichbare Modelle. Modelle unter "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS und "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS."
        ),
        zh=(
            "PixArt-Sigma 是 PixArt 团队开发的高效"
            "扩散 Transformer（DiT）文本到图像生成模型，"
            "使用 T5 文本编码器实现丰富的语义理解，支持最高 2048px 的多分辨率，"
            "提供 512px 和 1024px 两种规格。"
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
        self._pretrained_source(None)

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


class PixArtSigma1024(PixArtSigmaGenerationModel):
    """PixArt-Sigma XL 1024px checkpoint.

    Downloads its checkpoint into the component's own download folder.
    """

    MODEL_NAME: str = "PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
    DOWNLOAD_SIZE_BYTES: int = 2500000000
    DISPLAY_NAME = MultilingualString(
        en="PixArt-Sigma 1024",
        es="PixArt-Sigma 1024",
        pt="PixArt-Sigma 1024",
        de="PixArt-Sigma 1024",
        zh="PixArt-Sigma 1024",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "PixArt-Sigma XL by PixArt-alpha, a diffusion transformer (DiT) "
            "text-to-image model that reaches quality comparable to larger diffusion "
            "models with far fewer parameters. This checkpoint generates at "
            "1024x1024 px. Weights are downloaded into the component's own folder. "
            "Model page: https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-M"
            "S"
        ),
        es=(
            "PixArt-Sigma XL de PixArt-alpha, un modelo de texto a imagen basado en "
            "transformer de difusión (DiT) que alcanza una calidad comparable a "
            "modelos de difusión más grandes con muchos menos parámetros. Este "
            "checkpoint genera a 1024x1024 px. Los pesos se descargan en la carpeta "
            "propia del componente. Página del modelo: "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
        ),
        pt=(
            "PixArt-Sigma XL de PixArt-alpha, um modelo de texto para imagem baseado "
            "em transformer de difusão (DiT) que atinge qualidade comparável a "
            "modelos de difusão maiores com muito menos parâmetros. Este "
            "checkpoint gera a 1024x1024 px. Os pesos são baixados na pasta "
            "própria do componente. Página do modelo: "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
        ),
        de=(
            "PixArt-Sigma XL von PixArt-alpha, ein Text-zu-Bild-Modell auf Basis "
            "eines Diffusion-Transformers (DiT), das mit weit weniger Parametern "
            "eine Qualität vergleichbar mit größeren Diffusionsmodellen erreicht. "
            "Dieser Checkpoint erzeugt Bilder mit 1024x1024 px. Die Gewichte werden "
            "in den eigenen Ordner der Komponente heruntergeladen. Modellseite: "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
        ),
        zh=(
            "PixArt-alpha 推出的 PixArt-Sigma XL，是一种基于扩散 "
            "Transformer（DiT）的文本到图像模型，以远更少的参数量达到可媲美更大扩散模"
            "型的质量。该检查点以 1024x1024 "
            "像素生成。权重会下载到该组件自己的文件夹中。 模型页面： "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS"
        ),
    )


class PixArtSigma512(PixArtSigmaGenerationModel):
    """PixArt-Sigma XL 512px checkpoint (faster).

    Downloads its checkpoint into the component's own download folder.
    """

    MODEL_NAME: str = "PixArt-alpha/PixArt-Sigma-XL-2-512-MS"
    DOWNLOAD_SIZE_BYTES: int = 2500000000
    DISPLAY_NAME = MultilingualString(
        en="PixArt-Sigma 512",
        es="PixArt-Sigma 512",
        pt="PixArt-Sigma 512",
        de="PixArt-Sigma 512",
        zh="PixArt-Sigma 512",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "PixArt-Sigma XL by PixArt-alpha at 512x512 px, a diffusion transformer "
            "(DiT) text-to-image model. The lower resolution makes it faster and "
            "lighter than the 1024 px variant. Weights are downloaded into the "
            "component's own folder. Model page: https://huggingface.co/PixArt-alpha/"
            "PixArt-Sigma-XL-2-512-MS"
        ),
        es=(
            "PixArt-Sigma XL de PixArt-alpha a 512x512 px, un modelo de texto a "
            "imagen basado en transformer de difusión (DiT). La menor resolución "
            "lo hace más rápido y ligero que la variante de 1024 px. Los pesos se "
            "descargan en la carpeta propia del componente. Página del modelo: "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS"
        ),
        pt=(
            "PixArt-Sigma XL de PixArt-alpha a 512x512 px, um modelo de texto para "
            "imagem baseado em transformer de difusão (DiT). A menor resolução o "
            "torna mais rápido e leve que a variante de 1024 px. Os pesos são "
            "baixados na pasta própria do componente. Página do modelo: "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS"
        ),
        de=(
            "PixArt-Sigma XL von PixArt-alpha bei 512x512 px, ein "
            "Text-zu-Bild-Modell auf Basis eines Diffusion-Transformers (DiT). Die "
            "geringere Auflösung macht es schneller und leichter als die "
            "1024-px-Variante. Die Gewichte werden in den eigenen Ordner der "
            "Komponente heruntergeladen. Modellseite: "
            "https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS"
        ),
        zh=(
            "PixArt-alpha 推出的 PixArt-Sigma XL，分辨率为 512x512 "
            "像素，是一种基于扩散 Transformer（DiT）的文本到图像模型。较低的分辨率使"
            "其比 1024 像素变体更快、更轻量。权重会下载到该组件自己的文件夹中。 "
            "模型页面： https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-512-MS"
        ),
    )
