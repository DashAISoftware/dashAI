"""Pydantic AI message contracts and compatibility for DashAI text models."""

from collections.abc import Callable, Sequence
from dataclasses import asdict
from math import isfinite
from typing import Any, TypeVar

from pydantic import TypeAdapter, ValidationError
from pydantic_ai.direct import model_request_sync
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    UserPromptPart,
)
from pydantic_ai.models import Model

_T = TypeVar("_T")
_RESPONSE = TypeAdapter(ModelResponse)


def _validated(build: Callable[[Any], _T], data: Any) -> _T:
    """Report validation locations and reasons without logging message contents."""
    try:
        return build(data)
    except ValidationError as e:
        details = "; ".join(
            f"{'.'.join(map(str, err['loc'])) or 'value'}: {err['msg']}"
            for err in e.errors(include_input=False, include_url=False)
        )
        raise ValueError(f"Invalid generation data ({details}).") from None


def from_chat_messages(messages: list[dict[str, str]]) -> list[ModelMessage]:
    """Convert legacy role/content messages to native Pydantic AI types.

    Warnings
    --------
    Compatibility bridge only. Do not use this function in new integrations;
    construct native ``ModelRequest`` and ``ModelResponse`` messages instead.
    This conversion is reserved for existing tasks and plugins being migrated.
    """
    if not messages:
        raise ValueError("Generation requires at least one message.")
    converted: list[ModelMessage] = []
    for message in messages:
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or not isinstance(message["content"], str)
        ):
            raise ValueError("Text messages require only role and string content.")
        content = message["content"]
        if message["role"] == "system":
            converted.append(ModelRequest(parts=[SystemPromptPart(content)]))
        elif message["role"] == "user":
            converted.append(ModelRequest(parts=[UserPromptPart(content)]))
        elif message["role"] == "assistant":
            converted.append(ModelResponse(parts=[TextPart(content)]))
        else:
            raise ValueError("Text message role must be system, user or assistant.")
    return converted


def to_chat_messages(messages: Sequence[ModelMessage]) -> list[dict[str, str]]:
    """Adapt text-only messages, rejecting parts legacy plugins cannot represent.

    Warnings
    --------
    Compatibility bridge only. Do not use this function in new integrations;
    pass native Pydantic AI messages directly to the model. This conversion is
    reserved for adapters that must still call a legacy task, plugin or provider.
    """
    converted = []
    for message in messages:
        if not message.parts:
            raise ValueError("Generation messages require at least one part.")
        if isinstance(message, ModelResponse):
            if any(not isinstance(part, TextPart) for part in message.parts):
                raise ValueError("Legacy generation only accepts text input parts.")
            converted.append(
                {
                    "role": "assistant",
                    "content": "".join(part.content for part in message.parts),
                }
            )
            continue
        if message.instructions:
            raise ValueError("Legacy generation cannot represent request instructions.")
        for part in message.parts:
            if isinstance(part, SystemPromptPart):
                role, content = "system", part.content
            elif isinstance(part, UserPromptPart) and isinstance(part.content, str):
                role, content = "user", part.content
            else:
                raise ValueError(
                    "Legacy generation only accepts text messages; "
                    "multimodal and tool parts need an enriched model."
                )
            converted.append({"role": role, "content": content})
    return converted


def from_legacy_output(output: list[str] | tuple[str, ...]) -> ModelResponse:
    """Wrap the first legacy reply without inventing provider-reported usage.

    Warnings
    --------
    Compatibility bridge only. Do not use this function in new integrations;
    return a native ``ModelResponse`` with its parts and usage instead. This
    adapter exists solely to keep existing ``generate`` implementations working.
    """
    if not isinstance(output, (list, tuple)):
        raise TypeError("Text generation must return a list or tuple of strings.")
    if not output:
        raise ValueError("LLM model returned empty output list.")
    if not isinstance(output[0], str):
        raise TypeError(f"LLM output is not a string, got {type(output[0]).__name__}")
    return ModelResponse(parts=[TextPart(output[0])])


def text_answer(response: ModelResponse) -> str:
    """Project an answer for the current text storage, never dropping other output.

    Warnings
    --------
    Legacy text-storage adapter only. Do not use this projection in new structured
    storage or generation flows; retain the complete native ``ModelResponse``.
    It exists only until the current answer-only storage path is migrated.
    """
    if any(not isinstance(part, (TextPart, ThinkingPart)) for part in response.parts):
        raise ValueError(
            "This task cannot store tool or multimodal output yet; "
            "use a model that returns a text answer."
        )
    if not any(isinstance(part, TextPart) for part in response.parts):
        raise ValueError(
            "The model returned reasoning but no answer text. Reasoning "
            "is not stored yet; make the model return a text part with its answer."
        )
    return "".join(
        part.content for part in response.parts if isinstance(part, TextPart)
    )


def generate_text(
    model: Any, messages: list[dict[str, str]] | Sequence[ModelMessage]
) -> ModelResponse:
    """Call a Pydantic AI model, enriched DashAI model or legacy plugin once.

    Native messages retain multimodal and tool parts for capable models. Legacy
    adapters reject unsupported data before calling the provider. Invalid replies
    and provider failures never trigger a fallback generation call.

    New callers must pass native Pydantic AI messages and consume the complete
    ``ModelResponse``. Dictionary input and the legacy ``generate`` fallback are
    supported only for backward compatibility, not for new integrations.
    """
    if not messages:
        raise ValueError("Generation requires at least one message.")
    if all(isinstance(message, (ModelRequest, ModelResponse)) for message in messages):
        # Native dataclasses are mutable: validate a snapshot even for instances.
        request = _validated(
            ModelMessagesTypeAdapter.validate_python,
            [asdict(message) for message in messages],
        )
    else:
        request = from_chat_messages(messages)
    if isinstance(model, Model):
        response = model_request_sync(model, request)
    else:
        generate_result = getattr(model, "generate_result", None)
        if not callable(generate_result):
            return from_legacy_output(model.generate(to_chat_messages(request)))
        response = generate_result(request)
    if isinstance(response, ModelResponse):
        response = asdict(response)
    result = _validated(_RESPONSE.validate_python, response)
    for name, value in vars(result.usage).items():
        if (name.endswith("_tokens") and value < 0) or (
            name == "audio_seconds" and (value < 0 or not isfinite(value))
        ):
            raise ValueError(f"Invalid generation usage field: {name}.")
    return result
