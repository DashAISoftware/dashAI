from __future__ import annotations

from typing import List, Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, field_validator

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    list_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

deepseek_available_models = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
]


class DeepSeekThinking(BaseModel):
    type: Literal["enabled", "disabled"] = "enabled"
    reasoning_effort: Optional[Literal["low", "high", "max"]] = None


class DeepSeekResponseFormat(BaseModel):
    type: Literal["text", "json_object"]


class DeepSeekTextToTextGenerationModelSchema(BaseSchema):
    API_key: schema_field(
        string_field(),
        placeholder="",
        description="API key for DeepSeek access.",
    )  # type: ignore

    model_name: schema_field(
        enum_field(enum=deepseek_available_models),
        placeholder="deepseek-v4-flash",
        description="The specific DeepSeek model version to use.",
    )  # type: ignore

    @field_validator(
        "max_tokens",
        "response_format",
        "stop",
        "temperature",
        "thinking",
        "top_p",
        mode="before",
    )
    def validate_optional_fields(cls, v):  # noqa: N805
        if v == "":
            return None
        return v

    max_tokens: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=(
            "The maximum number of tokens that can be generated in the chat completion."
        ),
    ) = None  # type: ignore

    response_format: schema_field(
        none_type(DeepSeekResponseFormat),
        placeholder=None,
        description=(
            "Specifies the format that the model must output. "
            "Setting to { type: 'json_object' } enables JSON mode."
        ),
    ) = None  # type: ignore

    stop: schema_field(
        none_type(union_type(string_field(), list_field(string_field()))),
        placeholder=None,
        description=(
            "Up to 16 sequences where the API will stop generating further tokens."
        ),
    ) = None  # type: ignore

    temperature: schema_field(
        none_type(float_field(ge=0.0, le=2.0)),
        placeholder=None,
        description=(
            "What sampling temperature to use, between 0 and 2. "
            "Higher values like 0.8 will make the output more random, while lower "
            "values like 0.2 will make it more focused and deterministic."
        ),
    ) = None  # type: ignore

    thinking: schema_field(
        none_type(DeepSeekThinking),
        placeholder=None,
        description=(
            "Thinking mode configuration. "
            "type: enabled or disabled. "
            "reasoning_effort (optional): low, high, or max."
        ),
    ) = None  # type: ignore

    top_p: schema_field(
        none_type(float_field(ge=0.0, le=2.0)),
        placeholder=None,
        description=(
            "An alternative to sampling with temperature, called nucleus sampling, "
            "where the model considers the results of the tokens with top_p "
            "probability mass. So 0.1 means only the tokens comprising the top 10% "
            "probability mass are considered."
        ),
    ) = None  # type: ignore


class DeepSeekTextToTextGenerationModel(TextToTextGenerationTaskModel):
    """Wrapper around DeepSeek's text-to-text generation models via API."""

    SCHEMA = DeepSeekTextToTextGenerationModelSchema
    DISPLAY_NAME: str = MultilingualString(
        en="DeepSeek API",
        es="API de DeepSeek",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "API for DeepSeek's language models, allowing you to select and"
            " configure the text-to-text models supported by the DeepSeek"
            " API (https://deepseek.com/). Note that it requires a private"
            " API key with an associated cost, that the language model runs"
            " on DeepSeek's servers, and that your data will be used"
            " according to that company's policies."
        ),
        es=(
            "API para los modelos de lenguaje de DeepSeek, permite"
            " seleccionar y configurar los modelos de texto a texto"
            " soportados por la API de DeepSeek (https://deepseek.com/)."
            " Considere que requiere una API key (clave de API) privada"
            " con un costo asociado, que el modelo de lenguaje se ejecuta"
            " en los servidores de DeepSeek y que sus datos serán"
            " utilizados según las políticas de esa empresa."
        ),
    )

    def __init__(self, **kwargs):
        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get("model_name")
        self.client = OpenAI(
            api_key=kwargs.get("API_key"),
            base_url="https://api.deepseek.com",
        )
        self.max_tokens = kwargs.get("max_tokens")
        self.temperature = kwargs.get("temperature")
        self.top_p = kwargs.get("top_p")
        thinking = kwargs.get("thinking")
        self.thinking = DeepSeekThinking(**thinking) if thinking is not None else None
        response_format = kwargs.get("response_format")
        self.response_format = (
            DeepSeekResponseFormat(**response_format)
            if response_format is not None
            else None
        )
        self.stop = kwargs.get("stop")

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        params: dict = {
            "model": self.model_name,
            "messages": prompt,
        }
        extra_body: dict = {}
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.thinking is not None:
            extra_body["thinking"] = self.thinking.model_dump(exclude_none=True)
        if self.response_format is not None:
            extra_body["response_format"] = self.response_format.model_dump()
        if self.stop is not None:
            extra_body["stop"] = self.stop
        if extra_body:
            params["extra_body"] = extra_body
        output = self.client.chat.completions.create(**params)
        return [output.choices[0].message.content]
