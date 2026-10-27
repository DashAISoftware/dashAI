"""Default retrieval sufficiency evaluation prompt."""

from __future__ import annotations

from typing import Any

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.exceptions import RAGPromptTemplateError
from DashAI.back.models.RAG.prompts.evaluation.retrieval_sufficiency_prompt import (
    RetrievalSufficiencyPrompt,
)

TEMPLATES = {
    "en": (
        "You are a retrieval sufficiency evaluator for a Retrieval-Augmented "
        "Generation system. Decide whether the retrieved chunks are enough to "
        "answer the user message.\n"
        "\n"
        "This is evaluation round {round} of at most {max_rounds}.\n"
        "\n"
        "User message:\n"
        "{input}\n"
        "\n"
        "Documents: {documents.names}\n"
        "\n"
        "Document description: {documents.description}\n"
        "\n"
        "Current pool (each line shows its document_id and position):\n"
        "{chunks}\n"
        "\n"
        "Current pool size: {pool_size} chunks.\n"
        "\n"
        "Maximum retrievable chunks: {topk}.\n"
        "\n"
        "Free pool slots left: {remaining}.\n"
        "\n"
        "Retriever catalog: {retriever.description}\n"
        "\n"
        "The listed chunks ARE the current pool. Chunks not mentioned in the "
        "two chunk fields stay in the pool exactly as they are, except when the "
        "maximum capacity forces out older non-requested chunks; requested "
        "chunks take priority. Use the document chunk counts to choose valid "
        "positions.\n"
        "\n"
        "Respond by calling the function evaluate_retrieval_sufficiency with a "
        "single JSON object with this shape:\n"
        '{"sufficient": <true or false>, "call_retrievers": '
        '{"<retriever index>": <top_k>}, "request_specific_chunks": '
        '{"<document id>": [<chunk positions>]}, "discard_specific_chunks": '
        '{"<document id>": [<chunk positions>]}, '
        '"message": "<one short user-facing sentence>", '
        '"justification": "<one short rationale>"}\n'
        "\n"
        '- "sufficient" is required and says whether the retrieved chunks '
        "answer the user message.\n"
        '- "message" is optional: one short user-facing sentence in the same '
        "language as this prompt describing what you decided to do.\n"
        '- "justification" is optional: one short sentence in the same '
        "language as this prompt explaining why.\n"
        '- "call_retrievers" maps 1-based retriever indices from the retriever '
        "catalog to the number of chunks to retrieve from that retriever next. "
        "It is NOT mandatory every round. Indices must be at least 1. The "
        "per-retriever top_k is a size hint; the retriever enforces the hard pool "
        "cap.\n"
        '- "request_specific_chunks" maps document ids to chunk positions to '
        "ADD to the pool, even if no retriever returned them. Use the document "
        "chunk counts to choose valid positions.\n"
        '- "discard_specific_chunks" maps document ids to chunk positions to '
        "REMOVE from the pool.\n"
        '- "request_specific_chunks" and "discard_specific_chunks" are mutually '
        "exclusive for the same chunk: never list the same chunk in both.\n"
        "- Calling retrievers is NOT mandatory every round. Two valid cases:\n"
        "  1. The pool already has enough information for an accurate answer: "
        'set "sufficient": true and omit all actions.\n'
        "  2. The pool is insufficient: set "
        '"sufficient": false and request chunks, call retrievers, or both.\n'
        "- When asking for more, prefer requests within the remaining slots; "
        "the retriever enforces the hard pool cap.\n"
        "\n"
        "Invalid decisions are rejected and must be retried. Use only valid "
        "retriever indices and chunk positions, never request and discard the "
        "same chunk, leave free pool slots for the retrievers you call, and do "
        "not leave the pool empty unless you also call a retriever or request "
        "chunks.\n"
        "\n"
        "Respond with ONLY one JSON object, with no markdown fences and no "
        "extra text."
    ),
    "es": (
        "Eres un evaluador de suficiencia de recuperación para un sistema de "
        "Generación Aumentada por Recuperación. Decide si los fragmentos "
        "recuperados son suficientes para responder al mensaje del usuario.\n"
        "\n"
        "Esta es la ronda de evaluación {round} de como máximo {max_rounds}.\n"
        "\n"
        "Mensaje del usuario:\n"
        "{input}\n"
        "\n"
        "Documentos: {documents.names}\n"
        "\n"
        "Descripción de los documentos: {documents.description}\n"
        "\n"
        "Conjunto actual (cada línea muestra su document_id y posición):\n"
        "{chunks}\n"
        "\n"
        "Tamaño del conjunto actual: {pool_size} fragmentos.\n"
        "\n"
        "Máximo de fragmentos recuperables: {topk}.\n"
        "\n"
        "Espacios libres restantes: {remaining}.\n"
        "\n"
        "Catálogo de recuperadores: {retriever.description}\n"
        "\n"
        "Los fragmentos listados SON el conjunto actual. Los fragmentos no "
        "mencionados en los dos campos de fragmentos permanecen en el conjunto "
        "exactamente como están, salvo que la capacidad máxima expulse "
        "fragmentos antiguos no solicitados; los fragmentos solicitados tienen "
        "prioridad. Usa el número de fragmentos de cada documento para elegir "
        "posiciones válidas.\n"
        "\n"
        "Responde llamando a la función evaluate_retrieval_sufficiency con un "
        "único objeto JSON con esta forma:\n"
        '{"sufficient": <true o false>, "call_retrievers": '
        '{"<índice del recuperador>": <top_k>}, "request_specific_chunks": '
        '{"<id del documento>": [<posiciones de fragmentos>]}, '
        '"discard_specific_chunks": '
        '{"<id del documento>": [<posiciones de fragmentos>]}, '
        '"message": "<una frase breve para el usuario>", '
        '"justification": "<una justificación breve>"}\n'
        "\n"
        '- "sufficient" es obligatorio e indica si los fragmentos recuperados '
        "responden al mensaje del usuario.\n"
        '- "message" es opcional: una frase breve para el usuario, en el mismo '
        "idioma de este prompt, describiendo lo que decidiste hacer.\n"
        '- "justification" es opcional: una frase breve, en el mismo idioma de '
        "este prompt, explicando por qué.\n"
        '- "call_retrievers" asigna índices de recuperador basados en 1 del '
        "catálogo al número de fragmentos a recuperar de ese recuperador en la "
        "siguiente ronda. NO es obligatorio en cada ronda. Los índices deben "
        "ser al menos 1. El top_k por recuperador es una sugerencia de tamaño; "
        "el recuperador aplica el límite máximo del conjunto.\n"
        '- "request_specific_chunks" asigna ids de documento a posiciones de '
        "fragmento para AÑADIRLAS al conjunto, aunque ningún recuperador las "
        "haya devuelto. Usa el número de fragmentos de cada documento para "
        "elegir posiciones válidas.\n"
        '- "discard_specific_chunks" asigna ids de documento a posiciones de '
        "fragmento para ELIMINARLAS del conjunto.\n"
        '- "request_specific_chunks" y "discard_specific_chunks" son mutuamente '
        "excluyentes para el mismo fragmento: nunca listes el mismo fragmento "
        "en ambos.\n"
        "- Llamar a los recuperadores NO es obligatorio en cada ronda. Dos "
        "casos válidos:\n"
        "  1. El conjunto ya tiene información suficiente para una respuesta "
        'precisa: establece "sufficient": true y omite todas las acciones.\n'
        "  2. El conjunto es insuficiente: establece "
        '"sufficient": false y solicita fragmentos, llama a recuperadores, o '
        "ambos.\n"
        "- Cuando pidas más, prefiere solicitudes dentro de los espacios "
        "restantes; el recuperador impone el límite máximo del conjunto.\n"
        "\n"
        "Las decisiones inválidas se rechazan y deben reintentarse. Usa solo "
        "índices de recuperador y posiciones de fragmento válidos, nunca "
        "solicites y descartes el mismo fragmento, deja espacios libres para "
        "los recuperadores que llames y no dejes el conjunto vacío salvo que "
        "también llames a un recuperador o solicites fragmentos.\n"
        "\n"
        "Responde ÚNICAMENTE con un objeto JSON, sin bloques de código ni "
        "texto adicional."
    ),
    "pt": (
        "Você é um avaliador de suficiência de recuperação para um sistema de "
        "Geração Aumentada por Recuperação. Decida se os trechos recuperados "
        "são suficientes para responder à mensagem do usuário.\n"
        "\n"
        "Esta é a rodada de avaliação {round} de no máximo {max_rounds}.\n"
        "\n"
        "Mensagem do usuário:\n"
        "{input}\n"
        "\n"
        "Documentos: {documents.names}\n"
        "\n"
        "Descrição dos documentos: {documents.description}\n"
        "\n"
        "Conjunto atual (cada linha mostra seu document_id e posição):\n"
        "{chunks}\n"
        "\n"
        "Tamanho do conjunto atual: {pool_size} trechos.\n"
        "\n"
        "Máximo de trechos recuperáveis: {topk}.\n"
        "\n"
        "Espaços livres restantes: {remaining}.\n"
        "\n"
        "Catálogo de recuperadores: {retriever.description}\n"
        "\n"
        "Os trechos listados SÃO o conjunto atual. Os trechos não mencionados "
        "nos dois campos de trechos permanecem no conjunto exatamente como "
        "estão, exceto quando a capacidade máxima expulsa trechos antigos não "
        "solicitados; os trechos solicitados têm prioridade. Use o número de "
        "trechos de cada documento para escolher posições válidas.\n"
        "\n"
        "Responda chamando a função evaluate_retrieval_sufficiency com um "
        "único objeto JSON com esta forma:\n"
        '{"sufficient": <true ou false>, "call_retrievers": '
        '{"<índice do recuperador>": <top_k>}, "request_specific_chunks": '
        '{"<id do documento>": [<posições de trechos>]}, '
        '"discard_specific_chunks": '
        '{"<id do documento>": [<posições de trechos>]}, '
        '"message": "<uma frase breve para o usuário>", '
        '"justification": "<uma justificativa breve>"}\n'
        "\n"
        '- "sufficient" é obrigatório e indica se os trechos recuperados '
        "respondem à mensagem do usuário.\n"
        '- "message" é opcional: uma frase breve para o usuário, no mesmo '
        "idioma deste prompt, descrevendo o que você decidiu fazer.\n"
        '- "justification" é opcional: uma frase breve, no mesmo idioma deste '
        "prompt, explicando por quê.\n"
        '- "call_retrievers" mapeia índices de recuperador baseados em 1 do '
        "catálogo para o número de trechos a recuperar desse recuperador na "
        "próxima rodada. NÃO é obrigatório em cada rodada. Os índices devem ser "
        "pelo menos 1. O top_k por recuperador é uma sugestão de tamanho; o "
        "recuperador aplica o limite máximo do conjunto.\n"
        '- "request_specific_chunks" mapeia ids de documento para posições de '
        "trecho a ADICIONAR ao conjunto, mesmo que nenhum recuperador as tenha "
        "retornado. Use o número de trechos de cada documento para escolher "
        "posições válidas.\n"
        '- "discard_specific_chunks" mapeia ids de documento para posições de '
        "trecho a REMOVER do conjunto.\n"
        '- "request_specific_chunks" e "discard_specific_chunks" são mutuamente '
        "exclusivos para o mesmo trecho: nunca liste o mesmo trecho em ambos.\n"
        "- Chamar os recuperadores NÃO é obrigatório em cada rodada. Dois casos "
        "válidos:\n"
        "  1. O conjunto já tem informação suficiente para uma resposta "
        'precisa: defina "sufficient": true e omita todas as ações.\n'
        "  2. O conjunto é insuficiente: defina "
        '"sufficient": false e solicite trechos, chame recuperadores, ou '
        "ambos.\n"
        "- Ao pedir mais, prefira solicitações dentro dos espaços restantes; o "
        "recuperador impõe o limite máximo do conjunto.\n"
        "\n"
        "Decisões inválidas são rejeitadas e devem ser repetidas. Use apenas "
        "índices de recuperador e posições de trecho válidos, nunca solicite e "
        "descarte o mesmo trecho, deixe espaços livres para os recuperadores "
        "que chamar e não deixe o conjunto vazio a menos que também chame um "
        "recuperador ou solicite trechos.\n"
        "\n"
        "Responda APENAS com um objeto JSON, sem blocos de código e sem texto "
        "adicional."
    ),
}


