"""Deprecated DashAI generation types kept so older plugin code still imports.

An earlier iteration of the enriched text interface defined its own request,
result, usage and part classes in ``DashAI.back.core.generation``. They were
replaced by Pydantic AI's native types, but plugins written against them (for
example a ``generate_result`` that returns ``GenerationResult``) must keep
working instead of failing with ``ImportError``.

Warnings
--------
Do not use anything in this module in new code. Use the native types from
``pydantic_ai.messages`` and ``pydantic_ai.usage`` instead; they are described
in the plugin-development guide "Generation Interface". The names below are
still importable from ``DashAI.back.core.generation`` but emit a
``DeprecationWarning`` and may be removed in a future major release.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.messages import ModelResponse
from pydantic_ai.messages import TextPart as NativeTextPart
from pydantic_ai.messages import ThinkingPart as NativeThinkingPart
from pydantic_ai.usage import RequestUsage

#: Deprecated names re-exported (lazily, with a warning) by ``generation``.
DEPRECATED_NAMES = (
    "TextPart",
    "ReasoningPart",
    "GenerationPart",
    "GenerationMessage",
    "GenerationRequest",
    "GenerationUsage",
    "GenerationResult",
)

REPLACEMENT_HINT = (
    "Use the native Pydantic AI types from 'pydantic_ai.messages' and "
    "'pydantic_ai.usage' (ModelMessage, ModelResponse, TextPart, ThinkingPart, "
    "RequestUsage) and the bridge in 'DashAI.back.core.generation'. See the "
    "'Generation Interface' plugin-development guide."
)

_FINISH_REASONS = {"stop", "length", "content_filter", "tool_call", "error"}


class _GenerationData(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", allow_inf_nan=False)


class TextPart(_GenerationData):
    """Deprecated. Use ``pydantic_ai.messages.TextPart`` (field ``content``)."""

    type: Literal["text"] = "text"
    text: str


class ReasoningPart(_GenerationData):
    """Deprecated. Use ``pydantic_ai.messages.ThinkingPart`` (field ``content``)."""

    type: Literal["reasoning"] = "reasoning"
    text: str


GenerationPart = Annotated[TextPart | ReasoningPart, Field(discriminator="type")]


class GenerationMessage(_GenerationData):
    """Deprecated. Use ``ModelRequest`` / ``ModelResponse`` from Pydantic AI."""

    role: Literal["system", "user", "assistant"]
    parts: list[GenerationPart] = Field(min_length=1)


class GenerationRequest(_GenerationData):
    """Deprecated. ``generate_result`` now receives ``list[ModelMessage]``."""

    messages: list[GenerationMessage] = Field(min_length=1)

    @classmethod
    def from_messages(cls, messages: list[dict[str, str]]) -> "GenerationRequest":
        """Convert role/content dictionaries (deprecated)."""
        if any(set(message) != {"role", "content"} for message in messages):
            raise ValueError("Text message conversion supports only role and content.")
        return cls(
            messages=[
                GenerationMessage(
                    role=message["role"], parts=[TextPart(text=message["content"])]
                )
                for message in messages
            ]
        )

    def to_messages(self) -> list[dict[str, str]]:
        """Return role/content dictionaries, rejecting non-text parts (deprecated)."""
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
    """Deprecated. Use ``pydantic_ai.usage.RequestUsage``."""

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    generation_seconds: float | None = Field(default=None, ge=0)
    load_seconds: float | None = Field(default=None, ge=0)


class GenerationResult(_GenerationData):
    """Deprecated. Return a native ``pydantic_ai.messages.ModelResponse`` instead.

    The host still accepts this class from ``generate_result`` and converts it with
    :meth:`to_model_response`.
    """

    parts: list[GenerationPart] = Field(min_length=1)
    usage: GenerationUsage | None = None
    finish_reason: str | None = None

    @property
    def text(self) -> str:
        """Return answer text only, preserving part order and whitespace."""
        return "".join(part.text for part in self.parts if isinstance(part, TextPart))

    def to_model_response(self) -> ModelResponse:
        """Convert to a native response.

        Reasoning becomes ``ThinkingPart``. Token counts map to ``RequestUsage``;
        durations and a finish reason Pydantic AI does not define go to
        ``provider_details`` instead of being dropped.
        """
        parts = [
            NativeTextPart(part.text)
            if isinstance(part, TextPart)
            else NativeThinkingPart(part.text)
            for part in self.parts
        ]
        usage, details = RequestUsage(), {}
        if self.usage is not None:
            usage = RequestUsage(
                input_tokens=self.usage.prompt_tokens or 0,
                output_tokens=self.usage.completion_tokens or 0,
            )
            for name in ("generation_seconds", "load_seconds"):
                if (value := getattr(self.usage, name)) is not None:
                    details[name] = value
        finish_reason = None
        if self.finish_reason in _FINISH_REASONS:
            finish_reason = self.finish_reason
        elif self.finish_reason is not None:
            details["finish_reason"] = self.finish_reason
        return ModelResponse(
            parts=parts,
            usage=usage,
            finish_reason=finish_reason,  # ty: ignore[invalid-argument-type]
            provider_details=details or None,
        )


class LegacyRequestMessages(list):
    """Native messages that also answer the deprecated ``GenerationRequest`` calls.

    ``generate_result`` receives this list subclass. It behaves exactly like
    ``list[ModelMessage]``; ``to_messages()`` and ``messages`` exist only so
    enriched plugins written for the earlier draft keep working.
    """

    def to_messages(self) -> list[dict[str, str]]:
        """Return role/content dictionaries (deprecated)."""
        from DashAI.back.core.generation import to_chat_messages

        return to_chat_messages(self)

    @property
    def messages(self) -> list[GenerationMessage]:
        """Return the deprecated typed messages (deprecated)."""
        return GenerationRequest.from_messages(self.to_messages()).messages


def deprecated_attribute(name: str) -> Any:
    """Return one deprecated class by name; used by ``generation.__getattr__``."""
    return globals()[name]
