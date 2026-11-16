"""Qwen GGUF checkpoint subclasses for DashAI."""

from typing import Any, Dict

from DashAI.back.core.schema_fields import bool_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.hugging_face.gguf_text_generation_base import (
    GGUFTextGenerationModel,
    GGUFTextGenerationSchema,
)


class Qwen3GGUFTextGenerationSchema(GGUFTextGenerationSchema):
    """Qwen3 GGUF schema, adding the optional reasoning toggle."""

    enable_thinking: schema_field(
        bool_field(),
        False,
        description=MultilingualString(
            en=(
                "Emit a reasoning trace before the answer. It is off by default "
                "so RAG function calls stay within their token budget."
            ),
            es=(
                "Emitir un razonamiento antes de la respuesta. Está desactivado "
                "por defecto para que las llamadas RAG quepan en su presupuesto."
            ),
            pt=(
                "Emitir um raciocínio antes da resposta. Fica desativado por "
                "padrão para que as chamadas RAG caibam no orçamento de tokens."
            ),
            de=(
                "Vor der Antwort einen Denkverlauf ausgeben. Standardmäßig aus, "
                "damit RAG-Aufrufe im Token-Budget bleiben."
            ),
            zh="在回答前输出推理过程。默认关闭，以便 RAG 函数调用不超过词元预算。",
        ),
        alias=MultilingualString(
            en="Enable thinking",
            es="Activar razonamiento",
            pt="Ativar raciocínio",
            de="Denken aktivieren",
            zh="启用思考",
        ),
    )  # type: ignore


class Qwen25_05BInstruct(GGUFTextGenerationModel):  # noqa: N801
    """Qwen 2.5 0.5B Instruct GGUF checkpoint (Q8_0 quantization).

    A compact 500M-parameter instruction-tuned model from Alibaba Cloud,
    well suited for lightweight CPU inference. Weights are stored locally
    after a one-time download from HuggingFace.

    References
    ----------
    - Qwen Team (2024). "Qwen2.5 Technical Report."
      https://arxiv.org/abs/2412.15115
    - https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
    """

    REPO_ID = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
    GGUF_PATTERN = "*8_0.gguf"
    DOWNLOAD_SIZE_BYTES = 675710816
    SCHEMA = GGUFTextGenerationSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME = MultilingualString(
        en="Qwen2.5 0.5B Instruct",
        es="Qwen2.5 0.5B Instruct",
        pt="Qwen2.5 0.5B Instruct",
        de="Qwen2.5 0.5B Instruct",
        zh="Qwen2.5 0.5B Instruct",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Qwen 2.5 0.5B Instruct is a 500M-parameter instruction-tuned "
            "language model by Alibaba Cloud, loaded as a Q8_0 GGUF for "
            "efficient CPU inference. It is the fastest and most "
            "memory-efficient Qwen 2.5 variant in DashAI, ideal for rapid "
            "prototyping or devices with limited RAM. Model available at "
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF."
        ),
        es=(
            "Qwen 2.5 0.5B Instruct es un modelo de 500M parámetros ajustado "
            "para instrucciones por Alibaba Cloud, cargado como GGUF Q8_0 "
            "para inferencia eficiente en CPU. Es la variante Qwen 2.5 más "
            "rápida y con menor uso de memoria en DashAI, ideal para "
            "prototipado rápido o dispositivos con RAM limitada."
        ),
        pt=(
            "Qwen 2.5 0.5B Instruct é um modelo de 500M parâmetros ajustado "
            "para instruções pela Alibaba Cloud, carregado como GGUF Q8_0 "
            "para inferência eficiente em CPU. É a variante Qwen 2.5 mais "
            "rápida e com menor uso de memória no DashAI, ideal para "
            "prototipagem rápida ou dispositivos com RAM limitada."
        ),
        de=(
            "Qwen 2.5 0.5B Instruct ist ein 500M-Parameter-Instruktionsmodell "
            "von Alibaba Cloud, als Q8_0-GGUF für effiziente CPU-Inferenz "
            "geladen. Es ist die schnellste und speichereffizienteste "
            "Qwen-2.5-Variante in DashAI, ideal für schnelles Prototyping "
            "oder Geräte mit begrenztem RAM."
        ),
        zh=(
            "Qwen 2.5 0.5B Instruct 是阿里云推出的 5 亿参数指令微调语言模型，"
            "以 Q8_0 GGUF 格式加载，支持高效 CPU 推理。"
            "这是 DashAI 中速度最快、内存占用最低的 Qwen 2.5 变体，"
            "非常适合快速原型开发或内存受限的设备。"
        ),
    )


