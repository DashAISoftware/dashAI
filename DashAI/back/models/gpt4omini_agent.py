import sqlite3
from typing import Any

from kink import di
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, ToolRetryMiddleware
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from DashAI.back.Agent_tools import ALL_TOOLS, get_tools
from DashAI.back.core.schema_fields import (
    AgentSchema,
    BaseSchema,
    OpenAIAPISchema,
    float_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.agentic_model import AgenticModel
from DashAI.back.models.Prompts.agent_prompt import SYSTEM_PROMPT



class Gpt4oMiniAgentSchema(BaseSchema, AgentSchema, OpenAIAPISchema):
    """Schema for GPT-4o-mini agent hyperparameters.

    Configures the generation behaviour of the GPT-4o-mini agent, including
    sampling parameters, conversation summarization thresholds, maximum
    response length, and the set of tools available to the agent. The schema
    also exposes the OpenAI API credentials required to access the model.
    """

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description=MultilingualString(
            en=(
                "Penalty for repeated tokens in the output. Higher values reduce the "
                "likelihood of repetition, encouraging more diverse text generation."
            ),
            es=(
                "Penalización para tokens repetidos en la salida. Valores más altos "
                "reducen la probabilidad de repetición, fomentando una generación "
                "de texto más diversa."
            ),
        ),
        alias=MultilingualString(
            en="Frequency penalty", es="Penalización de frecuencia"
        ),
    )  # type: ignore


class Gpt4oMiniAgent(AgenticModel):
    """GPT-4o-mini model for agentic text generation using OpenAI.

    GPT-4o-mini is a lightweight multimodal language model from OpenAI designed
    for efficient conversational reasoning, tool calling, and instruction
    following. This integration enables persistent conversations, automatic
    context summarization, and seamless interaction with external tools through
    the LangChain agent framework.
    """

    COMPATIBLE_COMPONENTS = ["AgentTask"]
    SCHEMA = Gpt4oMiniAgentSchema
    METADATA = {"family_model": "OpenAI"}
    DISPLAY_NAME: str = MultilingualString(
        en="GPT-4o-mini model", es="Modelo GPT-4o-mini"
    )
    DESCRIPTION: str = MultilingualString(
        en="OpenAI model for use with agentic modality",
        es="Modelo OpenAI para su uso con modalidad agentica",
    )

    def __init__(self, **kwargs):
        """Initialise a GPT-4o-mini agent backed by the OpenAI Chat API.

        The model is configured with the provided API key and generation
        parameters. A set of user-selected tools is attached to the agent,
        together with middleware for automatic conversation summarization and
        tool retry handling.

        Parameters
        ----------
        **kwargs : dict
            key : str
                OpenAI API key used to authenticate requests.
            conversation_id : str, optional
                Identifier of the conversation thread used to persist state.
            system_prompt : str, optional
                System prompt that defines the agent behaviour.
                Defaults to ``SYSTEM_PROMPT``.
            max_tokens : int, optional
                Maximum number of tokens generated in each response.
                Default 10000.
            temperature : float, optional
                Sampling temperature controlling response randomness.
                Default 0.7.
            frequency_penalty : float, optional
                Penalty applied to repeated tokens. Default 0.1.
            summary_trigger : int, optional
                Number of conversation tokens that triggers automatic
                summarization. Default 10000.
            summary_keep : int, optional
                Number of recent tokens preserved after summarization.
                Default 5000.
            selected_tools : list[str], optional
                Names of the tools made available to the agent. If omitted,
                all registered tools are enabled.

        Raises
        ------
        RuntimeError
            If no valid OpenAI API key is provided.
        """

        self.conversation_id = kwargs.pop("conversation_id", None)
        kwargs = self.validate_and_transform(kwargs)
        self.model_name = "gpt-4o-mini"

        self.key = kwargs.get("key")
        if self.key is None:
            raise RuntimeError("There is not a valid key selected.")

        self.system_prompt = kwargs.pop("system_prompt", SYSTEM_PROMPT)
        self.max_tokens = kwargs.pop("max_tokens", 10000)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.summary_trigger = kwargs.pop("summary_trigger", 10000)
        self.summary_keep = kwargs.pop("summary_keep", 5000)

        selected_tools_name = set(
            kwargs.pop("selected_tools", [tool.name for tool in ALL_TOOLS])
        )
        all_tools = get_tools()
        tools_by_name = {tool.name: tool for tool in all_tools}
        self.tools_dashAI = [
            tools_by_name[name] for name in selected_tools_name if name in tools_by_name
        ]

        self.model = ChatOpenAI(
            model=self.model_name,
            openai_api_key=self.key,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            max_tokens=self.max_tokens,
        )

    def generate(self, user_prompt: str) -> list[Any]:
        """Generate a response while maintaining conversation state.

        The agent restores the conversation history associated with the current
        thread identifier, applies summarization when the configured token
        threshold is reached, executes tool calls when necessary, and returns
        the assistant's final response.

        Parameters
        ----------
        user_prompt : str
            User message to send to the conversational agent.

        Returns
        -------
        list[Any]
            The content of the assistant's final message.
        """
        config = di["config"]
        conn = sqlite3.connect(str(config["SQLITE_DB_PATH"]), check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        agent = create_agent(
            model=self.model,
            system_prompt=self.system_prompt,
            tools=self.tools_dashAI,
            middleware=[
                SummarizationMiddleware(
                    model=self.model,
                    trigger=("tokens", self.summary_trigger),
                    keep=("tokens", self.summary_keep),
                ),
                ToolRetryMiddleware(max_retries=1, on_failure="return_message"),
            ],
            checkpointer=checkpointer,
        )

        config = {"configurable": {"thread_id": str(self.conversation_id)}}
        response = agent.invoke(
            {"messages": user_prompt}, stream_node="values", config=config
        )

        return response["messages"][-1].content

    def generate_answer_test(self, user_prompt: str) -> list:
        """Generate a response without persistent conversation state.

        This method creates a temporary agent instance that does not use a
        checkpointer, making it suitable for testing or stateless inference.

        Parameters
        ----------
        user_prompt : str
            User message to send to the conversational agent.

        Returns
        -------
        list
            Full response object returned by the agent invocation, including
            all generated messages.
        """
        agent = create_agent(
            model=self.model,
            system_prompt=self.system_prompt,
            tools=self.tools_dashAI,
            middleware=[
                SummarizationMiddleware(
                    model=self.model,
                    trigger=("tokens", self.summary_trigger),
                    keep=("tokens", self.summary_keep),
                ),
                ToolRetryMiddleware(max_retries=1, on_failure="return_message"),
            ],
        )
        response = agent.invoke({"messages": user_prompt}, stream_mode="values")

        return response

    def resume(self, command_input: Command) -> list[Any]:
        pass
