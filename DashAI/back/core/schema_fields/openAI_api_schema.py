from DashAI.back.core.schema_fields.float_field import float_field
from DashAI.back.core.schema_fields.int_field import int_field
from DashAI.back.core.schema_fields.schema_field import schema_field
from DashAI.back.core.schema_fields.string_field import string_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.Prompts.agent_prompt import SYSTEM_PROMPT


class OpenAIAPISchema:
    """Schema for OpenAI API-based language models.

    Shared by all OpenAI model wrappers. Configures the core generation
    parameters, including maximum response length, sampling temperature,
    system prompt, and the API key required to authenticate requests to the
    OpenAI API.
    """

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=10000,
        description=MultilingualString(
            en=(
                "Maximum number of tokens to generate.  A low value may lead to "
                "unexpected behaviors in agentic mode."
            ),
            es=(
                "Número máximo de tokens a generar.  EXTREMO CUIDADO, si el valor "
                "es bajo y la respuesta de texto que el agente debe entregar emplea "
                "muchos tokens, la respuesta del agente es vacía.  "
            ),
        ),
        alias=MultilingualString(en="Max tokens", es="Tokens máximos"),
    )  # type: ignore

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description=MultilingualString(
            en=(
                "Sampling temperature. Higher values make the output more random, "
                "while lower values make it more focused and deterministic."
            ),
            es=(
                "Temperatura de muestreo. Valores más altos hacen la salida más "
                "aleatoria, mientras que valores más bajos la hacen más enfocada "
                "y determinista."
            ),
        ),
        alias=MultilingualString(en="Temperature", es="Temperatura"),
    )  # type: ignore

    system_prompt: schema_field(
        string_field(),
        placeholder=SYSTEM_PROMPT,
        description=MultilingualString(
            en=(
                "The system prompt to use for the OpenAI agent.  Adjust it to improve "
                "the agent's performance."
            ),
            es=(
                "El prompt del sistema a usar para el agente OpenAI.  Ajústelo para "
                "mejorar el desempeño del agente."
            ),
        ),
        alias=MultilingualString(en="System prompt", es="Prompt del sistema"),
    )  # type: ignore
    key: schema_field(
        string_field(),
        placeholder="",
        description=MultilingualString(
            en="OpenAI API key (required for LLM requests via endpoint)",
            es="Llave de OpenAI (requerida para solicitudes al LLM vía endpoint)",
        ),
        alias=MultilingualString(en="Api key llm", es="Llave para llm"),
    )  # type: ignore
