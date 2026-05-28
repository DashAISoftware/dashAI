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
    """Schema for MixtralModel hyperparameters.

    Configures the checkpoint variant (with optional GGUF filename override),
    generation length, sampling temperature, frequency penalty, context window,
    and target device for Mixtral Sparse-MoE models loaded via
    ``llama-cpp-python``.
    """

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
            pt=(
                "O checkpoint Mixtral Instruct a carregar em formato GGUF. "
                "'Mixtral-8x7B-Instruct-v0.1' é um modelo de Mistura Esparsa de "
                "Especialistas (SMoE) com 8 redes especialistas de 7B parâmetros cada, "
                "ativando 2 especialistas por token. Alcança qualidade comparável a "
                "modelos densos maiores sendo mais eficiente na inferência. "
                "Aviso: este modelo requer ~26 GB de RAM para a "
                "quantização Q4_K_M."
            ),
            de=(
                "Der im GGUF-Format zu ladende Mixtral Instruct-Checkpoint. "
                "'Mixtral-8x7B-Instruct-v0.1' ist ein Sparse Mixture-of-Experts "
                "(SMoE)-Modell mit 8 Expertennetzwerken à 7B Parameter, das 2 "
                "Experten pro Token aktiviert. Es erreicht eine mit größeren dichten "
                "Modellen vergleichbare Qualität bei effizienterer Inferenz. "
                "Warnung: dieses Modell benötigt ~26 GB RAM für die "
                "Q4_K_M-Quantisierung."
            ),
        ),
        alias=MultilingualString(
            en="Model name",
            es="Nombre del modelo",
            pt="Nome do modelo",
            de="Modellname",
        ),
    )  # type: ignore

    filename: schema_field(
        enum_field(
            enum=[
                "Mixtral-8x7B-Instruct-v0.1.Q2_K.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q3_K_M.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q4_0.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q4_K_M.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q5_0.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q5_K_M.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q6_K.gguf",
                "Mixtral-8x7B-Instruct-v0.1.Q8_0.gguf",
            ]
        ),
        placeholder="Mixtral-8x7B-Instruct-v0.1.Q2_K.gguf",
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
            pt=(
                "O arquivo GGUF específico a carregar para o modelo Mixtral. Os "
                "diferentes níveis de quantização (Q2_K, Q3_K_M, Q4_0, Q4_K_M, "
                "Q5_0, Q5_K_M, Q6_K, Q8_0) representam vários compromissos entre "
                "tamanho do modelo, velocidade de inferência e qualidade de saída. "
                "Q4_K_M é uma escolha popular para equilibrar desempenho e "
                "requisitos de recursos."
            ),
            de=(
                "Die zu ladende spezifische GGUF-Datei für das Mixtral-Modell. "
                "Die verschiedenen Quantisierungsstufen (Q2_K, Q3_K_M, Q4_0, Q4_K_M, "
                "Q5_0, Q5_K_M, Q6_K, Q8_0) stellen verschiedene Kompromisse zwischen "
                "Modellgröße, Inferenzgeschwindigkeit und Ausgabequalität dar. "
                "Q4_K_M ist eine beliebte Wahl für ausgewogene Leistung und "
                "Ressourcenbedarf."
            ),
        ),
        alias=MultilingualString(
            en="Filename", es="Nombre del archivo", pt="Nome do archivo", de="Dateiname"
        ),
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
            pt=(
                "Número máximo de tokens novos que o modelo gerará por resposta. "
                "Aproximadamente 1 token ≈ 0.75 palavras em português. Use 100-200 "
                "para respostas curtas, 500-1000 para explicações detalhadas "
                "ou código."
            ),
            de=(
                "Maximale Anzahl neuer Token, die das Modell pro Antwort erzeugt. "
                "Ungefähr 1 Token ≈ 0,75 englische Wörter. 100-200 für kurze "
                "Antworten, 500-1000 für ausführliche Erklärungen oder Code."
            ),
        ),
        alias=MultilingualString(
            en="Max tokens",
            es="Tokens máximos",
            pt="Tokens máximos",
            de="Maximale neue Token",
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
                "Temperatura de amostragem que controla a aleatoriedade "
                "(intervalo 0.0-1.0). "
                "Em 0.0 as saídas são determinísticas. Em torno de 0.7 equilibra "
                "qualidade e criatividade."
            ),
            de=(
                "Stichprobentemperatur zur Steuerung der Ausgabezufälligkeit (0.0-1.0)."
                "Bei 0.0 sind die Ausgaben deterministisch. Um 0.7 balanciert "
                "Qualität und Kreativität."
            ),
        ),
        alias=MultilingualString(
            en="Temperature", es="Temperatura", pt="Temperatura", de="Temperatur"
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
        ),
        alias=MultilingualString(
            en="Frequency penalty",
            es="Penalización de frecuencia",
            pt="Penalização de frequência",
            de="Häufigkeitsstrafe",
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
            pt=(
                "Orçamento total de tokens por passagem, incluindo prompt e "
                "resposta. Mixtral 8x7B suporta até 32K tokens nativamente."
            ),
            de=(
                "Gesamtes Token-Budget für einen einzelnen Vorwärtsdurchlauf, "
                "einschließlich Eingabe-Prompt und generierter Antwort. "
                "Mixtral 8x7B unterstützt nativ bis zu 32K Token."
            ),
        ),
        alias=MultilingualString(
            en="Context window",
            es="Ventana de contexto",
            pt="Janela de contexto",
            de="Kontextfenster",
        ),
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
            pt=(
                "Dispositivo de hardware para inferência com llama.cpp. 'CPU' executa "
                "o modelo na RAM. Uma opção de GPU descarrega todas as camadas para "
                "inferência mais rápida. Devido ao grande tamanho do Mixtral, "
                "recomenda-se "
                "uma GPU com pelo menos 24 GB de VRAM para descarregamento completo."
            ),
            de=(
                "Hardware-Gerät für die llama.cpp-Inferenz. 'CPU' führt das Modell "
                "im RAM aus. Eine GPU-Option lagert alle Schichten für schnellere "
                "Inferenz aus. Aufgrund der Größe von Mixtral wird eine GPU mit "
                "mindestens 24 GB VRAM für vollständiges GPU-Offloading empfohlen."
            ),
        ),
        alias=MultilingualString(
            en="Device", es="Dispositivo", pt="Dispositivo", de="Gerät"
        ),
    )  # type: ignore