class DefaultRetrievalSufficiencyPromptSchema(BaseSchema):
    """Schema for the default retrieval sufficiency prompt.

    Attributes:
        language: Language code for the generated instructions (en, es, pt).
        template: The prompt template string with placeholders.
    """

    language: schema_field(
        enum_field(enum=["en", "es", "pt"]),
        placeholder="en",
        description=MultilingualString(
            en="Language for the generated instructions.",
            es="Idioma de las instrucciones generadas.",
            pt="Idioma das instruções geradas.",
            de="Sprache der generierten Anweisungen.",
            zh="生成指令的语言。",
        ),
    )
    template: schema_field(
        string_field(),
        placeholder="",
        description="The prompt template with placeholders.",
    )


class DefaultRetrievalSufficiencyPrompt(RetrievalSufficiencyPrompt):
    """Default prompt template for judging retrieval sufficiency."""

    SCHEMA = DefaultRetrievalSufficiencyPromptSchema
    DESCRIPTION: str = MultilingualString(
        en="Default prompt template for deciding whether retrieved chunks are"
        " sufficient and which retrievers to consult next.",
        es="Plantilla de prompt predeterminada para decidir si los fragmentos"
        " recuperados son suficientes y qué recuperadores consultar después.",
        pt="Modelo de prompt padrão para decidir se os trechos recuperados são"
        " suficientes e quais recuperadores consultar em seguida.",
        de="Standard-Prompt-Vorlage, um zu entscheiden, ob abgerufene Fragmente"
        " ausreichen und welche Retriever als Nächstes zu konsultieren sind.",
        zh="用于判断已检索片段是否充分以及下一步咨询哪些检索器的默认提示词模板。",
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Default Retrieval Sufficiency Prompt",
        es="Prompt de Suficiencia de Recuperación Predeterminado",
        pt="Prompt de Suficiência de Recuperação Padrão",
        de="Standard-Retrieval-Suffizienz-Prompt",
        zh="默认检索充分性提示词",
    )

    required_placeholders = RetrievalSufficiencyPrompt.required_placeholders
    optional_placeholders = RetrievalSufficiencyPrompt.optional_placeholders

    metadata = {
        "name": "Default Retrieval Sufficiency Prompt",
        "description": "Default prompt template for deciding whether retrieved"
        " chunks are sufficient and which retrievers or chunks to fetch next.",
        "type": "evaluation",
        "technique": "sufficiency",
        "required_placeholders": required_placeholders,
        "optional_placeholders": optional_placeholders,
        "placeholder_descriptions": {
            "{input}": "The current user message the chunks must answer.",
            "{chunks}": (
                "The chunks under evaluation, one line per chunk carrying its "
                "document_id, position and text; a preformatted string is kept "
                "verbatim."
            ),
            "{pool_size}": (
                "Optional candidate pool size; the whole line disappears when "
                "it is not provided."
            ),
            "{topk}": (
                "Optional maximum number of retrievable chunks; the whole line "
                "disappears when it is not provided."
            ),
            "{round}": (
                "Optional 1-based evaluation round number; the whole line "
                "disappears when it is not provided."
            ),
            "{max_rounds}": (
                "Optional maximum number of evaluation rounds; the whole line "
                "disappears when it is not provided."
            ),
            "{remaining}": (
                "Optional number of free pool slots left; the whole line "
                "disappears when it is not provided."
            ),
            "{retriever.description}": (
                "Optional JSON catalog of the retrievers; the whole line "
                "disappears when it is not provided."
            ),
            "{documents.names}": (
                "Optional comma-separated document names; the whole line "
                "disappears when it is not provided."
            ),
            "{documents.description}": (
                "Optional JSON document summary; the whole line disappears when "
                "it is not provided."
            ),
        },
        "templates": TEMPLATES,
    }

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the default sufficiency prompt.

        Parameters
        ----------
        language : str
            Language code used to pick the default template ("en", "es", "pt").
        template : str, optional
            Override template. When omitted, the template for ``language`` is
            used.

        Raises
        ------
        RAGPromptTemplateError
            If no template is available for the language or the resolved
            template is missing required placeholders.
        """
        self.language = kwargs.pop("language")
        if "template" in kwargs:
            self.template = kwargs.pop("template")
        else:
            self.template = TEMPLATES.get(self.language, "")
        if not self.template:
            raise RAGPromptTemplateError(
                f"No template available for language: {self.language}"
            )
        self._validate()
