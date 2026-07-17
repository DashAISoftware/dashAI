from typing import List

from openai import OpenAI
from pydantic import field_validator

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

deepseek_available_models = [
    "deepseek-chat",
    "deepseek-reasoner",
]


class DeepSeekTextToTextGenerationModelSchema(BaseSchema):
    API_key: schema_field(
        string_field(),
        placeholder="",
        description="API key for DeepSeek access.",
    )  # type: ignore

    model_name: schema_field(
        enum_field(enum=deepseek_available_models),
        placeholder="deepseek-chat",
        description="The specific DeepSeek model version to use.",
    )  # type: ignore

    @field_validator(
        "frequency_penalty",
        "max_completions_tokens",
        "presence_penalty",
        "temperature",
        "top_p",
        mode="before",
    )
    def validate_optional_fields(cls, v):  # noqa: N805
        if v == "":
            return None
        return v

    frequency_penalty: schema_field(
        none_type(float_field(ge=-2.0, le=2.0)),
        placeholder=None,
        description=(
            "Number between -2.0 and 2.0. Positive values penalize new tokens "
            "based on their existing frequency in the text so far, decreasing the "
            "model's likelihood to repeat the same line verbatim."
        ),
    )  # type: ignore

    max_completions_tokens: schema_field(
        none_type(int_field(ge=1)),
        placeholder=None,
        description=(
            "An upper bound for the number of tokens that can be generated for a "
            "completion, including visible output tokens and reasoning tokens."
        ),
    )  # type: ignore

    presence_penalty: schema_field(
        none_type(float_field(ge=-2.0, le=2.0)),
        placeholder=None,
        description=(
            "Number between -2.0 and 2.0. Positive values penalize new tokens "
            "based on whether they appear in the text so far, increasing the "
            "model's likelihood to talk about new topics."
        ),
    )  # type: ignore

    temperature: schema_field(
        none_type(float_field(ge=0.0, le=2.0)),
        placeholder=None,
        description=(
            "temperature: What sampling temperature to use, between 0 and 2. "
            "Higher values like 0.8 will make the output more random, while lower "
            "values like 0.2 will make it more focused and deterministic. "
            "We generally recommend altering this or `top_p` but not both."
        ),
    )  # type: ignore

    top_p: schema_field(
        none_type(float_field(ge=0.0, le=2.0)),
        placeholder=None,
        description=(
            "An alternative to sampling with temperature, called nucleus sampling, "
            "where the model considers the results of the tokens with top_p "
            "probability mass. So 0.1 means only the tokens comprising the top 10% "
            "probability mass are considered. "
            "We generally recommend altering this or `temperature` but not both."
        ),
    )  # type: ignore


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
        self.client = OpenAI(
            api_key=kwargs.get("API_key"),
            base_url="https://api.deepseek.com",
        )
        self.model_name = kwargs.get("model_name")

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        output = self.client.chat.completions.create(
            model=self.model_name,
            messages=prompt,
        )
        return [output.choices[0].message.content]
