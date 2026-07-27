# ruff: noqa
import os

import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from openevals import create_trajectory_match_evaluator
from openevals.llm import create_llm_as_judge

from DashAI.back.Agent_tools import ALL_TOOLS
from DashAI.back.models.gpt4omini_agent import Gpt4oMiniAgent
from DashAI.back.models.Prompts.agent_prompt import SYSTEM_PROMPT
from tests.back.agents.evaluation_criteria.main_response_quality_criteria import (
    MainResponseQualityCriteria,
)
from tests.back.agents.evaluator_prompt import EVALUATION_PROMPT

load_dotenv()
key = os.getenv("OPENAI_API_KEY_DASHAI")


@pytest.fixture(name="agent")
def fixture_agent():
    return Gpt4oMiniAgent(
        key=key,
        frequency_penalty=0.1,
        system_prompt=SYSTEM_PROMPT,
        selected_tools=[tools.name for tools in ALL_TOOLS],
        max_tokens=5000,
        temperature=0.7,
        summary_trigger=10000,
        summary_keep=5000,
        conversation_id="test-thread-id",
    )


@pytest.fixture(name="llm_judge")
def fixture_llm_judge():
    llm_judge = ChatOpenAI(
        model="gpt-4o-mini", openai_api_key=key, temperature=0.1, max_tokens=5000
    )
    return create_llm_as_judge(
        prompt=EVALUATION_PROMPT,
        judge=llm_judge,
        output_schema=MainResponseQualityCriteria,
    )


@pytest.fixture(name="tool_calling_evaluator")
def fixture_tool_calling_evaluator():
    return create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="ignore"
    )


@pytest.fixture(name="tool_args_evaluator")
def fixture_tool_args_evaluator():
    return create_trajectory_match_evaluator(
        trajectory_match_mode="superset", tool_args_match_mode="subset"
    )
