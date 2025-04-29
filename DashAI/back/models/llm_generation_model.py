from DashAI.back.core.schema_fields import (
    BaseSchema,
    int_field,
    float_field,
    schema_field,
)

from DashAI.back.models.base_generative_model import BaseGenerativeModel

class LLMGenerationSchema(BaseSchema):
    """Schema for Llama text generation model."""

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description="Maximum number of tokens to generate.",
    )  # type: ignore   

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description="Sampling temperature. Higher values make the output more random, while lower values make it more focused and deterministic.",
    )  # type: ignore

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description="Penalty for repeated tokens in the output. Higher values reduce the likelihood of repetition, encouraging more diverse text generation.",
    )  # type: ignore

    n_ctx: schema_field(
        int_field(ge=1),
        placeholder=512,
        description="Maximum number of tokens the model can process in a single forward pass (context window size).",
    ) # type: ignore

class LLMGenerationModel(BaseGenerativeModel):
    """Class for models associated to LLMGenerationTask."""

    COMPATIBLE_COMPONENTS = ["LLMGenerationTask"]
    SCHEMA = LLMGenerationSchema

    def __init__(self, **kwargs):
        kwargs = self.validate_and_transform(kwargs)
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("n_ctx", 512)