class Qwen25_15BInstruct(GGUFTextGenerationModel):  # noqa: N801
    """Qwen 2.5 1.5B Instruct GGUF checkpoint (Q8_0 quantization).

    A 1.5B-parameter instruction-tuned model from Alibaba Cloud that offers
    higher response quality than the 0.5B variant while still running on CPU.
    Weights are stored locally after a one-time download from HuggingFace.

    References
    ----------
    - Qwen Team (2024). "Qwen2.5 Technical Report."
      https://arxiv.org/abs/2412.15115
    - https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
    """

    REPO_ID = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
    GGUF_PATTERN = "*8_0.gguf"
    DOWNLOAD_SIZE_BYTES = 1894532128
    SCHEMA = GGUFTextGenerationSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME = MultilingualString(
        en="Qwen2.5 1.5B Instruct",
        es="Qwen2.5 1.5B Instruct",
        pt="Qwen2.5 1.5B Instruct",
        de="Qwen2.5 1.5B Instruct",
        zh="Qwen2.5 1.5B Instruct",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Qwen 2.5 1.5B Instruct is a 1.5B-parameter instruction-tuned "
            "language model by Alibaba Cloud, loaded as a Q8_0 GGUF for "
            "efficient CPU inference. It provides stronger reasoning and "
            "generation quality than the 0.5B variant at the cost of slightly "
            "more memory. Model available at "
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF."
        ),
        es=(
            "Qwen 2.5 1.5B Instruct es un modelo de 1.5B parámetros ajustado "
            "para instrucciones por Alibaba Cloud, cargado como GGUF Q8_0 "
            "para inferencia eficiente en CPU. Ofrece mayor capacidad de "
            "razonamiento y calidad de generación que la variante de 0.5B a "
            "costa de un poco más de memoria."
        ),
        pt=(
            "Qwen 2.5 1.5B Instruct é um modelo de 1.5B parâmetros ajustado "
            "para instruções pela Alibaba Cloud, carregado como GGUF Q8_0 "
            "para inferência eficiente em CPU. Oferece melhor raciocínio e "
            "qualidade de geração que a variante de 0.5B ao custo de um pouco "
            "mais de memória."
        ),
        de=(
            "Qwen 2.5 1.5B Instruct ist ein 1,5B-Parameter-Instruktionsmodell "
            "von Alibaba Cloud, als Q8_0-GGUF für effiziente CPU-Inferenz "
            "geladen. Es bietet besseres Schlussfolgern und "
            "Generierungsqualität als die 0,5B-Variante, benötigt jedoch "
            "etwas mehr Speicher."
        ),
        zh=(
            "Qwen 2.5 1.5B Instruct 是阿里云推出的 15 亿参数指令微调语言模型，"
            "以 Q8_0 GGUF 格式加载，支持高效 CPU 推理。"
            "与 0.5B 变体相比，它具有更强的推理能力和生成质量，但需要稍多的内存。"
        ),
    )


