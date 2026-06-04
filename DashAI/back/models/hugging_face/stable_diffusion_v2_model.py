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
    """Configuration schema for Stable Diffusion V2 text-to-image generation.

    Configures the checkpoint variant (``model_name``), prompt conditioning
    (``negative_prompt``), denoising schedule (``num_inference_steps``),
    classifier-free guidance strength (``guidance_scale``), output dimensions
    (``width``, ``height``), reproducibility (``seed``), hardware target
    (``device``), and batch size (``num_images_per_prompt``) for
    ``StableDiffusionV2Model``.
    """

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
            pt=(
                "O checkpoint específico do Stable Diffusion 2.x a carregar. "
                "As variantes '-base' são treinadas a 512x512 px e são mais rápidas; "
                "as variantes sem '-base' visam 768x768 px "
                "e produzem maior detalhe. "
                "As variantes '2-1' são mais ajustadas "
                "e geralmente superam a '2'."
            ),
            de=(
                "Der zu ladende spezifische Stable Diffusion 2.x-Checkpoint. "
                "Die '-base'-Varianten werden bei 512x512 px trainiert und sind "
                "schneller; "
                "die Nicht-base-Varianten zielen auf 768x768 px ab "
                "und liefern schärfere Details. "
                "Die '2-1'-Varianten sind weiter feinabgestimmt "
                "und übertreffen '2' in der Regel."
            ),
        ),
        alias=MultilingualString(
            en="Model name",
            es="Nombre del modelo",
            pt="Nome do modelo",
            de="Modellname",
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
                    "marca de agua'. Dejar vacío para omitir "
                    "el condicionamiento negativo."
                ),
                pt=(
                    "Texto descrevendo o que excluir da imagem gerada. "
                    "Valores comuns: 'borrado, baixa qualidade, distorcido, "
                    "marca d'água'. Deixe vazio para omitir "
                    "o condicionamento negativo."
                ),
                de=(
                    "Text, der beschreibt, was aus dem generierten Bild ausgeschlossen "
                    "werden soll. Häufige Werte: 'unscharf, geringe Qualität, verzerrt,"
                    "Wasserzeichen'. Leer lassen, um die negative Konditionierung zu "
                    "überspringen."
                ),
            ),
            alias=MultilingualString(
                en="Negative prompt",
                es="Prompt negativo",
                pt="Prompt negativo",
                de="Negativer Prompt",
            ),
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
            pt=(
                "Número de passos de remoção de ruído a executar. Mais passos refinam "
                "a imagem mas aumentam o tempo de geração. Intervalo típico: 15-30 "
                "para resultados rápidos, 40-50 para maior qualidade. Valores acima "
                "de 100 raramente melhoram o resultado."
            ),
            de=(
                "Anzahl der auszuführenden Entrauschungsschritte. Mehr Schritte "
                "verfeinern "
                "das Bild, erhöhen aber die Generierungszeit. Typischer Bereich: 15-30 "
                "für schnelle Ergebnisse, 40-50 für höhere Qualität. Werte über 100 "
                "verbessern das Ergebnis selten."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps",
            es="Número de pasos de inferencia",
            pt="Número de passos de inferência",
            de="Anzahl Inferenzschritte",
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
            pt=(
                "Escala de Classifier-Free Guidance (CFG). Controla quão "
                "estritamente a imagem segue o prompt de texto. Valores baixos "
                "(1-4) permitem liberdade criativa; valores médios (5-9) equilibram "
                "qualidade e aderência; valores altos (10+) reforçam o prompt mas "
                "podem produzir artefatos."
            ),
            de=(
                "Classifier-Free Guidance (CFG)-Skala. Steuert, wie streng das Bild "
                "dem Textprompt folgt. Niedrige Werte (1-4) erlauben kreative Freiheit;"
                "mittlere Werte (5-9) balancieren Qualität und Treue; hohe Werte (10+) "
                "erzwingen den Prompt, können aber Artefakte erzeugen."
            ),
        ),
        alias=MultilingualString(
            en="Guidance scale",
            es="Escala de guía",
            pt="Escala de orientação",
            de="Führungsskala",
        ),
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
            pt=(
                "Dispositivo de hardware para inferência. Selecione uma opção de GPU "
                "para aceleração por hardware, altamente recomendado para modelos de "
                "difusão. Selecione 'CPU' em sistemas sem GPU compatível, mas espere "
                "tempos de geração significativamente mais longos."
            ),
            de=(
                "Hardware-Gerät für die Inferenz. Wählen Sie eine GPU-Option für "
                "Hardwarebeschleunigung, die für Diffusionsmodelle dringend empfohlen "
                "wird. Wählen Sie 'CPU' auf Systemen ohne kompatible GPU, aber erwarten"
                "Sie deutlich längere Generierungszeiten."
            ),
        ),
        alias=MultilingualString(
            en="Device", es="Dispositivo", pt="Dispositivo", de="Gerät"
        ),
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
            pt=(
                "Semente aleatória para geração reproduzível. Um inteiro positivo "
                "fixo sempre produzirá a mesma imagem com configurações idênticas. "
                "Use um valor negativo (ex. -1) para uma semente aleatória em cada "
                "execução."
            ),
            de=(
                "Zufalls-Seed für reproduzierbare Generierung. Ein fester positiver "
                "Integer erzeugt stets dasselbe Bild bei identischen Einstellungen. "
                "Verwenden Sie einen negativen Wert (z.B. -1) für einen zufälligen "
                "Seed bei jedem Durchlauf."
            ),
        ),
        alias=MultilingualString(en="Seed", es="Semilla", pt="Semente", de="Seed"),
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
            pt=(
                "Largura da imagem de saída em pixels. Deve ser múltiplo de 8. "
                "A resolução nativa é 512 para variantes '-base' e 768 para as "
                "demais. Usar a resolução nativa produz os melhores resultados."
            ),
            de=(
                "Breite des Ausgabebildes in Pixeln. Muss ein Vielfaches von 8 sein. "
                "Die native Auflösung beträgt 512 für '-base'-Varianten und 768 für "
                "andere. "
                "Die native Auflösung liefert die besten Qualitätsergebnisse."
            ),
        ),
        alias=MultilingualString(en="Width", es="Ancho", pt="Largura", de="Breite"),
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
            pt=(
                "Altura da imagem de saída em pixels. Deve ser múltiplo de 8. "
                "A resolução nativa é 512 para variantes '-base' e 768 para as "
                "demais. Usar a resolução nativa produz os melhores resultados."
            ),
            de=(
                "Höhe des Ausgabebildes in Pixeln. Muss ein Vielfaches von 8 sein. "
                "Die native Auflösung beträgt 512 für '-base'-Varianten und 768 für "
                "andere. "
                "Die native Auflösung liefert die besten Qualitätsergebnisse."
            ),
        ),
        alias=MultilingualString(en="Height", es="Altura", pt="Altura", de="Höhe"),
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
            pt=(
                "Quantas imagens gerar a partir de um único prompt em um lote. "
                "Aumentar este valor é mais eficiente do que executar várias sessões, "
                "mas requer proporcionalmente mais memória GPU."
            ),
            de=(
                "Wie viele Bilder aus einem einzelnen Prompt in einem Stapel generiert "
                "werden sollen. Diesen Wert zu erhöhen ist effizienter als mehrere "
                "Sitzungen zu starten, erfordert aber proportional mehr GPU-Speicher."
            ),
        ),
        alias=MultilingualString(
            en="Num images per prompt",
            es="Número de imágenes por prompt",
            pt="Número de imagens por prompt",
            de="Bilder pro Prompt",
        ),
    )  # type: ignore


