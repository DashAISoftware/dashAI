from typing import List

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.models.hugging_face.llama_utils import is_gpu_available_for_llama_cpp
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

if Llama is not None and is_gpu_available_for_llama_cpp():
    DEVICE_ENUM = ["gpu", "cpu"]
    DEVICE_PLACEHOLDER = "gpu"
else:
    DEVICE_ENUM = ["cpu"]
    DEVICE_PLACEHOLDER = "cpu"


class QwenSchema(BaseSchema):
    """Schema for Qwen model."""

    model_name: schema_field(
        enum_field(
            enum=[
                "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                "Qwen/Qwen3-4B-GGUF ",
            ]
        ),
        placeholder="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        description="The specific Qwen model version to use.",
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


class QwenModel(TextToTextGenerationTaskModel):
    """Qwen model for text generation using llama.cpp library."""

    SCHEMA = QwenSchema

    def __init__(self, **kwargs):
        if Llama is None:
            raise RuntimeError(
                "llama-cpp-python is not installed. Please install it to use QwenModel."
            )

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        self.filename = "*8_0.gguf"

        self.model = Llama.from_pretrained(
            repo_id=self.model_name,
            filename=self.filename,
            verbose=True,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if kwargs.get("device", "gpu") == "gpu" else 0,
        )

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )
        return [output["choices"][0]["message"]["content"]]