class Qwen25_3BInstruct(GGUFTextGenerationModel):  # noqa: N801
    """Qwen 2.5 3B Instruct GGUF checkpoint (Q8_0 quantization).

    A 3B-parameter instruction-tuned model from Alibaba Cloud that offers
    higher response quality than the 1.5B variant while still running on CPU.
    Weights are stored locally after a one-time download from HuggingFace.

    References
    ----------
    - Qwen Team (2024). "Qwen2.5 Technical Report."
      https://arxiv.org/abs/2412.15115
    - https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
    """

    REPO_ID = "Qwen/Qwen2.5-3B-Instruct-GGUF"
    GGUF_PATTERN = "*8_0.gguf"
    DOWNLOAD_SIZE_BYTES = 3616088480
    SCHEMA = GGUFTextGenerationSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME = MultilingualString(
        en="Qwen2.5 3B Instruct",
        es="Qwen2.5 3B Instruct",
        pt="Qwen2.5 3B Instruct",
        de="Qwen2.5 3B Instruct",
        zh="Qwen2.5 3B Instruct",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Qwen 2.5 3B Instruct is a 3B-parameter instruction-tuned "
            "language model by Alibaba Cloud, loaded as a Q8_0 GGUF for "
            "efficient CPU inference. It provides stronger reasoning and "
            "generation quality than the 1.5B variant at the cost of slightly "
            "more memory. Model available at "
            "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF."
        ),
        es=(
            "Qwen 2.5 3B Instruct es un modelo de 3B parámetros ajustado "
            "para instrucciones por Alibaba Cloud, cargado como GGUF Q8_0 "
            "para inferencia eficiente en CPU. Ofrece mayor capacidad de "
            "razonamiento y calidad de generación que la variante de 1.5B a "
            "costa de un poco más de memoria."
        ),
        pt=(
            "Qwen 2.5 3B Instruct é um modelo de 3B parâmetros ajustado "
            "para instruções pela Alibaba Cloud, carregado como GGUF Q8_0 "
            "para inferência eficiente em CPU. Oferece melhor raciocínio e "
            "qualidade de geração que a variante de 1.5B ao custo de um pouco "
            "mais de memória."
        ),
        de=(
            "Qwen 2.5 3B Instruct ist ein 3B-Parameter-Instruktionsmodell "
            "von Alibaba Cloud, als Q8_0-GGUF für effiziente CPU-Inferenz "
            "geladen. Es bietet besseres Schlussfolgern und "
            "Generierungsqualität als die 1,5B-Variante, benötigt jedoch "
            "etwas mehr Speicher."
        ),
        zh=(
            "Qwen 2.5 3B Instruct 是阿里云推出的 30 亿参数指令微调语言模型，"
            "以 Q8_0 GGUF 格式加载，支持高效 CPU 推理。"
            "与 1.5B 变体相比，它具有更强的推理能力和生成质量，但需要稍多的内存。"
            "模型地址：https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF。"
        ),
    )


class Qwen25_7BInstruct(GGUFTextGenerationModel):  # noqa: N801
    """Qwen 2.5 7B Instruct GGUF checkpoint (Q8_0 quantization).

    A 7B-parameter instruction-tuned model from Alibaba Cloud that offers
    higher response quality than the 3B variant while still running on CPU.
    Weights are stored locally after a one-time download from HuggingFace.

    References
    ----------
    - Qwen Team (2024). "Qwen2.5 Technical Report."
      https://arxiv.org/abs/2412.15115
    - https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
    """

    REPO_ID = "Qwen/Qwen2.5-7B-Instruct-GGUF"
    # The 7B Q8_0 checkpoint ships split across three shards named
    # ``qwen2.5-7b-instruct-q8_0-0000N-of-00003.gguf``; the leading ``*`` is
    # required for the pattern to match the repo file names (and their local
    # paths after ``snapshot_download``).
    GGUF_PATTERN = "*-q8_0*.gguf"
    DOWNLOAD_SIZE_BYTES = 8098525408
    SCHEMA = GGUFTextGenerationSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME = MultilingualString(
        en="Qwen2.5 7B Instruct",
        es="Qwen2.5 7B Instruct",
        pt="Qwen2.5 7B Instruct",
        de="Qwen2.5 7B Instruct",
        zh="Qwen2.5 7B Instruct",
    )


