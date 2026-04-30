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

LLAMA_FILENAME_MAP = {
    "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF": "*Q4_K_M.gguf",
    "bartowski/Llama-3.2-1B-Instruct-GGUF": "*Q4_K_M.gguf",
    "bartowski/Llama-3.2-3B-Instruct-GGUF": "*Q4_K_M.gguf",
}


class LlamaSchema(BaseSchema):
    """Configuration schema for Meta Llama 3.x text generation.

    Configures the GGUF checkpoint variant (``model_name``), generation
    behaviour (``max_tokens``, ``temperature``, ``frequency_penalty``),
    context length (``context_window``), device target (``device``), and
    system prompt (``system_prompt``) for ``LlamaModel``.
    """

    model_name: schema_field(
        enum_field(
            enum=[
                "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
                "bartowski/Llama-3.2-1B-Instruct-GGUF",
                "bartowski/Llama-3.2-3B-Instruct-GGUF",
            ]
        ),
        placeholder="bartowski/Llama-3.2-3B-Instruct-GGUF",
        description=MultilingualString(
            en=(
                "The Meta Llama 3.x Instruct checkpoint to load in GGUF format via "
                "bartowski's community quantizations. 'Llama-3.2-1B' (~1B parameters) "
                "is the smallest and fastest, ideal for CPU-only systems. "
                "'Llama-3.2-3B' (~3B parameters) offers a good speed/quality "
                "trade-off. "
                "'Meta-Llama-3.1-8B' (~8B parameters) delivers the highest quality "
                "at the cost of more RAM and slower inference."
            ),
            es=(
                "El checkpoint Meta Llama 3.x Instruct a cargar en formato GGUF "
                "mediante las cuantizaciones comunitarias de bartowski. "
                "'Llama-3.2-1B' (~1B parámetros) es el más pequeño y rápido, "
                "ideal para sistemas solo con CPU. "
                "'Llama-3.2-3B' (~3B parámetros) ofrece un buen equilibrio entre "
                "velocidad y calidad. 'Meta-Llama-3.1-8B' (~8B parámetros) entrega "
                "la mayor calidad a costa de más RAM e inferencia más lenta."
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
                "Roughly 1 token ≈ 0.75 English words. Set to 100-200 for short "
                "answers, 500-1000 for detailed explanations or code. Must not "
                "exceed the context window minus the prompt length."
            ),
            es=(
                "Número máximo de tokens nuevos que el modelo generará por respuesta. "
                "Aproximadamente 1 token ≈ 0.75 palabras en español. Use 100-200 "
                "para respuestas cortas, 500-1000 para explicaciones detalladas o "
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
                "Sampling temperature controlling output randomness (range 0.0-1.0). "
                "At 0.0 the model always picks the most likely token (greedy, fully "
                "deterministic). Around 0.7 is a good balance for conversational "
                "tasks. At 1.0 outputs are maximally varied and unpredictable."
            ),
            es=(
                "Temperatura de muestreo que controla la aleatoriedad de la salida "
                "(rango 0.0-1.0). En 0.0 el modelo siempre elige el token más "
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
                "how often they occur (range 0.0-2.0). At 0.0 there is no penalty "
                "and the model may repeat itself. Values around 0.1-0.3 gently "
                "discourage repetition. High values (1.5+) strongly prevent reuse "
                "of any word, which may produce less coherent text."
            ),
            es=(
                "Penaliza los tokens que ya aparecieron en la salida según su "
                "frecuencia (rango 0.0-2.0). En 0.0 no hay penalización y el modelo "
                "puede repetirse. Valores en torno a 0.1-0.3 desincentivan "
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
        int_field(ge=1, le=131072),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Total token budget for a single forward pass, including both the "
                "input prompt and the generated response. Larger values allow longer "
                "conversations but consume more RAM/VRAM. Llama 3.1 supports up to "
                "128K tokens natively; Llama 3.2 models support up to 128K tokens."
            ),
            es=(
                "Presupuesto total de tokens para una sola pasada, incluyendo tanto "
                "el prompt de entrada como la respuesta generada. Valores más altos "
                "permiten conversaciones más largas pero consumen más RAM/VRAM. "
                "Llama 3.1 soporta hasta 128K tokens de forma nativa; los modelos "
                "Llama 3.2 soportan hasta 128K tokens."
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


class LlamaModel(TextToTextGenerationTaskModel):
    """Meta Llama 3.x instruction-tuned model for text generation via llama.cpp.

    Wraps the Meta Llama 3.x family of open-weight instruction-tuned LLMs
    loaded in Q4_K_M GGUF format using the ``llama-cpp-python`` library.
    GGUF quantization enables efficient CPU and GPU inference without requiring
    full-precision weights, making the models practical on consumer hardware.

    Three sizes are available via bartowski's community quantizations:
    1B (fastest, CPU-friendly), 3B (balanced), and 8B (highest quality).

    References
    ----------
    - [1] Meta AI, "Llama 3", 2024. https://ai.meta.com/blog/meta-llama-3/
    - [2] https://huggingface.co/bartowski
    """

    SCHEMA = LlamaSchema
    COLOR: str = "#1a237e"
    TAGS: list = ["llama.cpp", "Meta AI"]
    DISPLAY_NAME: str = MultilingualString(
        en="Llama Model",
        es="Modelo Llama",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Meta Llama 3.x is a family of open instruction-tuned large language "
            "models developed by Meta AI, loaded in GGUF format for efficient CPU "
            "and GPU inference via the llama.cpp library. It supports multi-turn "
            "conversation, reasoning, coding, and general text generation. Available "
            "in 1B, 3B, and 8B parameter sizes. Models are hosted at "
            "https://huggingface.co/bartowski."
        ),
        es=(
            "Meta Llama 3.x es una familia de modelos de lenguaje grande de código "
            "abierto ajustados para instrucciones, desarrollados por Meta AI, cargados "
            "en formato GGUF para inferencia eficiente en CPU y GPU mediante la "
            "librería llama.cpp. Soporta conversación multi-turno, razonamiento, "
            "programación y generación de texto en general. Disponible en tamaños de "
            "1B, 3B y 8B parámetros. Los modelos están en "
            "https://huggingface.co/bartowski."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise a Llama 3.x GGUF model via llama.cpp.

        The model weights are fetched from HuggingFace Hub using
        ``Llama.from_pretrained`` and kept in memory for repeated calls to
        ``generate``.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace repo ID for the GGUF checkpoint.
                Defaults to ``"bartowski/Llama-3.2-3B-Instruct-GGUF"``.
            max_tokens : int, optional
                Maximum number of new tokens to generate per call. Default 100.
            temperature : float, optional
                Sampling temperature in [0.0, 1.0]. Default 0.7.
            frequency_penalty : float, optional
                Token-frequency penalty in [0.0, 2.0]. Default 0.1.
            context_window : int, optional
                Total token budget (prompt + response) for a single forward
                pass. Default 512.
            device : str, optional
                Target device from ``LLAMA_DEVICE_ENUM``. Any value whose
                index is >= 0 enables full GPU offload (``n_gpu_layers=-1``);
                ``"CPU"`` runs fully in RAM.

        Raises
        ------
        RuntimeError
            If ``llama-cpp-python`` is not installed.
        """
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is not installed. "
                "Please install it to use this model."
            ) from e

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get(
            "model_name", "bartowski/Llama-3.2-3B-Instruct-GGUF"
        )
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = LLAMA_FILENAME_MAP.get(self.model_name, "*Q4_K_M.gguf")
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
        """Generate a reply for the given chat prompt.

        Parameters
        ----------
        prompt : list of dict
            Conversation history in OpenAI chat format. Each dict must contain
            at least ``"role"`` (``"system"``, ``"user"``, or ``"assistant"``)
            and ``"content"`` (the message text).

        Returns
        -------
        list of str
            A single-element list containing the model's reply text, extracted
            from ``choices[0]["message"]["content"]``.
        """
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )
        return [output["choices"][0]["message"]["content"]]
