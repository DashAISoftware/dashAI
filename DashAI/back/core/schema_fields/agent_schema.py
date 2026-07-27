from typing import List

from pydantic import Field
from typing_extensions import Annotated

from DashAI.back.Agent_tools import ALL_TOOLS
from DashAI.back.core.schema_fields.int_field import int_field
from DashAI.back.core.schema_fields.schema_field import schema_field
from DashAI.back.core.utils import MultilingualString


class AgentSchema:
    """Schema for agentic language models.

    Shared by all agent-based language model wrappers. Controls conversation
    summarization behaviour through configurable token thresholds and allows
    selecting the set of tools available to the agent during execution. These
    settings help balance context preservation, response quality, and execution
    efficiency.
    """

    summary_trigger: schema_field(
        int_field(ge=1),
        placeholder=70000,
        description=MultilingualString(
            en=(
                "Number of tokens after which the conversation will be summarized.  "
                "This helps to manage long conversations by keeping the context "
                "window within limits of llm and avoid possible hallucinations by "
                "context window overflow. Set to a high value to effectively "
                "disable summarization"
            ),
            es=(
                "Número de tokens que gatillara un resumen de la conversación.  "
                "Esto ayuda a manejar conversaciones largas manteniendo la ventana de "
                "contexto dentro de los limites del modelo y evita posibles "
                "alucinaciones por ventana de contexto extensas. Establece un valor "
                "alto para deshabilitar hacer un resumen de la conversación"
            ),
        ),
        alias=MultilingualString(en="Summary trigger", es="Tokens para resumir"),
    )  # type: ignore
    summary_keep: schema_field(
        int_field(ge=1),
        placeholder=50000,
        description=MultilingualString(
            en=(
                "Number of tokens to keep in the summary after summarization "
                "is triggered. "
            ),
            es=(
                "Número de tokens a mantener en el resumen después de que "
                "se gatille el resumen."
            ),
        ),
        alias=MultilingualString(en="Summary keep", es="Tokens a mantener en resumen"),
    )  # type: ignore
    selected_tools: Annotated[
        List[str],
        Field(
            description=MultilingualString(
                en=(
                    "Select which tools the agent can use. A smaller number of tools "
                    "can improve the agent's performance by reducing the amount of "
                    "context dedicated to describing the tools, but a larger number "
                    "of tools gives the agent more capabilities and some tools are "
                    "necessary for the correct execution of others."
                ),
                es=(
                    "Selecciona cuáles herramientas puede usar el agente.  Una menor "
                    "cantidad de herramienta puede mejorar el desempeño del agente al "
                    "reducir la cantidad de contexto dedicado a describir las "
                    "herramienta, pero una mayor cantidad de herramientas le da más "
                    "capacidades al agente y algunas herramientas resultan "
                    "ser necesarias para la correcta ejecución de otras.  Por otro "
                    "lado, si el número de herramientas es bajo, mejora la velocidad "
                    "de respuesta."
                ),
            ),
            json_schema_extra={
                "display_tools_name": [
                    tool.extras["display_name"] for tool in ALL_TOOLS
                ],
                "display_name": MultilingualString(
                    en="Available tools", es="Herramientas disponibles"
                ),
                "toolsName": [tool.name for tool in ALL_TOOLS],
            },
        ),
    ]  # type: ignore
