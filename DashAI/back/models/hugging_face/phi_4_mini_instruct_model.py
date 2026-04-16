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
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)
from DashAI.back.models.utils import (
    LLAMA_DEVICE_ENUM,
    LLAMA_DEVICE_PLACEHOLDER,
    LLAMA_DEVICE_TO_IDX,
)


class Phi4MiniInstructSchema(BaseSchema):
    """Schema for Phi 4 Mini Instruct model."""

    quantization: schema_field(
        enum_field(
            enum=[
                #"unsloth/Phi-4-mini-instruct-GGUF",
                "Phi-4-mini-instruct-Q2_K.gguf",
                "Phi-4-mini-instruct-Q2_K_L.gguf",
                "Phi-4-mini-instruct-Q3_K_M.gguf",
                "Phi-4-mini-instruct-Q4_K_M.gguf",
                "Phi-4-mini-instruct-Q5_K_M.gguf",
                "Phi-4-mini-instruct-Q6_K.gguf",
                "Phi-4-mini-instruct.BF16.gguf",
                "Phi-4-mini-instruct.Q8_0.gguf",
            ]
        ),
        placeholder="Phi-4-mini-instruct.BF16.gguf",
        description="The specific Phi 4 Mini Instruct model quantization to use.",
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
        placeholder=4096,
        description=(
            "Maximum number of tokens the model can process in a single forward pass "
            "(context window size)."
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=LLAMA_DEVICE_ENUM),
        placeholder=LLAMA_DEVICE_PLACEHOLDER,
        description="The device to use for model inference.",
    )  # type: ignore


class Phi4MiniInstructModel(TextToTextGenerationTaskModel):
    """Phi 4 Mini Instruct model for text generation using llama.cpp library."""

    SCHEMA = Phi4MiniInstructSchema

    def __init__(self, **kwargs):
        if Llama is None:
            raise RuntimeError(
                "llama-cpp-python is not installed. Please install it to use Phi 4 Mini Instruct model."
            )

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = "unsloth/Phi-4-mini-instruct-GGUF"
        self.quantization = kwargs.pop("quantization", "Phi-4-mini-instruct.Q8_0.gguf")
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        use_gpu = LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) >= 0

        self.model = Llama.from_pretrained(
            repo_id=self.model_name,
            filename=self.quantization,
            verbose=True,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if use_gpu else 0,
            main_gpu=LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) if use_gpu else 0,
        )

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )
        return [output["choices"][0]["message"]["content"]]
