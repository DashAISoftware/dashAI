"""Typed generation, legacy adaptation, and provider-call boundaries."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from DashAI.back.core.generation import (
    GenerationMessage,
    GenerationRequest,
    GenerationResult,
    GenerationUsage,
    ReasoningPart,
    TextPart,
    generate_text,
)
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)

MESSAGES = [
    {"role": "system", "content": "Keep whitespace."},
    {"role": "user", "content": " Question\n"},
    {"role": "assistant", "content": "Prior answer"},
    {"role": "user", "content": "Follow-up"},
]


class LegacyModel(TextToTextGenerationTaskModel):
    def __init__(self):
        self.generate = Mock(return_value=[" Answer\n"])

    def generate(self, prompt):
        raise NotImplementedError


class TypedModel(LegacyModel):
    def generate_result(self, request):
        assert request.to_messages() == MESSAGES
        return GenerationResult(
            parts=[ReasoningPart(text="Plan"), TextPart(text=" Answer\n")],
            usage=GenerationUsage(prompt_tokens=10, completion_tokens=5),
            finish_reason="stop",
        )


def test_legacy_subclass_keeps_input_and_answer_exactly():
    model = LegacyModel()
    result = generate_text(model, MESSAGES)

    model.generate.assert_called_once_with(MESSAGES)
    assert result.text == " Answer\n"
    assert result.usage is None
    assert result.finish_reason is None


def test_duck_typed_legacy_plugin_needs_only_generate():
    model = Mock(spec=["generate"])
    model.generate.return_value = ["answer"]

    assert generate_text(model, MESSAGES).text == "answer"
    model.generate.assert_called_once_with(MESSAGES)


def test_enriched_model_uses_one_path_and_preserves_metadata():
    model = TypedModel()
    result = generate_text(model, MESSAGES)

    model.generate.assert_not_called()
    assert result.text == " Answer\n"
    assert result.parts[0] == ReasoningPart(text="Plan")
    assert result.usage.completion_tokens == 5
    assert result.finish_reason == "stop"
    assert GenerationResult.model_validate_json(result.model_dump_json()) == result


def test_enriched_failure_does_not_repeat_generation():
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.side_effect = RuntimeError("provider failed")

    with pytest.raises(RuntimeError, match="provider failed"):
        generate_text(model, MESSAGES)

    model.generate_result.assert_called_once()
    model.generate.assert_not_called()


def test_invalid_enriched_response_does_not_fall_back_to_legacy():
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.return_value = ["not a GenerationResult"]

    with pytest.raises(ValidationError):
        generate_text(model, MESSAGES)

    model.generate.assert_not_called()


@pytest.mark.parametrize("output", [None, "answer", [], [None], [42], [{}]])
def test_invalid_legacy_output_is_not_silently_stringified(output):
    with pytest.raises((TypeError, ValueError)):
        GenerationResult.from_legacy(output)


def test_legacy_first_reply_convention_is_preserved():
    assert GenerationResult.from_legacy(["first", "second"]).text == "first"


def test_reasoning_is_never_concatenated_into_the_answer():
    result = GenerationResult(
        parts=[TextPart(text="A "), ReasoningPart(text="private"), TextPart(text="B")]
    )
    assert result.text == "A B"


def test_reasoning_only_result_is_valid_for_later_display():
    assert GenerationResult(parts=[ReasoningPart(text="Partial plan")]).text == ""


def test_legacy_input_cannot_silently_drop_reasoning_parts():
    request = GenerationRequest(
        messages=[
            GenerationMessage(role="assistant", parts=[ReasoningPart(text="Plan")])
        ]
    )
    model = LegacyModel()

    with pytest.raises(ValueError, match="only accepts text"):
        model.generate_result(request)

    model.generate.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": []},
        {"messages": [{"role": "invalid", "parts": [{"type": "text", "text": "x"}]}]},
        {"messages": [{"role": "user", "parts": []}]},
        {"messages": [{"role": "user", "parts": [{"type": "image", "text": "x"}]}]},
        {"messages": [{"role": "user", "parts": [{"type": "text", "text": 42}]}]},
        {
            "messages": [{"role": "user", "parts": [{"type": "text", "text": "x"}]}],
            "unexpected": True,
        },
    ],
)
def test_request_rejects_invalid_or_unsupported_data(payload):
    with pytest.raises(ValidationError):
        GenerationRequest.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt_tokens": -1},
        {"completion_tokens": "5"},
        {"completion_tokens": True},
        {"generation_seconds": -0.1},
        {"generation_seconds": float("nan")},
        {"load_seconds": float("inf")},
        {"total_tokens": 1.5},
    ],
)
def test_usage_rejects_invalid_measurements(payload):
    with pytest.raises(ValidationError):
        GenerationUsage.model_validate(payload)


def test_request_and_results_do_not_share_mutable_data():
    request = GenerationRequest.from_messages(MESSAGES)
    request.messages[0].parts[0].text = "changed"
    assert MESSAGES[0]["content"] == "Keep whitespace."


def test_legacy_input_conversion_does_not_drop_unsupported_fields():
    with pytest.raises(ValueError, match="only role and content"):
        GenerationRequest.from_messages(
            [{"role": "assistant", "content": "Answer", "tool_calls": []}]
        )
