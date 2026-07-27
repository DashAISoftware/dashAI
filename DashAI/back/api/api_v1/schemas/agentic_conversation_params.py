from typing import Any, Union

from pydantic import BaseModel


class AgenticConversationParams(BaseModel):
    name: Union[str, None] = None
    description: Union[str, None] = None


class AgenticConversationUpdateParams(BaseModel):
    name: Union[str, None] = None
    description: Union[str, None] = None


class AgenticConfigurationParams(BaseModel):
    configuration_name: str
    configuration_description: str
    family_model_name: str
    model_name: str
    parameters: dict[str, Any]
    tools: list[str]


class AgenticUpdateConfigurationParams(BaseModel):
    configuration_name: Union[str, None] = None
    configuration_description: Union[str, None] = None
    family_model_name: Union[str, None] = None
    model_name: Union[str, None] = None
    parameters: Union[dict[str, Any], None] = None
    tools: Union[list[str], None] = None
