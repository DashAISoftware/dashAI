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


class QwenSchema(BaseSchema):
    """Schema for Qwen model."""

    model_name: schema_field(
        enum_field(
            enum=[
                "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
            ]
        ),
        placeholder="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        description=MultilingualString(
            en="The specific Qwen model version to use.",
            es="La versión específica del modelo Qwen a usar.",
        ),
        alias=MultilingualString(en="Model name", es="Nombre del modelo"),
    )  # type: ignore

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description=MultilingualString(
            en="Maximum number of tokens to generate.",
            es="Número máximo de tokens a generar.",
        ),
        alias=MultilingualString(en="Max tokens", es="Tokens máximos"),
    )  # type: ignore

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description=MultilingualString(
            en=(
                "Sampling temperature. Higher values make the output more random, "
                "while lower values make it more focused and deterministic."
            ),
            es=(
                "Temperatura de muestreo. Valores más altos hacen la salida más "
                "aleatoria, mientras que valores más bajos la hacen más enfocada "
                "y determinista."
            ),
        ),
        alias=MultilingualString(en="Temperature", es="Temperatura"),
    )  # type: ignore

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description=MultilingualString(
            en=(
                "Penalty for repeated tokens in the output. Higher values reduce the "
                "likelihood of repetition, encouraging more diverse text generation."
            ),
            es=(
                "Penalización para tokens repetidos en la salida. Valores más altos "
                "reducen la probabilidad de repetición, fomentando una generación "
                "de texto más diversa."
            ),
        ),
        alias=MultilingualString(
            en="Frequency penalty", es="Penalización de frecuencia"
        ),
    )  # type: ignore

    context_window: schema_field(
        int_field(ge=1),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Maximum number of tokens the model can process in a single forward "
                "pass (context window size)."
            ),
            es=(
                "Número máximo de tokens que el modelo puede procesar en una sola "
                "pasada hacia adelante (tamaño de ventana de contexto)."
            ),
        ),
        alias=MultilingualString(en="Context window", es="Ventana de contexto"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=LLAMA_DEVICE_ENUM),
        placeholder=LLAMA_DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en="The device to use for model inference.",
            es="El dispositivo a usar para la inferencia del modelo.",
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class QwenModel(TextToTextGenerationTaskModel):
    """Qwen model for text generation using llama.cpp library."""

    SCHEMA = QwenSchema
    DISPLAY_NAME: str = MultilingualString(
        en="Qwen Model",
        es="Modelo Qwen",
    )
    DESCRIPTION: str = MultilingualString(
        en="Qwen model for text generation using llama.cpp library.",
        es="Modelo Qwen para generación de texto usando la librería llama.cpp.",
    )

    def __init__(self, **kwargs):
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is not installed. Please install it to use QwenModel."
            ) from e

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = "*8_0.gguf"
        use_gpu = LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) >= 0

        self.model = Llama.from_pretrained(
            repo_id=self.model_name,
            filename=self.filename,
            verbose=True,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if use_gpu else 0,
            main_gpu=LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) if use_gpu else 0,
        )

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )
        return [output["choices"][0]["message"]["content"]]