class StableDiffusionV2Model(TextToImageGenerationTaskModel):
    """Latent diffusion model for high-resolution text-to-image generation.

    Wraps the Stable Diffusion 2.x family of checkpoints released by
    Stability AI. The pipeline uses a U-Net denoiser conditioned on OpenCLIP
    text embeddings (ViT-H/14) and a variational autoencoder (VAE) to
    iteratively denoise a latent representation into a high-resolution image.

    Four checkpoints are supported:

    * ``stable-diffusion-2`` / ``stable-diffusion-2-1`` — trained at 768 px,
      produce sharper detail; '2-1' is further fine-tuned and generally
      outperforms '2'.
    * ``stable-diffusion-2-base`` / ``stable-diffusion-2-1-base`` — trained at
      512 px, faster and lower memory; best for rapid prototyping.

    Models are served from the ``sd2-community`` HuggingFace organisation,
    a community mirror of the original Stability AI weights (deprecated at
    ``stabilityai``).

    References
    ----------
    - [1] Rombach et al., "High-Resolution Image Synthesis with Latent
           Diffusion Models", CVPR 2022. https://arxiv.org/abs/2112.10752
    - [2] https://huggingface.co/sd2-community
    """

    SCHEMA = StableDiffusionSchema
    COLOR: str = "#1565c0"
    DISPLAY_NAME: str = MultilingualString(
        en="Stable Diffusion V2",
        es="Stable Diffusion V2",
        pt="Stable Diffusion V2",
        de="Stable Diffusion V2",
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
        pt=(
            "Stable Diffusion 2.x é um modelo de difusão latente da Stability AI para "
            "geração de imagens de alta resolução a partir de texto. Utiliza um "
            "denoiser U-Net condicionado em embeddings de texto CLIP e um autoencoder "
            "variacional (VAE) para produzir imagens detalhadas. Suporta as variantes "
            "stable-diffusion-2, stable-diffusion-2-base, stable-diffusion-2-1 e "
            "stable-diffusion-2-1-base. Os modelos são servidos pela organização "
            "sd2-community (https://huggingface.co/sd2-community), um espelho "
            "comunitário dos pesos originais da Stability AI que foram depreciados e "
            "removidos de https://huggingface.co/stabilityai."
        ),
        de=(
            "Stable Diffusion 2.x ist ein latentes Diffusionsmodell von Stability AI "
            "zur hochauflösenden Text-zu-Bild-Generierung. Es verwendet einen U-Net-"
            "Entrauscher konditioniert auf CLIP-Texteinbettungen und einen "
            "variationalen "
            "Autoencoder (VAE) zur Erzeugung detaillierter Bilder. Unterstützt die "
            "Varianten stable-diffusion-2, stable-diffusion-2-base, "
            "stable-diffusion-2-1 "
            "und stable-diffusion-2-1-base. Modelle werden von der Organisation "
            "sd2-community (https://huggingface.co/sd2-community) bereitgestellt, einem"
            "Community-Spiegel der originalen Stability AI-Gewichte, die von "
            "https://huggingface.co/stabilityai veraltet und entfernt wurden."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise the Stable Diffusion V2 pipeline.

        Downloads the selected checkpoint from HuggingFace Hub via
        ``DiffusionPipeline.from_pretrained`` and moves the pipeline to the
        requested device.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace model ID to load.  Must be one of the four
                ``sd2-community`` checkpoints defined in ``StableDiffusionSchema``.
                Defaults to ``"sd2-community/stable-diffusion-2"``.
            negative_prompt : str or None, optional
                Text describing content to suppress in the output image.
            num_inference_steps : int
                Number of denoising steps.  Higher values improve quality at
                the cost of generation time.
            guidance_scale : float
                Classifier-Free Guidance (CFG) scale controlling prompt
                adherence.
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
