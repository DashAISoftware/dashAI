from typing import List

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)
from DashAI.back.models.utils import (
    LLAMA_DEVICE_ENUM,
    LLAMA_DEVICE_PLACEHOLDER,
    LLAMA_DEVICE_TO_IDX,
)

SMOLLM_FILENAME_MAP = {
    "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF": "*Q4_K_M.gguf",
    "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF": "*Q8_0.gguf",
}


class SmolLMSchema(BaseSchema):
    """Schema for SmolLM2 model."""

    model_name: schema_field(
        enum_field(
            enum=[
                "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
                "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
            ]
        ),
        placeholder="HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        description=MultilingualString(
            en=(
                "The SmolLM2 Instruct checkpoint to load in GGUF format. "
                "'SmolLM2-1.7B' is a 1.7B-parameter instruction model with strong "
                "performance for on-device and edge inference. "
                "'SmolLM2-360M' is an ultra-compact 360M-parameter model for "
                "extremely fast CPU inference with minimal memory usage (~300 MB). "
                "Both models are trained on diverse synthetic datasets by Hugging Face."
            ),
            es=(
                "El checkpoint SmolLM2 Instruct a cargar en formato GGUF. "
                "'SmolLM2-1.7B' es un modelo de instrucción de 1.7B parámetros con "
                "fuerte rendimiento para inferencia en dispositivos y en el borde. "
                "'SmolLM2-360M' es un modelo ultra-compacto de 360M parámetros para "
                "inferencia CPU extremadamente rápida con uso mínimo de memoria "
                "(~300 MB). "
                "Ambos modelos son entrenados en datasets sintéticos diversos por "
                "Hugging Face."
            ),
        ),
        alias=MultilingualString(en="Model name", es="Nombre del modelo"),
    )  # type: ignore

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description=MultilingualString(
            en=(
                "Maximum number of new tokens the model will generate per response. "
                "Roughly 1 token ≈ 0.75 English words. SmolLM2 models are optimized "
                "for short to medium-length responses."
            ),
            es=(
                "Número máximo de tokens nuevos que el modelo generará por respuesta. "
                "Aproximadamente 1 token ≈ 0.75 palabras en español. Los modelos "
                "SmolLM2 están optimizados para respuestas cortas a medianas."
            ),
        ),
        alias=MultilingualString(en="Max tokens", es="Tokens máximos"),
    )  # type: ignore

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description=MultilingualString(
            en=(
                "Sampling temperature controlling output randomness (range 0.0-1.0). "
                "At 0.0 outputs are deterministic. Around 0.7 balances quality and "
                "creativity."
            ),
            es=(
                "Temperatura de muestreo que controla la aleatoriedad (rango 0.0-1.0). "
                "En 0.0 las salidas son deterministas. Alrededor de 0.7 equilibra "
                "calidad y creatividad."
            ),
        ),
        alias=MultilingualString(en="Temperature", es="Temperatura"),
    )  # type: ignore

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description=MultilingualString(
            en=(
                "Penalizes tokens that have already appeared in the output based on "
                "frequency (range 0.0-2.0). Higher values discourage repetition."
            ),
            es=(
                "Penaliza los tokens que ya aparecieron en la salida según su "
                "frecuencia (rango 0.0-2.0). Valores más altos desincentivan "
                "la repetición."
            ),
        ),
        alias=MultilingualString(
            en="Frequency penalty", es="Penalización de frecuencia"
        ),
    )  # type: ignore

    context_window: schema_field(
        int_field(ge=1, le=8192),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Total token budget for a single forward pass, including both the "
                "input prompt and the generated response. SmolLM2 models support "
                "up to 8K tokens natively."
            ),
            es=(
                "Presupuesto total de tokens por pasada, incluyendo prompt y "
                "respuesta. Los modelos SmolLM2 soportan hasta 8K tokens de "
                "forma nativa."
            ),
        ),
        alias=MultilingualString(en="Context window", es="Ventana de contexto"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=LLAMA_DEVICE_ENUM),
        placeholder=LLAMA_DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware device for llama.cpp inference. 'CPU' runs the model "
                "fully in RAM with no GPU requirement. SmolLM2 models are small "
                "enough to run efficiently on CPU even on modest hardware."
            ),
            es=(
                "Dispositivo de hardware para inferencia con llama.cpp. 'CPU' ejecuta "
                "el modelo en RAM sin requisito de GPU. Los modelos SmolLM2 son lo "
                "suficientemente pequeños para ejecutarse eficientemente en CPU "
                "incluso "
                "en hardware modesto."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class SmolLMModel(TextToTextGenerationTaskModel):
    """SmolLM2 model for lightweight text generation using llama.cpp library."""

    SCHEMA = SmolLMSchema
    COLOR: str = "#00695c"
    DISPLAY_NAME: str = MultilingualString(
        en="SmolLM Model",
        es="Modelo SmolLM",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "SmolLM2 is a family of compact instruction-tuned language models by "
            "Hugging Face, loaded in GGUF format for efficient CPU and GPU inference "
            "via the llama.cpp library. Designed for on-device and edge deployment, "
            "SmolLM2 achieves strong benchmark results at very small parameter counts. "
            "The 360M variant requires less than 300 MB of RAM, making it ideal for "
            "resource-constrained environments. Available in 360M and 1.7B variants. "
            "Models available at https://huggingface.co/HuggingFaceTB."
        ),
        es=(
            "SmolLM2 es una familia de modelos de lenguaje compactos ajustados para "
            "instrucciones por Hugging Face, cargados en formato GGUF para inferencia "
            "eficiente en CPU y GPU mediante llama.cpp. Diseñados para despliegue en "
            "dispositivo y en el borde, SmolLM2 logra fuertes resultados de benchmark "
            "con muy pocos parámetros. La variante de 360M requiere menos de 300 MB de "
            "RAM, ideal para entornos con recursos limitados. Disponible en variantes "
            "de 360M y 1.7B. Modelos en https://huggingface.co/HuggingFaceTB."
        ),
    )

    def __init__(self, **kwargs):
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Please install it to use this model."
            ) from e

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get(
            "model_name", "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF"
        )
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = SMOLLM_FILENAME_MAP.get(self.model_name, "*Q4_K_M.gguf")
        use_gpu = LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) >= 0

        self.model = Llama.from_pretrained(
            repo_id=self.model_name,
            filename=self.filename,
            verbose=True,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if use_gpu else 0,
            main_gpu=(LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) if use_gpu else 0),
        )

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )
        return [output["choices"][0]["message"]["content"]]
