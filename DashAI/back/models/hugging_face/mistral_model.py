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


class MistralSchema(BaseSchema):
    """Schema for MistralModel hyperparameters.

    Configures the checkpoint variant, generation length, sampling temperature,
    frequency penalty, context window, and target device for Mistral Instruct
    models loaded via ``llama-cpp-python`` in GGUF format.
    """

    model_name: schema_field(
        enum_field(
            enum=[
                "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
                "bartowski/Mistral-Nemo-Instruct-2407-GGUF",
            ]
        ),
        placeholder="bartowski/Mistral-7B-Instruct-v0.3-GGUF",
        description=MultilingualString(
            en=(
                "The Mistral Instruct checkpoint to load in GGUF format. "
                "'Mistral-7B-Instruct-v0.3' is a 7B-parameter instruction model "
                "that delivers strong performance for its size. "
                "'Mistral-Nemo-Instruct-2407' is a 12B-parameter model jointly "
                "developed with NVIDIA, featuring a 128K context window and "
                "improved multilingual capabilities."
            ),
            es=(
                "El checkpoint Mistral Instruct a cargar en formato GGUF. "
                "'Mistral-7B-Instruct-v0.3' es un modelo de instrucción de 7B "
                "parámetros con fuerte rendimiento para su tamaño. "
                "'Mistral-Nemo-Instruct-2407' es un modelo de 12B parámetros "
                "desarrollado conjuntamente con NVIDIA, con una ventana de contexto "
                "de 128K y mejores capacidades multilingües."
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
                "At 0.0 the model picks the most likely token (deterministic). "
                "Around 0.7 balances quality and creativity. At 1.0 outputs are "
                "maximally varied."
            ),
            es=(
                "Temperatura de muestreo que controla la aleatoriedad (rango 0.0-1.0). "
                "En 0.0 el modelo elige el token más probable (determinista). "
                "Alrededor de 0.7 equilibra calidad y creatividad. En 1.0 las salidas "
                "son máximamente variadas."
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
        int_field(ge=1, le=131072),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Total token budget for a single forward pass, including prompt and "
                "response. Mistral-7B supports up to 32K tokens; Mistral-Nemo "
                "supports up to 128K tokens."
            ),
            es=(
                "Presupuesto total de tokens por pasada, incluyendo prompt y "
                "respuesta. Mistral-7B soporta hasta 32K tokens; Mistral-Nemo "
                "soporta hasta 128K tokens."
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
                "fully in RAM. A GPU option offloads all layers for faster inference."
            ),
            es=(
                "Dispositivo de hardware para inferencia con llama.cpp. 'CPU' ejecuta "
                "el modelo en RAM. Una opción de GPU descarga todas las capas para "
                "inferencia más rápida."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class MistralModel(TextToTextGenerationTaskModel):
    """Mistral Instruct model for open-ended text generation via llama.cpp.

    Mistral is a 7B-parameter transformer language model developed by Mistral AI,
    designed to deliver high performance with efficient inference. It uses grouped-
    query attention (GQA) for faster decoding and sliding-window attention (SWA) to
    handle long contexts efficiently. The 12B Mistral-Nemo variant, developed jointly
    with NVIDIA, extends the context window to 128 K tokens and improves multilingual
    capability.

    Models are loaded as GGUF quantized checkpoints via ``llama-cpp-python``,
    allowing CPU and GPU inference without requiring a full PyTorch stack.

    References
    ----------
    .. [1] Jiang et al. (2023) "Mistral 7B" https://arxiv.org/abs/2310.06825
    .. [2] https://huggingface.co/mistralai
    """

    SCHEMA = MistralSchema
    COLOR: str = "#ff6f00"
    DISPLAY_NAME: str = MultilingualString(
        en="Mistral Model",
        es="Modelo Mistral",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Mistral instruction-tuned models by Mistral AI, loaded in GGUF format "
            "for efficient CPU and GPU inference via the llama.cpp library. Mistral "
            "models are known for strong performance relative to their parameter count "
            "and efficient inference. Supports multi-turn conversation, reasoning, "
            "and general text generation. Available in 7B (Mistral-7B-v0.3) and 12B "
            "(Mistral-Nemo-2407) variants. Models hosted at "
            "https://huggingface.co/bartowski."
        ),
        es=(
            "Modelos ajustados para instrucciones de Mistral AI, cargados en formato "
            "GGUF para inferencia eficiente en CPU y GPU mediante llama.cpp. "
            "Los modelos "
            "Mistral son conocidos por su fuerte rendimiento relativo a su cantidad de "
            "parámetros e inferencia eficiente. Soporta conversación multi-turno, "
            "razonamiento y generación de texto en general. Disponible en variantes de "
            "7B (Mistral-7B-v0.3) y 12B (Mistral-Nemo-2407). Modelos en "
            "https://huggingface.co/bartowski."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise a Mistral Instruct GGUF model via llama.cpp.

        The model weights are fetched from HuggingFace Hub using
        ``Llama.from_pretrained`` and kept in memory for repeated calls to
        ``generate``.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace repo ID for the GGUF checkpoint.
                Defaults to ``"bartowski/Mistral-7B-Instruct-v0.3-GGUF"``.
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
            "model_name", "bartowski/Mistral-7B-Instruct-v0.3-GGUF"
        )
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = "*Q4_K_M.gguf"
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
