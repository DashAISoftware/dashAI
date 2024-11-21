from DashAI.back.core.schema_fields import (
    BaseSchema,
    int_field,
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

class LLMGenerationModel(BaseGenerativeModel):
    """Class for models associated to ImageGenerationTasks."""

    COMPATIBLE_COMPONENTS = ["LLMGenerationTask"]

    def __init__(self, **kwargs):
        kwargs = self.validate_and_transform(kwargs)
        self.max_tokens = kwargs.pop("max_tokens", 100)
