from typing import Any, List, Tuple

from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.controlnet_model import ControlNetModel as BaseControlNetModel
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


class StableDiffusionXLV1ControlNetSchema(BaseSchema):
    """Configuration schema for the SDXL V1 Depth ControlNet pipeline.

    Configures the denoising schedule (``num_inference_steps``), depth-map
    conditioning strength (``controlnet_conditioning_scale``), prompt adherence
    (``guidance_scale``), and hardware target (``device``) for
    ``StableDiffusionXLV1ControlNet``.
    """

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=15,
        description=MultilingualString(
            en=(
                "Number of denoising steps to run. More steps refine the image but "
                "increase generation time. Typical range: 20-30 for fast results, "
                "40-50 for higher quality. Values above 100 rarely improve output."
            ),
            es=(
                "Número de pasos de eliminación de ruido a ejecutar. Más pasos "
                "refinan la imagen pero aumentan el tiempo de generación. Rango "
                "típico: 20-30 para resultados rápidos, 40-50 para mayor calidad. "
                "Valores superiores a 100 raramente mejoran el resultado."
            ),
            pt=(
                "Número de passos de eliminação de ruído a executar. Mais passos "
                "refinam a imagem mas aumentam o tempo de geração. Intervalo típico: "
                "20-30 para resultados rápidos, 40-50 para maior qualidade. "
                "Valores acima de 100 raramente melhoram o resultado."
            ),
        ),
        alias=MultilingualString(
            en="Num inference steps",
            es="Número de pasos de inferencia",
            pt="Número de passos de inferência",
        ),
    )  # type: ignore

    controlnet_conditioning_scale: schema_field(
        float_field(ge=0.0),
        placeholder=1.0,
        description=MultilingualString(
            en=(
                "Weight of the ControlNet depth conditioning relative to the base "
                "diffusion pipeline. Valid range is 0.0-2.0. At 0.0 the depth map "
                "has no effect; at 1.0 (default) the output closely follows the "
                "input image structure; above 1.5 the depth constraint dominates "
                "and may produce overly rigid results."
            ),
            es=(
                "Peso del condicionamiento de profundidad ControlNet relativo al "
                "pipeline de difusión base. Rango válido: 0.0-2.0. En 0.0 el mapa "
                "de profundidad no tiene efecto; en 1.0 (por defecto) la salida "
                "sigue de cerca la estructura de la imagen de entrada; por encima "
                "de 1.5 la restricción de profundidad domina y puede producir "
                "resultados demasiado rígidos."
            ),
            pt=(
                "Peso do condicionamento de profundidade do ControlNet relativo ao "
                "pipeline de difusão base. Intervalo válido: 0.0-2.0. Em 0.0 o mapa "
                "de profundidade não tem efeito; em 1.0 (padrão) a saída segue de "
                "perto a estrutura da imagem de entrada; acima de 1.5 a restrição de "
                "profundidade domina e pode produzir resultados excessivamente rígidos."
            ),
        ),
        alias=MultilingualString(
            en="ControlNet conditioning scale",
            es="Escala de condicionamiento ControlNet",
            pt="Escala de condicionamento ControlNet",
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
                "para aceleração por hardware, fortemente recomendada para modelos de "
                "difusão. Selecione 'CPU' em sistemas sem GPU compatível, mas espere "
                "tempos de geração significativamente mais longos."
            ),
        ),
        alias=MultilingualString(
            en="Device",
            es="Dispositivo",
            pt="Dispositivo",
        ),
    )  # type: ignore


def get_depth_map(image, device):
    """Convert an input image to a normalised depth map for SDXL ControlNet.

    Uses Intel's DPT-Hybrid-MiDaS model to estimate per-pixel depth, then
    bilinearly interpolates the result to 1024x1024 and normalises values to
    the [0, 1] range before returning a three-channel PIL image.

    Parameters
    ----------
    image : PIL.Image.Image
        The source image to estimate depth from.
    device : str
        Torch device string (e.g. ``"cpu"`` or ``"cuda:0"``) on which the
        depth estimator will run.

    Returns
    -------
    PIL.Image.Image
        A 1024x1024 RGB image where each channel encodes the normalised depth
        value, ready to be used as a ControlNet conditioning signal.
    """
    import numpy as np
    import torch
    from PIL import Image
    from transformers import DPTForDepthEstimation, DPTImageProcessor

    depth_estimator = DPTForDepthEstimation.from_pretrained(
        "Intel/dpt-hybrid-midas"
    ).to(device)
    feature_extractor = DPTImageProcessor.from_pretrained("Intel/dpt-hybrid-midas")

    image = feature_extractor(images=image, return_tensors="pt").pixel_values.to(device)

    with torch.no_grad(), torch.autocast(device, dtype=torch.float16):
        depth_map = depth_estimator(image).predicted_depth

    depth_map = torch.nn.functional.interpolate(
        depth_map.unsqueeze(1),
        size=(1024, 1024),
        mode="bicubic",
        align_corners=False,
    )
    depth_min = torch.amin(depth_map, dim=[1, 2, 3], keepdim=True)
    depth_max = torch.amax(depth_map, dim=[1, 2, 3], keepdim=True)
    depth_map = (depth_map - depth_min) / (depth_max - depth_min)
    image = torch.cat([depth_map] * 3, dim=1)

    image = image.permute(0, 2, 3, 1).cpu().numpy()[0]
    image = Image.fromarray((image * 255.0).clip(0, 255).astype(np.uint8))
    return image


