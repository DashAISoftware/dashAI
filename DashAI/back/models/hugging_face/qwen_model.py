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
    """Schema for QwenModel hyperparameters.

    Configures the Qwen 2.5 Instruct checkpoint variant (0.5B or 1.5B), generation
    length, sampling temperature, frequency penalty, context window, and target
    device. The GGUF filename is selected automatically using a Q8_0 quantization
    pattern; no manual filename override is exposed.
    """

    model_name: schema_field(
        enum_field(
            enum=[
                "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                # "Qwen/Qwen3-4B-GGUF", This one is not working on llama-cpp 0.3.4
                "Qwen/Qwen2.5-3B-Instruct-GGUF",
                "Qwen/Qwen2.5-7B-Instruct-GGUF",
                "Qwen/Qwen2.5-14B-Instruct-GGUF",
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
            pt=(
                "O checkpoint Qwen 2.5 Instruct a carregar em formato GGUF. "
                "'0.5B' (500M parâmetros) é mais rápido e usa menos memória, "
                "adequado para tarefas leves em CPU. '1.5B' (1.5B parâmetros) "
                "é mais capaz e produz respostas de maior qualidade ao custo de "
                "mais memória e inferência levemente mais lenta."
            ),
            de=(
                "Der im GGUF-Format zu ladende Qwen 2.5 Instruct-Checkpoint. "
                "'0.5B' (500M Parameter) ist schneller und verbraucht weniger Speicher,"
                "geeignet für leichte CPU-Aufgaben. '1.5B' (1,5B Parameter) ist "
                "leistungsfähiger und liefert qualitativ hochwertigere Antworten "
                "auf Kosten von mehr Speicher und etwas langsamerer Inferenz."
            ),
            zh=(
                "要加载的 Qwen 2.5 Instruct GGUF 格式检查点。"
                "'0.5B'（5亿参数）速度更快、内存占用更少，适合 CPU 上的轻量级任务。"
                "'1.5B'（15亿参数）能力更强，生成质量更高，但需要更多内存且推理速度略慢。"
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
            pt=(
                "Número máximo de tokens novos que o modelo gerará por resposta. "
                "Aproximadamente 1 token ≈ 0.75 palavras em português. Use 100-200 "
                "para respostas curtas, 500-1000 para explicações detalhadas ou "
                "código. Não deve exceder a janela de contexto menos o comprimento "
                "do prompt."
            ),
            de=(
                "Maximale Anzahl neuer Token, die das Modell pro Antwort erzeugt. "
                "Ungefähr 1 Token ≈ 0,75 englische Wörter. 100-200 für kurze "
                "Antworten, 500-1000 für ausführliche Erklärungen oder Code. "
                "Darf die Kontextfenstergröße abzüglich der Prompt-Länge nicht "
                "überschreiten."
            ),
            zh=(
                "模型每次响应生成的最大新 token 数量。"
                "大约 1 token 约等于 0.75 个英文单词。短答案设为 100-200，"
                "详细说明或代码设为 500-1000。不得超过上下文窗口减去提示词长度的值。"
            ),
        ),
        alias=MultilingualString(
            en="Max tokens",
            es="Tokens máximos",
            pt="Tokens máximos",
            de="Maximale neue Token",
            zh="最大 token 数",
        ),
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
            pt=(
                "Temperatura de amostragem que controla a aleatoriedade da saída "
                "(intervalo 0.0-1.0). Em 0.0 o modelo sempre escolhe o token mais "
                "provável (greedy, totalmente determinístico). Em torno de 0.7 é "
                "um bom equilíbrio para tarefas conversacionais. Em 1.0 as "
                "saídas são maximamente variadas e imprevisíveis."
            ),
            de=(
                "Stichprobentemperatur zur Steuerung der Ausgabezufälligkeit (0.0-1.0)."
                "Bei 0.0 wählt das Modell stets den wahrscheinlichsten Token (greedy, "
                "vollständig deterministisch). Um 0.7 ist ein gutes Gleichgewicht für "
                "Konversationsaufgaben. Bei 1.0 sind Ausgaben maximal variiert und "
                "unvorhersehbar."
            ),
            zh=(
                "控制输出随机性的采样温度（范围 0.0-1.0）。"
                "0.0 时模型始终选择最可能的 token（贪心，完全确定性）。"
                "0.7 左右是对话任务的良好平衡点。1.0 时输出变化最大，不可预测。"
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
            pt=(
                "Penaliza os tokens que já apareceram na saída com base em "
                "sua frequência (intervalo 0.0-2.0). Em 0.0 não há penalização e o "
                "modelo pode se repetir. Valores em torno de 0.1-0.3 desestimulam "
                "suavemente a repetição. Valores altos (1.5+) impedem fortemente a "
                "reutilização de palavras, o que pode produzir texto menos coerente."
            ),
            de=(
                "Bestraft Token, die bereits in der Ausgabe erschienen sind, "
                "basierend auf ihrer Häufigkeit (0.0-2.0). Bei 0.0 gibt es keine "
                "Strafe und das Modell kann sich wiederholen. Werte um 0.1-0.3 "
                "hemmen Wiederholungen sanft. Hohe Werte (1.5+) verhindern die "
                "Wiederverwendung von Wörtern stark, was zu weniger kohärentem Text "
                "führen kann."
            ),
            zh=(
                "根据 token 在输出中出现的频率对其进行惩罚（范围 0.0-2.0）。"
                "0.0 时无惩罚，模型可能重复输出。0.1-0.3 左右可轻微抑制重复。"
                "高值（1.5+）会强烈阻止任何词的复用，可能导致文本连贯性下降。"
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
            pt=(
                "Orçamento total de tokens para uma única passagem, incluindo tanto "
                "o prompt de entrada quanto a resposta gerada. Valores maiores "
                "permitem conversas mais longas mas consomem mais RAM/VRAM. "
                "Qwen 2.5 suporta até 32768 tokens nativamente; mantenha "
                "este valor igual ou abaixo desse limite."
            ),
            de=(
                "Gesamtes Token-Budget für einen einzelnen Vorwärtsdurchlauf, "
                "einschließlich Eingabe-Prompt und generierter Antwort. Größere Werte "
                "ermöglichen längere Gespräche, verbrauchen jedoch mehr RAM/VRAM. "
                "Qwen 2.5 unterstützt nativ bis zu 32768 Token; halten Sie "
                "diesen Wert gleich oder unter diesem Limit."
            ),
            zh=(
                "单次前向传播的总 token 预算，包含输入提示词和生成的响应。"
                "较大的值允许更长的对话，但会消耗更多 RAM/VRAM。"
                "Qwen 2.5 原生支持最多 32768 个 token，请保持此值不超过该限制。"
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
            pt=(
                "Dispositivo de hardware para inferência com llama.cpp. 'CPU' "
                "executa o modelo completamente na RAM sem requisito de GPU. "
                "Selecionar uma opção de GPU descarrega todas as camadas para "
                "inferência mais rápida, definindo n_gpu_layers=-1 para que "
                "cada camada do transformer seja acelerada por GPU."
            ),
            de=(
                "Hardware-Gerät für die llama.cpp-Inferenz. 'CPU' führt das Modell "
                "vollständig im RAM ohne GPU-Anforderung aus. Eine GPU-Option "
                "lagert alle Schichten für schnellere Inferenz aus und setzt "
                "n_gpu_layers=-1, damit jede Transformer-Schicht GPU-beschleunigt wird."
            ),
            zh=(
                "llama.cpp 推理所使用的硬件设备。'CPU' 完全在内存中运行模型，无需 GPU。"
                "选择 GPU 选项会将所有层卸载以加快推理速度，"
                "并设置 n_gpu_layers=-1 使每个 Transformer 层均由 GPU 加速。"
            ),
        ),
        alias=MultilingualString(
            en="Device",
            es="Dispositivo",
            pt="Dispositivo",
            de="Gerät",
            zh="设备",
        ),
    )  # type: ignore


class QwenModel(TextToTextGenerationTaskModel):
    """Qwen 2.5 Instruct model for efficient text generation via llama.cpp.

    Qwen 2.5 is a series of dense transformer language models from Alibaba Cloud,
    spanning 0.5B to 72B parameters. The DashAI integration exposes the 0.5B and
    1.5B Instruct variants, which run comfortably on CPU. Both are trained on 18
    trillion tokens with improved coding, mathematics, and multilingual capability
    over Qwen 2.

    Models are loaded as GGUF Q8_0 quantized checkpoints via ``llama-cpp-python``;
    the quantization file is selected automatically from the HuggingFace repo.

    References
    ----------
    - [1] Qwen Team (2024). "Qwen2.5 Technical Report." https://arxiv.org/abs/2412.15115
    - [2] https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
    """

    SCHEMA = QwenSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME: str = MultilingualString(
        en="Qwen Model",
        es="Modelo Qwen",
        pt="Modelo Qwen",
        de="Qwen-Modell",
        zh="Qwen 模型",
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
        pt=(
            "Qwen 2.5 é um modelo de linguagem grande ajustado para instruções "
            "pela Alibaba Cloud, carregado em formato GGUF para inferência eficiente "
            "em CPU e GPU via biblioteca llama.cpp. Suporta conversa multi-turno, "
            "raciocínio, programação e geração de texto em geral. Disponível nos "
            "tamanhos 0.5B e 1.5B parâmetros. Os modelos estão disponíveis em "
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF e "
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF."
        ),
        de=(
            "Qwen 2.5 ist ein instruktionsoptimiertes großes Sprachmodell von "
            "Alibaba Cloud, im GGUF-Format für effiziente CPU- und GPU-Inferenz über "
            "die llama.cpp-Bibliothek geladen. Unterstützt Mehrfachdialog, "
            "Schlussfolgerung, Programmierung und allgemeine Textgenerierung. "
            "Verfügbar in den Parametergrößen 0,5B und 1,5B. Modelle verfügbar unter "
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF und "
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF."
        ),
        zh=(
            "Qwen 2.5 是阿里云开发的指令微调大语言模型，"
            "以 GGUF 格式加载，通过 llama.cpp 库实现高效的 CPU 和 GPU 推理。"
            "支持多轮对话、推理、编程和通用文本生成。提供 0.5B 和 1.5B 参数规格。"
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise a Qwen 2.5 Instruct GGUF model via llama.cpp.

        The model weights are fetched from HuggingFace Hub using
        ``Llama.from_pretrained`` and kept in memory for repeated calls to
        ``generate``. The Q8_0 quantization file is always selected regardless
        of the chosen model variant.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace repo ID for the GGUF checkpoint.
                Defaults to ``"Qwen/Qwen2.5-1.5B-Instruct-GGUF"``.
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
                "llama-cpp-python is not installed. Please install it to use QwenModel."
            ) from e

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = "*q8_0.gguf"
        use_gpu = LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) >= 0

        try:
            self.model = Llama.from_pretrained(
                repo_id=self.model_name,
                filename=self.filename,
                verbose=True,
                n_ctx=self.n_ctx,
                n_gpu_layers=-1 if use_gpu else 0,
                main_gpu=LLAMA_DEVICE_TO_IDX.get(kwargs.get("device"))
                if use_gpu
                else 0,
            )
        except ValueError:
            # Fall back to Q2_K single-file quantization when Q8_0 is
            # not available (e.g. large models whose Q8_0 is multi-part).
            self.filename = "*q2_k.gguf"
            self.model = Llama.from_pretrained(
                repo_id=self.model_name,
                filename=self.filename,
                verbose=True,
                n_ctx=self.n_ctx,
                n_gpu_layers=-1 if use_gpu else 0,
                main_gpu=LLAMA_DEVICE_TO_IDX.get(kwargs.get("device"))
                if use_gpu
                else 0,
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