class Qwen3_8B(GGUFTextGenerationModel):  # noqa: N801
    """Qwen3 8B GGUF checkpoint (Q6_K quantization).

    An 8B-parameter Qwen3 model distributed by Qwen in GGUF format. The Q6_K
    checkpoint offers higher weight precision than smaller quantizations, at
    the cost of a larger download and runtime memory requirement.

    The checkpoint exposes an ``enable_thinking`` schema parameter, off by
    default because DashAI uses it as the RAG function-calling model. When off,
    the Qwen3 chat template appends an empty think block, so the model answers
    or emits its tool call without a reasoning trace. Turning it on restores the
    template's normal reasoning output for any chat use of this checkpoint.

    References
    ----------
    - Qwen Team (2025). "Qwen3 Technical Report."
      https://arxiv.org/abs/2505.09388
    - https://huggingface.co/Qwen/Qwen3-8B-GGUF
    """

    REPO_ID = "Qwen/Qwen3-8B-GGUF"
    GGUF_PATTERN = "Qwen3-8B-Q6_K.gguf"
    DOWNLOAD_SIZE_BYTES = 6_725_899_040
    SCHEMA = Qwen3GGUFTextGenerationSchema
    COLOR: str = "#2e7d32"
    DISPLAY_NAME = MultilingualString(
        en="Qwen3 8B Q6_K",
        es="Qwen3 8B Q6_K",
        pt="Qwen3 8B Q6_K",
        de="Qwen3 8B Q6_K",
        zh="Qwen3 8B Q6_K",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Qwen3 8B is an 8B-parameter language model from Qwen, loaded from "
            "the Q6_K GGUF checkpoint. This higher-precision quantization uses "
            "about 6.73 GB for the model file and requires additional memory for "
            "inference. Reasoning output is controlled by the Enable thinking "
            "parameter and is off by default. Model available at "
            "https://huggingface.co/Qwen/Qwen3-8B-GGUF."
        ),
        es=(
            "Qwen3 8B es un modelo de lenguaje de 8B parámetros de Qwen, cargado "
            "desde el checkpoint GGUF Q6_K. Esta cuantización de mayor precisión "
            "ocupa unos 6,73 GB en el archivo del modelo y requiere memoria "
            "adicional para la inferencia. El razonamiento se controla con el "
            "parámetro «Activar razonamiento» y está desactivado por defecto. "
            "Disponible en https://huggingface.co/Qwen/Qwen3-8B-GGUF."
        ),
        pt=(
            "Qwen3 8B é um modelo de linguagem de 8B parâmetros da Qwen, carregado "
            "a partir do checkpoint GGUF Q6_K. Esta quantização de maior precisão "
            "ocupa cerca de 6,73 GB no arquivo do modelo e requer memória adicional "
            "para inferência. O raciocínio é controlado pelo parâmetro "
            "«Ativar raciocínio» e fica desativado por padrão. Disponível em "
            "https://huggingface.co/Qwen/Qwen3-8B-GGUF."
        ),
        de=(
            "Qwen3 8B ist ein 8B-Sprachmodell von Qwen, geladen aus dem "
            "Q6_K-GGUF-Checkpoint. Diese höherpräzise Quantisierung benötigt etwa "
            "6,73 GB für die Modelldatei sowie zusätzlichen Speicher für die "
            "Inferenz. Die Denk-Ausgabe lässt sich über den Parameter "
            "„Denken aktivieren“ steuern und ist standardmäßig aus. Verfügbar unter "
            "https://huggingface.co/Qwen/Qwen3-8B-GGUF."
        ),
        zh=(
            "Qwen3 8B 是 Qwen 推出的 80 亿参数语言模型，使用 Q6_K GGUF 检查点。"
            "这种精度较高的量化模型文件约占 6.73 GB，推理时还需要额外内存。"
            "思考输出由“启用思考”参数控制，默认关闭。"
            "模型地址：https://huggingface.co/Qwen/Qwen3-8B-GGUF。"
        ),
    )

    def _resolve_chat_template_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Map the ``enable_thinking`` schema parameter to a template variable.

        Parameters
        ----------
        kwargs : Dict[str, Any]
            Validated model parameters not consumed by the base class.

        Returns
        -------
        Dict[str, Any]
            The Qwen3 chat-template variable controlling the think block.

        Raises
        ------
        KeyError
            If the validated schema did not provide ``enable_thinking``.
        """
        return {"enable_thinking": kwargs.pop("enable_thinking")}
