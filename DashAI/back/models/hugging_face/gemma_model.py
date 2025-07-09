from typing import List

from llama_cpp import Llama

from huggingface_hub import login

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.models.hugging_face.llama_utils import is_gpu_available_for_llama_cpp
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

if is_gpu_available_for_llama_cpp():
    DEVICE_ENUM = ["gpu", "cpu"]
    DEVICE_PLACEHOLDER = "gpu"
else:
    DEVICE_ENUM = ["cpu"]
    DEVICE_PLACEHOLDER = "cpu"


class GemmaSchema(BaseSchema):
    """Schema for Gemma model."""

    model_name: schema_field(
        enum_field(
            enum=[
                "google/gemma-3-1b-it-qat-q4_0-gguf",
                "google/gemma-3-4b-it-qat-q4_0-gguf",
            ]
        ),
        placeholder="google/gemma-3-4b-it-qat-q4_0-gguf",
        description="The specific Gemma model version to use.",
    )  # type: ignore

    huggingface_key: schema_field(
        string_field(),
        placeholder="",
        description="Hugging Face API key for private models.",
    )  # type: ignore

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description="Maximum number of tokens to generate.",
    )  # type: ignore

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description=(
            "Sampling temperature. Higher values make the output more random, while "
            "lower values make it more focused and deterministic."
        ),
    )  # type: ignore

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description=(
            "Penalty for repeated tokens in the output. Higher values reduce the "
            "likelihood of repetition, encouraging more diverse text generation."
        ),
    )  # type: ignore

    context_window: schema_field(
        int_field(ge=1),
        placeholder=512,
        description=(
            "Maximum number of tokens the model can process in a single forward pass "
            "(context window size)."
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=DEVICE_ENUM),
        placeholder=DEVICE_PLACEHOLDER,
        description="The device to use for model inference.",
    )  # type: ignore


class GemmaModel(TextToTextGenerationTaskModel):
    """Gemma model for text generation using llama.cpp library."""

    SCHEMA = GemmaSchema

    def __init__(self, **kwargs):
        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get("model_name", "google/gemma-3-4b-it-qat-q4_0-gguf")
        self.huggingface_key = kwargs.get("huggingface_key")

        if self.huggingface_key:
            try:
                login(token=self.huggingface_key)
            except Exception as e:
                raise ValueError(
                    "Failed to login to Hugging Face. Please check your API key."
                ) from e

        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = "*0.gguf"

        self.model = Llama.from_pretrained(
            repo_id=self.model_name,
            filename=self.filename,
            verbose=True,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if kwargs.get("device", "gpu") == "gpu" else 0,
        )

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        """Generate text based on prompts."""
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )

        generated_text = output["choices"][0]["message"]["content"]
        return [generated_text]

    def __call__(self, prompt: str) -> List[str]:
        return self.generate(prompt)
