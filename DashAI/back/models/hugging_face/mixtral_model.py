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


class MixtralSchema(BaseSchema):
    """Schema for Mixtral model."""

    model_name: schema_field(
        enum_field(
            enum=[
                "mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF",
            ]
        ),
        placeholder="mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF",
        description=MultilingualString(
            en=(
                "The Mixtral Instruct checkpoint to load in GGUF format. "
                "'Mixtral-8x7B-Instruct-v0.1' is a Sparse Mixture-of-Experts (SMoE) "
                "model with 8 expert networks of 7B parameters each, activating 2 "
                "experts per token. It achieves quality comparable to larger dense "
                "models while being more efficient at inference. "
                "Warning: this model requires ~26 GB of RAM for the Q4_K_M "
                "quantization."
            ),
            es=(
                "El checkpoint Mixtral Instruct a cargar en formato GGUF. "
                "'Mixtral-8x7B-Instruct-v0.1' es un modelo de Mezcla Dispersa de "
                "Expertos (SMoE) con 8 redes expertas de 7B parámetros cada una, "
                "activando 2 expertos por token. Logra calidad comparable a modelos "
                "densos más grandes siendo más eficiente en inferencia. "
                "Advertencia: este modelo requiere ~26 GB de RAM para la "
                "cuantización Q4_K_M."
            ),
        ),
        alias=MultilingualString(en="Model name", es="Nombre del modelo"),
    )  # type: ignore

    filename: schema_field(
        enum_field(
            enum=[
                "mixtral-8x7b-instruct-v0.1.Q2_K.gguf",
                "mixtral-8x7b-instruct-v0.1.Q3_K_M.gguf",
                "mixtral-8x7b-instruct-v0.1.Q4_0.gguf",
                "mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf",
                "mixtral-8x7b-instruct-v0.1.Q5_0.gguf",
                "mixtral-8x7b-instruct-v0.1.Q5_K_M.gguf",
                "mixtral-8x7b-instruct-v0.1.Q6_K.gguf",
                "mixtral-8x7b-instruct-v0.1.Q8_0.gguf",
            ]
        ),
        placeholder="mixtral-8x7b-instruct-v0.1.Q2_K.gguf",
        description=MultilingualString(
            en=(
                "The specific GGUF file to load for the Mixtral model. The different "
                "quantization levels (Q2_K, Q3_K_M, Q4_0, Q4_K_M, Q5_0, Q5_K_M, "
                "Q6_K, Q8_0) represent various trade-offs between model size, "
                "inference speed, and output quality. Q4_K_M is a popular choice "
                "for balancing performance and resource requirements."
            ),
            es=(
                "El archivo GGUF específico a cargar para el modelo Mixtral. Los "
                "diferentes niveles de cuantización (Q2_K, Q3_K_M, Q4_0, Q4_K_M, "
                "Q5_0, Q5_K_M, Q6_K, Q8_0) representan varios compromisos entre "
                "tamaño del modelo, velocidad de inferencia y calidad de salida. "
                "Q4_K_M es una opción popular para equilibrar rendimiento y "
                "requisitos de recursos."
            ),
        ),
        alias=MultilingualString(en="Filename", es="Nombre del archivo"),
    )  # type: ignore

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description=MultilingualString(
            en=(
                "Maximum number of new tokens the model will generate per response. "
                "Roughly 1 token ≈ 0.75 English words. Set to 100-200 for short "
                "answers, 500-1000 for detailed explanations or code."
            ),
            es=(
                "Número máximo de tokens nuevos que el modelo generará por respuesta. "
                "Aproximadamente 1 token ≈ 0.75 palabras en español. Use 100-200 "
                "para respuestas cortas, 500-1000 para explicaciones detalladas "
                "o código."
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
        int_field(ge=1, le=32768),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Total token budget for a single forward pass, including both the "
                "input prompt and the generated response. Mixtral 8x7B supports "
                "up to 32K tokens natively."
            ),
            es=(
                "Presupuesto total de tokens por pasada, incluyendo prompt y "
                "respuesta. Mixtral 8x7B soporta hasta 32K tokens de forma nativa."
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
                "fully in RAM. A GPU option offloads all layers for faster inference. "
                "Due to the large size of Mixtral, a GPU with at least 24 GB VRAM "
                "is recommended for full GPU offloading."
            ),
            es=(
                "Dispositivo de hardware para inferencia con llama.cpp. 'CPU' ejecuta "
                "el modelo en RAM. Una opción de GPU descarga todas las capas para "
                "inferencia más rápida. Debido al gran tamaño de Mixtral, "
                "se recomienda "
                "una GPU con al menos 24 GB de VRAM para descarga completa."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class MixtralModel(TextToTextGenerationTaskModel):
    """Mixtral Sparse Mixture-of-Experts model for text generation using llama.cpp."""

    SCHEMA = MixtralSchema
    COLOR: str = "#4a148c"
    DISPLAY_NAME: str = MultilingualString(
        en="Mixtral Model",
        es="Modelo Mixtral",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Mixtral 8x7B Instruct, a Sparse Mixture-of-Experts (SMoE) model by "
            "Mistral AI, loaded in GGUF format for efficient CPU and GPU inference "
            "via the llama.cpp library. The model uses 8 expert networks of 7B "
            "parameters each, activating only 2 experts per token, achieving "
            "performance comparable to larger dense models while being more efficient "
            "at inference. Supports multi-turn conversation, reasoning, coding, and "
            "general text generation. Warning: requires ~26 GB of RAM for the Q4_K_M "
            "quantization. Model hosted at "
            "https://huggingface.co/mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF."
        ),
        es=(
            "Mixtral 8x7B Instruct, un modelo de Mezcla Dispersa de Expertos (SMoE) "
            "de Mistral AI, cargado en formato GGUF para inferencia eficiente en CPU "
            "y GPU mediante llama.cpp. El modelo usa 8 redes expertas de 7B parámetros "
            "cada una, activando solo 2 expertos por token, logrando un rendimiento "
            "comparable a modelos densos más grandes "
            "siendo más eficiente en inferencia. "
            "Soporta conversación multi-turno, razonamiento, programación y generación "
            "de texto en general. Advertencia: requiere ~26 GB de RAM para la "
            "cuantización Q4_K_M. Modelo en "
            "https://huggingface.co/mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF."
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
            "model_name", "mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF"
        )
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = kwargs.get("filename", "mixtral-8x7b-instruct-v0.1.Q2_K.gguf")
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
