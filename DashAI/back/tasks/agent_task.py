from DashAI.back.core.utils import MultilingualString
from DashAI.back.tasks.base_agent_task import BaseAgentTask


class AgentTask(BaseAgentTask):
    """
    Task for open-ended text generation using large language
    models in agentic modality.
    """

    metadata: dict = None

    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Agent Task", es="Tarea de Agente"
    )

    DESCRIPTION: MultilingualString = MultilingualString(
        en="""
        This task uses a large language model (LLM) in agentic modality to
        execute actions on the page and answer queries from users.
        """,
        es="""
        Esta tarea utiliza un modelo de lenguaje grande (LLM) en modalidad
        agentica para ejecutar acciones en la página y responder consultas
        de los usuarios.
        """,
    )
