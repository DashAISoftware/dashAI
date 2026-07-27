from typing import List

from langchain_core.tools import BaseTool

from DashAI.back.Agent_tools.tools_converters import CONVERTER_TOOLS
from DashAI.back.Agent_tools.tools_datasets import DATASET_TOOLS
from DashAI.back.Agent_tools.tools_explorers import EXPLORER_TOOLS
from DashAI.back.Agent_tools.tools_notebook import NOTEBOOK_TOOLS
from DashAI.back.Agent_tools.tools_sessions import SESSIONS_TOOLS

ALL_TOOLS: list[BaseTool] = (
    DATASET_TOOLS + NOTEBOOK_TOOLS + EXPLORER_TOOLS + SESSIONS_TOOLS + CONVERTER_TOOLS
)


def get_tools() -> list[BaseTool]:
    """Return the LangChain tools available for the DashAI agent."""
    return list(ALL_TOOLS)
