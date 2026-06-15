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
            de=(
                "Der im GGUF-Format zu ladende SmolLM2 Instruct-Checkpoint. "
                "'SmolLM2-1.7B' ist ein 1,7B-Parameter-Instruktionsmodell mit starker "
                "Leistung für Inferenz auf Endgeräten und Edge-Systemen. "
                "'SmolLM2-360M' ist ein ultra-kompaktes 360M-Parameter-Modell für "
                "extrem schnelle CPU-Inferenz mit minimalem Speicherbedarf (~300 MB). "
                "Beide Modelle werden von Hugging Face auf diversen synthetischen "
                "Datensätzen trainiert."
            ),
            zh=(
                "以 GGUF 格式加载的 SmolLM2 Instruct 检查点。"
                "'SmolLM2-1.7B' 是 17 亿参数指令模型，适用于端侧和边缘推理。"
                "'SmolLM2-360M' 是 3.6 亿参数超紧凑模型，CPU 推理极快，"
                "内存占用极低（约 300 MB）。"
                "两款模型均由 Hugging Face 在多样化合成数据集上训练。"
            ),
        ),
        alias=MultilingualString(
            en="Model name",
            es="Nombre del modelo",
            pt="Nome do modelo",
            de="Modellname",
            zh="模型名称",
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
            de=(
                "Maximale Anzahl neuer Token, die das Modell pro Antwort erzeugt. "
                "Ungefähr 1 Token ≈ 0,75 englische Wörter. SmolLM2-Modelle sind "
                "für kurze bis mittellange Antworten optimiert."
            ),
            zh=(
                "模型每次响应生成的最大新词元数。"
                "约 1 词元 ≈ 0.75 个英文单词。"
                "SmolLM2 模型针对短至中等长度的响应进行了优化。"
            ),
        ),
        alias=MultilingualString(
            en="Max tokens",
            es="Tokens máximos",
            pt="Tokens máximos",
            de="Maximale neue Token",
            zh="最大词元数",
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
            de=(
                "Stichprobentemperatur zur Steuerung der Ausgabezufälligkeit (0.0-1.0)."
                "Bei 0.0 sind die Ausgaben deterministisch. Um 0.7 balanciert "
                "Qualität und Kreativität."
            ),
            zh=(
                "控制输出随机性的采样温度（范围 0.0-1.0）。"
                "0.0 时输出为确定性结果，0.7 左右可平衡质量与创造力。"
            ),
        ),
        alias=MultilingualString(
            en="Temperature",
            es="Temperatura",
            pt="Temperatura",
            de="Temperatur",
            zh="温度",
        ),
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
            de=(
                "Bestraft Token, die bereits in der Ausgabe erschienen sind, "
                "basierend auf ihrer Häufigkeit (0.0-2.0). Höhere Werte reduzieren "
                "Wiederholungen."
            ),
            zh=(
                "根据词元在输出中出现的频率对其进行惩罚（范围 0.0-2.0）。"
                "较高的值可抑制重复内容。"
            ),
        ),
        alias=MultilingualString(
            en="Frequency penalty",
            es="Penalización de frecuencia",
            pt="Penalização de frequência",
            de="Häufigkeitsstrafe",
            zh="频率惩罚",
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
            de=(
                "Gesamtes Token-Budget für einen einzelnen Vorwärtsdurchlauf, "
                "einschließlich Eingabe-Prompt und Antwort. "
                "SmolLM2-Modelle unterstützen nativ bis zu 8K Token."
            ),
            zh=(
                "单次前向传播的词元总预算，包含输入提示和生成响应。"
                "SmolLM2 模型原生支持最多 8K 词元。"
            ),
        ),
        alias=MultilingualString(
            en="Context window",
            es="Ventana de contexto",
            pt="Janela de contexto",
            de="Kontextfenster",
            zh="上下文窗口",
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
            de=(
                "Hardware-Gerät für die llama.cpp-Inferenz. 'CPU' führt das Modell "
                "im RAM ohne GPU-Anforderung aus. SmolLM2-Modelle sind klein genug, "
                "um auch auf bescheidener Hardware effizient auf der CPU zu laufen."
            ),
            zh=(
                "llama.cpp 推理所用的硬件设备。'CPU' 将模型完全加载至内存运行，"
                "无需 GPU。"
                "SmolLM2 模型体积小巧，即使在普通硬件上也能高效地在 CPU 上运行。"
            ),
        ),
        alias=MultilingualString(
            en="Device", es="Dispositivo", pt="Dispositivo", de="Gerät", zh="设备"
        ),
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
        de="SmolLM-Modell",
        zh="SmolLM 模型",
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
        de=(
            "SmolLM2 ist eine Familie kompakter instruktionsoptimierter Sprachmodelle "
            "von Hugging Face, im GGUF-Format für effiziente CPU- und GPU-Inferenz "
            "über llama.cpp geladen. Für Deployment auf Endgeräten und Edge-Systemen "
            "konzipiert, erzielt SmolLM2 starke Benchmark-Ergebnisse mit sehr wenigen "
            "Parametern. Die 360M-Variante benötigt weniger als 300 MB RAM und ist "
            "ideal für ressourcenbeschränkte Umgebungen. Verfügbar in den Varianten "
            "360M und 1,7B. Modelle unter https://huggingface.co/HuggingFaceTB."
        ),
        zh=(
            "SmolLM2 是 Hugging Face 推出的紧凑型指令微调语言模型系列，"
            "以 GGUF 格式加载，通过 llama.cpp 库高效推理。"
            "专为端侧和边缘部署设计，提供 360M 和 1.7B 两种规格。"
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