class StableDiffusionXLV1ControlNet(BaseControlNetModel):
    """A wrapper implementation of ControlNet with depth preprocessing and stable
    diffusion xl 1.0 as pipeline."""

    SCHEMA = StableDiffusionXLV1ControlNetSchema
    COLOR: str = "#e65100"
    DISPLAY_NAME: str = MultilingualString(
        en="Stable Diffusion XL V1 ControlNet",
        es="Stable Diffusion XL V1 ControlNet",
        pt="Stable Diffusion XL V1 ControlNet",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Combines ControlNet depth conditioning with the Stable Diffusion XL 1.0 "
            "pipeline for structure-aware image generation. Takes an input image and "
            "a text prompt: a depth map is extracted using Intel's DPT-Hybrid-MiDaS "
            "model, then used as a spatial condition to guide image synthesis. Uses "
            "diffusers/controlnet-depth-sdxl-1.0-small "
            "(https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0-small), "
            "madebyollin/sdxl-vae-fp16-fix "
            "(https://huggingface.co/madebyollin/sdxl-vae-fp16-fix), and "
            "stabilityai/stable-diffusion-xl-base-1.0 "
            "(https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)."
        ),
        es=(
            "Combina el condicionamiento de profundidad de ControlNet con el pipeline "
            "de Stable Diffusion XL 1.0 para generación de imágenes con conciencia "
            "de estructura. Recibe una imagen de entrada y un prompt de texto: se "
            "extrae un mapa de profundidad usando el modelo DPT-Hybrid-MiDaS de Intel "
            "y se usa como condición espacial para guiar la síntesis. Utiliza "
            "diffusers/controlnet-depth-sdxl-1.0-small "
            "(https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0-small), "
            "madebyollin/sdxl-vae-fp16-fix "
            "(https://huggingface.co/madebyollin/sdxl-vae-fp16-fix) y "
            "stabilityai/stable-diffusion-xl-base-1.0 "
            "(https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)."
        ),
        pt=(
            "Combina o condicionamento de profundidade do ControlNet com o pipeline "
            "do Stable Diffusion XL 1.0 para geração de imagens com reconhecimento "
            "de estrutura. Recebe uma imagem de entrada e um prompt de texto: um mapa "
            "de profundidade é extraído usando o modelo DPT-Hybrid-MiDaS da Intel e "
            "usado como condição espacial para guiar a síntese de imagens. Utiliza "
            "diffusers/controlnet-depth-sdxl-1.0-small "
            "(https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0-small), "
            "madebyollin/sdxl-vae-fp16-fix "
            "(https://huggingface.co/madebyollin/sdxl-vae-fp16-fix) e "
            "stabilityai/stable-diffusion-xl-base-1.0 "
            "(https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)."
        ),
    )

    def __init__(self, **kwargs: Any):
        """Initialize the SDXL V1 Depth ControlNet model and pipeline.

        Loads ``diffusers/controlnet-depth-sdxl-1.0-small`` as the ControlNet
        backbone, ``madebyollin/sdxl-vae-fp16-fix`` as the VAE, and
        ``stabilityai/stable-diffusion-xl-base-1.0`` as the base diffusion
        pipeline, all moved to the requested device. CPU offloading is enabled
        automatically via ``pipe.enable_model_cpu_offload()`` to reduce VRAM
        pressure.

        Parameters
        ----------
        **kwargs : Any
            Keyword arguments validated against
            :class:`StableDiffusionXLV1ControlNetSchema`. Recognised keys are:

            device : str
                Target hardware (e.g. ``"GPU 0"`` or ``"CPU"``).
            num_inference_steps : int
                Number of denoising steps during generation.
            controlnet_conditioning_scale : float
                Strength of the depth-map conditioning signal (0.0-2.0).
        """
        import torch
        from diffusers import (
            AutoencoderKL,
            ControlNetModel,
            StableDiffusionXLControlNetPipeline,
        )

        kwargs = self.validate_and_transform(kwargs)
        use_gpu = DEVICE_TO_IDX.get(kwargs.get("device")) >= 0
        self.device = (
            f"cuda:{DEVICE_TO_IDX.get(kwargs.get('device'))}" if use_gpu else "cpu"
        )

        self.controlnet = ControlNetModel.from_pretrained(
            "diffusers/controlnet-depth-sdxl-1.0-small",
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.vae = AutoencoderKL.from_pretrained(
            "madebyollin/sdxl-vae-fp16-fix",
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            controlnet=self.controlnet,
            vae=self.vae,
            variant="fp16",
            use_safetensors=True,
            torch_dtype=torch.float32 if self.device == "cpu" else torch.float16,
        ).to(self.device)

        self.controlnet_conditioning_scale = kwargs.get("controlnet_conditioning_scale")
        self.num_inference_steps = kwargs.get("num_inference_steps")

        if self.device != "cpu":
            self.pipe.enable_model_cpu_offload()

    def generate(self, input: Tuple[Any, str]) -> List[Any]:
        """Generate output from a generative model.

        Parameters
        ----------
        input : Tuple[Any, str]
            Input data to be generated

        Returns
        -------
        List[Any]
            Generated output data in a list
        """
        image = input[0]
        prompt = input[1]

        depth_map = get_depth_map(image, self.device)
        image = self.pipe(
            prompt=prompt,
            image=depth_map,
            num_inference_steps=self.num_inference_steps,
            controlnet_conditioning_scale=self.controlnet_conditioning_scale,
            height=image.size[1],
            width=image.size[0],
        ).images

        return image