class MixtralModel(TextToTextGenerationTaskModel):
    """Mixtral Sparse Mixture-of-Experts (SMoE) model for text generation via llama.cpp.

    Mixtral 8x7B is a transformer language model with 8 expert feed-forward
    networks per layer; only 2 experts are activated per token, giving it the
    computational cost of a 12B-parameter dense model while retaining capacity
    equivalent to a 47B model. It matches or surpasses Llama 2 70B and GPT-3.5
    on most benchmarks.

    Models are loaded as GGUF quantized checkpoints via ``llama-cpp-python``.
    The Q4_K_M quantization requires approximately 26 GB of RAM.

    References
    ----------
    - [1] Jiang et al. (2024) "Mixtral of Experts" https://arxiv.org/abs/2401.04088
    - [2] https://huggingface.co/mistralai/Mixtral-8x7B-Instruct-v0.1
    """

    SCHEMA = MixtralSchema
    COLOR: str = "#4a148c"
    DISPLAY_NAME: str = MultilingualString(
        en="Mixtral Model",
        es="Modelo Mixtral",
        pt="Modelo Mixtral",
        de="Mixtral-Modell",
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
        pt=(
            "Mixtral 8x7B Instruct, um modelo de Mistura Esparsa de Especialistas "
            "(SMoE) da Mistral AI, carregado em formato GGUF para inferência eficiente "
            "em CPU e GPU via biblioteca llama.cpp. O modelo usa 8 redes especialistas "
            "de 7B parâmetros cada, ativando apenas 2 especialistas por token, "
            "alcançando desempenho comparável a modelos densos maiores sendo mais "
            "eficiente na inferência. Suporta conversa multi-turno, raciocínio, "
            "programação e geração de texto em geral. Aviso: requer ~26 GB de RAM para "
            "a quantização Q4_K_M. Modelo disponível em "
            "https://huggingface.co/mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF."
        ),
        de=(
            "Mixtral 8x7B Instruct, ein Sparse Mixture-of-Experts (SMoE)-Modell von "
            "Mistral AI, im GGUF-Format für effiziente CPU- und GPU-Inferenz über die "
            "llama.cpp-Bibliothek geladen. Das Modell nutzt 8 Expertennetzwerke à 7B "
            "Parameter und aktiviert nur 2 Experten pro Token, was mit größeren dichten"
            "Modellen vergleichbare Leistung bei effizienterer Inferenz ermöglicht. "
            "Unterstützt Mehrfachdialog, Schlussfolgerung, Programmierung und "
            "allgemeine "
            "Textgenerierung. Warnung: erfordert ~26 GB RAM für die "
            "Q4_K_M-Quantisierung. "
            "Modell unter "
            "https://huggingface.co/mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF."
        ),
    )

    def __init__(self, **kwargs):
        """Download and initialise a Mixtral 8x7B Instruct GGUF model via llama.cpp.

        The model weights are fetched from HuggingFace Hub using
        ``Llama.from_pretrained`` and kept in memory for repeated calls to
        ``generate``.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace repo ID for the GGUF checkpoint.
                Defaults to
                ``"mradermacher/Mixtral-8x7B-Instruct-v0.1-GGUF"``.
            filename : str, optional
                Specific GGUF quantization file to load (e.g.
                ``"mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"``). Defaults to
                the Q2_K variant. Higher quantizations use more RAM but
                produce better output quality.
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
