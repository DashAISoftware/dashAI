"""Provider-independent contracts and compatibility for text generation."""

from collections.abc import Callable
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_T = TypeVar("_T")


class _GenerationData(BaseModel):
    # frozen: a validated request or result cannot later be edited into an
    # invalid state (for example by assigning ``parts = []``).
    model_config = ConfigDict(
        strict=True, extra="forbid", allow_inf_nan=False, frozen=True
    )


class TextPart(_GenerationData):
    """Text supplied by a user or returned as an answer."""

    type: Literal["text"] = "text"
    text: str


class ReasoningPart(_GenerationData):
    """Reasoning explicitly supplied by a model, separate from its answer."""

    type: Literal["reasoning"] = "reasoning"
    text: str


GenerationPart = Annotated[TextPart | ReasoningPart, Field(discriminator="type")]


class GenerationMessage(_GenerationData):
    """One conversation message with ordered, typed parts."""

    role: Literal["system", "user", "assistant"]
    parts: list[GenerationPart] = Field(min_length=1)


class GenerationRequest(_GenerationData):
    """A text conversation; model parameters remain in the existing schema."""

    messages: list[GenerationMessage] = Field(min_length=1)

    @classmethod
    def from_messages(cls, messages: list[dict[str, str]]) -> "GenerationRequest":
        """Convert the role/content messages prepared by existing text tasks."""
        if any(
            not isinstance(message, dict) or set(message) != {"role", "content"}
            for message in messages
        ):
            raise ValueError(
                "Text message conversion supports only role and content dictionaries."
            )
        return cls(
            messages=[
                GenerationMessage(
                    role=message["role"], parts=[TextPart(text=message["content"])]
                )
                for message in messages
            ]
        )

    def to_messages(self) -> list[dict[str, str]]:
        """Adapt text requests to legacy models without dropping richer parts."""
        messages = []
        for message in self.messages:
            if any(not isinstance(part, TextPart) for part in message.parts):
                raise ValueError("Legacy generation only accepts text input parts.")
            messages.append(
                {
                    "role": message.role,
                    "content": "".join(part.text for part in message.parts),
                }
            )
        return messages


class GenerationUsage(_GenerationData):
    """Optional backend-reported measurements; unavailable values stay absent."""

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    generation_seconds: float | None = Field(default=None, ge=0)
    load_seconds: float | None = Field(default=None, ge=0)


class GenerationResult(_GenerationData):
    """One assistant reply with optional usage and a backend finish reason."""

    parts: list[GenerationPart] = Field(min_length=1)
    usage: GenerationUsage | None = None
    finish_reason: str | None = None

    @property
    def text(self) -> str:
        """Return answer text only, preserving part order and whitespace."""
        return "".join(part.text for part in self.parts if isinstance(part, TextPart))

    @classmethod
    def from_legacy(cls, output: list[str] | tuple[str, ...]) -> "GenerationResult":
        """Normalize the first reply, as the existing chat and RAG tasks do.

        Only ``output[0]`` is used; further replies are ignored.
        """
        if not isinstance(output, (list, tuple)):
            raise TypeError("Text generation must return a list of strings.")
        if not output:
            raise ValueError("LLM model returned empty output list.")
        if not isinstance(output[0], str):
            raise TypeError(
                f"LLM output is not a string, got {type(output[0]).__name__}"
            )
        return cls(parts=[TextPart(text=output[0])])


def _validated(build: Callable[[Any], _T], data: Any) -> _T:
    """Run a pydantic constructor, reporting where and why data is invalid.

    pydantic's own message embeds the offending input, which here is prompt or
    answer text. That message ends up in logs and stored process data, so only
    the location and reason are kept.
    """
    try:
        return build(data)
    except ValidationError as e:
        details = "; ".join(
            f"{'.'.join(map(str, err['loc'])) or 'value'}: {err['msg']}"
            for err in e.errors(include_input=False, include_url=False)
        )
        raise ValueError(f"Invalid text generation data ({details}).") from None


def generate_text(model: Any, messages: list[dict[str, str]]) -> GenerationResult:
    """Run a typed or legacy text model once, without retrying generation errors.

    Duck-typed legacy plugins need only ``generate``. New models can expose
    ``generate_result``; an invalid enriched result is an error, not a reason
    to call the provider again through the legacy method.

    Raises
    ------
    ValueError
        If the messages or an enriched result are invalid. The message names
        the invalid fields but never repeats their content.
    TypeError
        If a legacy ``generate`` does not return a list of strings.
    """
    request = _validated(GenerationRequest.from_messages, messages)
    generate_result = getattr(model, "generate_result", None)
    if not callable(generate_result):
        return GenerationResult.from_legacy(model.generate(request.to_messages()))
    return _validated(GenerationResult.model_validate, generate_result(request))
