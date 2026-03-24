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
            en=(
                "The Qwen 2.5 Instruct checkpoint to load in GGUF format. "
                "'0.5B' (500M parameters) is faster and uses less memory, suitable "
                "for lightweight tasks on CPU. '1.5B' (1.5B parameters) is more "
                "capable and produces higher-quality responses at the cost of "
                "more memory and slightly slower inference."
            ),
            es=(
                "El checkpoint Qwen 2.5 Instruct a cargar en formato GGUF. "
                "'0.5B' (500M parámetros) es más rápido y usa menos memoria, "
                "adecuado para tareas ligeras en CPU. '1.5B' (1.5B parámetros) "
                "es más capaz y produce respuestas de mayor calidad a costa de "
                "más memoria e inferencia levemente más lenta."
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
                "Roughly 1 token ≈ 0.75 English words. Set to 100–200 for short "
                "answers, 500–1000 for detailed explanations or code. Must not "
                "exceed the context window minus the prompt length."
            ),
            es=(
                "Número máximo de tokens nuevos que el modelo generará por respuesta. "
                "Aproximadamente 1 token ≈ 0.75 palabras en español. Use 100–200 "
                "para respuestas cortas, 500–1000 para explicaciones detalladas o "
                "código. No debe superar la ventana de contexto menos la longitud "
                "del prompt."
            ),
        ),
        alias=MultilingualString(en="Max tokens", es="Tokens máximos"),
    )  # type: ignore

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description=MultilingualString(
            en=(
                "Sampling temperature controlling output randomness (range 0.0–1.0). "
                "At 0.0 the model always picks the most likely token (greedy, fully "
                "deterministic). Around 0.7 is a good balance for conversational "
                "tasks. At 1.0 outputs are maximally varied and unpredictable."
            ),
            es=(
                "Temperatura de muestreo que controla la aleatoriedad de la salida "
                "(rango 0.0–1.0). En 0.0 el modelo siempre elige el token más "
                "probable (greedy, totalmente determinista). Alrededor de 0.7 es "
                "un buen equilibrio para tareas conversacionales. En 1.0 las "
                "salidas son máximamente variadas e impredecibles."
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
                "how often they occur (range 0.0–2.0). At 0.0 there is no penalty "
                "and the model may repeat itself. Values around 0.1–0.3 gently "
                "discourage repetition. High values (1.5+) strongly prevent reuse "
                "of any word, which may produce less coherent text."
            ),
            es=(
                "Penaliza los tokens que ya aparecieron en la salida según su "
                "frecuencia (rango 0.0–2.0). En 0.0 no hay penalización y el modelo "
                "puede repetirse. Valores en torno a 0.1–0.3 desincentivan "
                "suavemente la repetición. Valores altos (1.5+) previenen "
                "fuertemente la reutilización de palabras, lo que puede producir "
                "texto menos coherente."
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
                "input prompt and the generated response. Larger values allow longer "
                "conversations but consume more RAM/VRAM. Qwen 2.5 supports up to "
                "32768 tokens natively; keep this at or below that limit."
            ),
            es=(
                "Presupuesto total de tokens para una sola pasada, incluyendo tanto "
                "el prompt de entrada como la respuesta generada. Valores más altos "
                "permiten conversaciones más largas pero consumen más RAM/VRAM. "
                "Qwen 2.5 soporta hasta 32768 tokens de forma nativa; mantenga "
                "este valor igual o por debajo de ese límite."
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
                "fully in RAM with no GPU requirement. Selecting a GPU option "
                "offloads all layers for faster inference, setting n_gpu_layers=-1 "
                "so every transformer layer is GPU-accelerated."
            ),
            es=(
                "Dispositivo de hardware para la inferencia con llama.cpp. 'CPU' "
                "ejecuta el modelo completamente en RAM sin requisito de GPU. "
                "Seleccionar una opción de GPU descarga todas las capas para "
                "inferencia más rápida, estableciendo n_gpu_layers=-1 para que "
                "cada capa del transformer sea acelerada por GPU."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class QwenModel(TextToTextGenerationTaskModel):
    """Qwen model for text generation using llama.cpp library."""

    SCHEMA = QwenSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME: str = MultilingualString(
        en="Qwen Model",
        es="Modelo Qwen",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Qwen 2.5 is an instruction-tuned large language model by Alibaba Cloud, "
            "loaded in GGUF format for efficient CPU and GPU inference via the "
            "llama.cpp library. It supports multi-turn conversation, reasoning, "
            "coding, and general text generation. Available in 0.5B and 1.5B "
            "parameter sizes. Models are available at "
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF and "
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF."
        ),
        es=(
            "Qwen 2.5 es un modelo de lenguaje grande ajustado para instrucciones "
            "por Alibaba Cloud, cargado en formato GGUF para inferencia eficiente en "
            "CPU y GPU mediante la librería llama.cpp. Soporta conversación "
            "multi-turno, razonamiento, programación y generación de texto en "
            "general. Disponible en tamaños de 0.5B y 1.5B parámetros. Los modelos "
            "están disponibles en "
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF y "
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF."
        ),
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
