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
    """Schema for SmolLM2 model hyperparameters.

    Configures the SmolLM2 Instruct checkpoint variant (360M or 1.7B), generation
    length, sampling temperature, frequency penalty, context window, and target
    device. The GGUF filename is resolved automatically from ``SMOLLM_FILENAME_MAP``:
    Q4_K_M quantization for 1.7B and Q8_0 quantization for 360M.
    """

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
            pt=(
                "O checkpoint SmolLM2 Instruct a carregar em formato GGUF. "
                "'SmolLM2-1.7B' é um modelo de instrução de 1.7B parâmetros com "
                "forte desempenho para inferência em dispositivos e na borda. "
                "'SmolLM2-360M' é um modelo ultra-compacto de 360M parâmetros para "
                "inferência CPU extremamente rápida com uso mínimo de memória "
                "(~300 MB). "
                "Ambos os modelos são treinados em conjuntos de dados sintéticos "
                "diversos pelo Hugging Face."
            ),
        ),
        alias=MultilingualString(
            en="Model name", es="Nombre del modelo", pt="Nome do modelo"
        ),
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
            pt=(
                "Número máximo de tokens novos que o modelo gerará por resposta. "
                "Aproximadamente 1 token ≈ 0.75 palavras em português. Os modelos "
                "SmolLM2 são otimizados para respostas curtas a médias."
            ),
        ),
        alias=MultilingualString(
            en="Max tokens", es="Tokens máximos", pt="Tokens máximos"
        ),
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
            pt=(
                "Temperatura de amostragem que controla a aleatoriedade da saída "
                "(intervalo 0.0-1.0). Em 0.0 as saídas são determinísticas. "
                "Em torno de 0.7 equilibra qualidade e criatividade."
            ),
        ),
        alias=MultilingualString(en="Temperature", es="Temperatura", pt="Temperatura"),
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
            pt=(
                "Penaliza os tokens que já apareceram na saída com base na "
                "frequência (intervalo 0.0-2.0). Valores mais altos desestimulam "
                "a repetição."
            ),
        ),
        alias=MultilingualString(
            en="Frequency penalty",
            es="Penalización de frecuencia",
            pt="Penalização de frequência",
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
            pt=(
                "Orçamento total de tokens por passagem, incluindo prompt e "
                "resposta. Os modelos SmolLM2 suportam até 8K tokens nativamente."
            ),
        ),
        alias=MultilingualString(
            en="Context window", es="Ventana de contexto", pt="Janela de contexto"
        ),
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
            pt=(
                "Dispositivo de hardware para inferência com llama.cpp. 'CPU' executa "
                "o modelo na RAM sem requisito de GPU. Os modelos SmolLM2 são "
                "pequenos o suficiente para rodar eficientemente em CPU "
                "mesmo em hardware modesto."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo", pt="Dispositivo"),
    )  # type: ignore


class SmolLMModel(TextToTextGenerationTaskModel):
    """SmolLM2 Instruct model for on-device text generation via llama.cpp.

    SmolLM2 is a family of compact, instruction-tuned language models developed by
    Hugging Face TB, designed for efficient on-device and edge deployment. Unlike
    larger language models, SmolLM2 achieves competitive benchmark results at very
    small parameter counts by training on high-quality synthetic datasets including
    cosmopedia-v2, FineWeb-Edu, and StackEdu.

    The DashAI integration exposes the 360M and 1.7B Instruct variants. The 360M
    model requires under 300 MB of RAM and runs comfortably on modest CPU hardware;
    the 1.7B model delivers higher-quality responses while remaining deployable
    without a GPU.

    Models are loaded as GGUF quantized checkpoints via ``llama-cpp-python``. The
    quantization level is variant-dependent: Q8_0 for 360M (higher fidelity at small
    size) and Q4_K_M for 1.7B (balanced quality/size trade-off). The filename is
    resolved automatically from ``SMOLLM_FILENAME_MAP``.

    References
    ----------
    - [1] Allal, L.B. et al. (2024). "SmolLM2 — with great data, comes great
           performance." Hugging Face Blog.
           https://huggingface.co/blog/smollm2
    - [2] https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF
    - [3] https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF
    """

    SCHEMA = SmolLMSchema
    COLOR: str = "#00695c"
    DISPLAY_NAME: str = MultilingualString(
        en="SmolLM Model",
        es="Modelo SmolLM",
        pt="Modelo SmolLM",
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
        pt=(
            "SmolLM2 é uma família de modelos de linguagem compactos ajustados para "
            "instruções pelo Hugging Face, carregados em formato GGUF para inferência "
            "eficiente em CPU e GPU via llama.cpp. Projetados para implantação em "
            "dispositivos e na borda, SmolLM2 alcança fortes resultados de benchmark "
            "com pouquíssimos parâmetros. A variante de 360M requer menos de 300 MB de "
            "RAM, ideal para ambientes com recursos limitados. "
            "Disponível nas variantes "
            "360M e 1.7B. Modelos disponíveis em https://huggingface.co/HuggingFaceTB."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise a SmolLM2 Instruct GGUF model via llama.cpp.

        The model weights are fetched from HuggingFace Hub using
        ``Llama.from_pretrained`` and kept in memory for repeated calls to
        ``generate``. The GGUF filename is resolved from ``SMOLLM_FILENAME_MAP``
        (Q4_K_M for 1.7B, Q8_0 for 360M).

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace repo ID for the GGUF checkpoint.
                Defaults to ``"HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF"``.
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
