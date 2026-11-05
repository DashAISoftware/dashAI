"""Native Pydantic AI messages, legacy adaptation, and provider-call boundaries."""

from unittest.mock import Mock

import pytest
from pydantic_ai.messages import (
    AudioUrl,
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from DashAI.back.core.generation import (
    from_chat_messages,
    from_legacy_output,
    generate_text,
    text_answer,
    to_chat_messages,
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
    def generate_result(self, messages):
        assert to_chat_messages(messages) == MESSAGES
        return ModelResponse(
            parts=[ThinkingPart("Plan"), TextPart(" Answer\n")],
            usage=RequestUsage(input_tokens=10, output_tokens=5),
            finish_reason="stop",
        )


def test_legacy_subclass_keeps_input_and_answer_exactly():
    model = LegacyModel()
    result = generate_text(model, MESSAGES)

    model.generate.assert_called_once_with(MESSAGES)
    assert isinstance(result, ModelResponse)
    assert text_answer(result) == " Answer\n"
    assert result.finish_reason is None


def test_duck_typed_legacy_plugin_needs_only_generate():
    model = Mock(spec=["generate"])
    model.generate.return_value = ["answer"]

    assert text_answer(generate_text(model, MESSAGES)) == "answer"
    model.generate.assert_called_once_with(MESSAGES)


def test_enriched_model_uses_one_path_and_preserves_native_metadata():
    model = TypedModel()
    result = generate_text(model, MESSAGES)

    model.generate.assert_not_called()
    assert text_answer(result) == " Answer\n"
    assert result.parts[0] == ThinkingPart("Plan")
    assert result.usage.output_tokens == 5
    assert result.finish_reason == "stop"
    encoded = ModelMessagesTypeAdapter.dump_json([result])
    assert ModelMessagesTypeAdapter.validate_json(encoded) == [result]


def test_native_pydantic_ai_model_is_called_without_an_agent_loop():
    calls = []

    def respond(messages, info):
        calls.append(to_chat_messages(messages))
        return ModelResponse(
            parts=[ThinkingPart("Plan"), TextPart("Native answer")],
            usage=RequestUsage(input_tokens=7, output_tokens=3),
            finish_reason="stop",
        )

    result = generate_text(FunctionModel(respond), MESSAGES)

    assert calls == [MESSAGES]
    assert result.text == "Native answer"
    assert result.usage.output_tokens == 3


@pytest.mark.parametrize("native", [False, True])
def test_provider_failure_does_not_repeat_generation(native):
    calls = []

    def fail(*args):
        calls.append(1)
        raise RuntimeError("provider failed")

    model = (
        FunctionModel(fail) if native else Mock(spec=["generate", "generate_result"])
    )
    if not native:
        model.generate_result.side_effect = fail

    with pytest.raises(RuntimeError, match="provider failed"):
        generate_text(model, MESSAGES)

    assert calls == [1]
    if not native:
        model.generate.assert_not_called()


@pytest.mark.parametrize(
    "response", [["invalid"], {"parts": [{"part_kind": "text", "content": 42}]}]
)
def test_invalid_enriched_response_does_not_fall_back_to_legacy(response):
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.return_value = response

    with pytest.raises(ValueError, match="Invalid generation data"):
        generate_text(model, MESSAGES)

    model.generate.assert_not_called()


@pytest.mark.parametrize("output", [None, "answer", [], (), [None], [42], [{}]])
def test_invalid_legacy_output_is_not_silently_stringified(output):
    with pytest.raises((TypeError, ValueError)):
        from_legacy_output(output)


@pytest.mark.parametrize("output", [["first", "second"], ("first", "second")])
def test_legacy_first_reply_convention_and_tuple_support_are_preserved(output):
    assert text_answer(from_legacy_output(output)) == "first"


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "user", "content": None}],
        [{"role": "tool", "content": "x"}],
        [("role", "content")],
    ],
)
def test_invalid_messages_fail_before_any_provider_call(messages):
    model = Mock(spec=["generate"])

    with pytest.raises(ValueError, match="requires at least|Text message"):
        generate_text(model, messages)

    model.generate.assert_not_called()


def test_validation_errors_do_not_repeat_the_content():
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.return_value = {
        "parts": [{"part_kind": "text", "content": {"secret answer": 42}}]
    }

    with pytest.raises(ValueError, match="parts") as error:
        generate_text(model, [{"role": "user", "content": "secret prompt"}])

    assert "secret prompt" not in str(error.value)
    assert "secret answer" not in str(error.value)
    assert "input_value" not in str(error.value)
    model.generate.assert_not_called()


def test_enriched_method_may_return_a_native_response_mapping():
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.return_value = {
        "parts": [{"part_kind": "text", "content": "mapped"}]
    }

    assert text_answer(generate_text(model, MESSAGES)) == "mapped"


def test_non_callable_generate_result_attribute_uses_legacy_path():
    model = Mock(spec=["generate"])
    model.generate.return_value = ["answer"]
    model.generate_result = None

    assert text_answer(generate_text(model, MESSAGES)) == "answer"


def test_reasoning_is_never_concatenated_into_the_stored_answer():
    response = ModelResponse(
        parts=[TextPart("A "), ThinkingPart("private"), TextPart("B")]
    )
    assert text_answer(response) == "A B"


@pytest.mark.parametrize(
    "parts", [[ThinkingPart("Plan")], [ToolCallPart("lookup", {"query": "x"})]]
)
def test_unrepresentable_output_is_rejected_before_plain_text_storage(parts):
    with pytest.raises(ValueError, match="no answer text|cannot store"):
        text_answer(ModelResponse(parts=parts))


@pytest.mark.parametrize(
    "parts", [[ThinkingPart("Plan")], [TextPart("A"), ThinkingPart("Plan")]]
)
def test_legacy_input_cannot_silently_drop_reasoning_parts(parts):
    model = LegacyModel()

    with pytest.raises(ValueError, match="only accepts text"):
        model.generate_result([ModelResponse(parts=parts)])

    model.generate.assert_not_called()


MULTIMODAL_CONTENT = [
    DocumentUrl("https://example.org/file.pdf"),
    ImageUrl("https://example.org/image.png"),
    AudioUrl("https://example.org/audio.mp3"),
    VideoUrl("https://example.org/video.mp4"),
    BinaryContent(data=b"document bytes", media_type="application/pdf"),
]


@pytest.mark.parametrize("content", MULTIMODAL_CONTENT)
def test_native_model_receives_multimodal_content_without_download_or_flattening(
    content,
):
    received = []

    def respond(messages, info):
        received.extend(messages)
        return ModelResponse(parts=[TextPart("Description")])

    messages = [ModelRequest(parts=[UserPromptPart(["Describe this", content])])]
    assert generate_text(FunctionModel(respond), messages).text == "Description"
    assert received[0].parts[0].content == ["Describe this", content]


@pytest.mark.parametrize("content", MULTIMODAL_CONTENT)
def test_legacy_model_rejects_multimodal_input_before_provider_call(content):
    model = LegacyModel()
    messages = [ModelRequest(parts=[UserPromptPart(["Describe this", content])])]

    with pytest.raises(ValueError, match="multimodal"):
        generate_text(model, messages)

    model.generate.assert_not_called()


def test_native_validation_snapshots_input_and_response_without_aliasing():
    messages = from_chat_messages(MESSAGES)
    response = ModelResponse(parts=[TextPart("Answer")])
    model = Mock(spec=["generate_result"])
    model.generate_result.return_value = response

    result = generate_text(model, messages)
    model.generate_result.call_args.args[0][0].parts[0].content = "changed"
    response.parts[0].content = "changed"

    assert to_chat_messages(messages) == MESSAGES
    assert text_answer(result) == "Answer"


def test_mutated_native_dataclass_is_revalidated_at_the_boundary():
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.return_value = ModelResponse(parts=[TextPart(content=42)])
    with pytest.raises(ValueError, match="Invalid generation data"):
        generate_text(model, MESSAGES)
    model.generate.assert_not_called()


@pytest.mark.parametrize(
    "usage",
    [
        RequestUsage(input_tokens=-1),
        RequestUsage(output_tokens=-1),
        RequestUsage(audio_seconds=-1),
        RequestUsage(audio_seconds=float("nan")),
        RequestUsage(audio_seconds=float("inf")),
    ],
)
def test_native_usage_cannot_report_negative_or_nonfinite_measurements(usage):
    model = Mock(spec=["generate", "generate_result"])
    model.generate_result.return_value = ModelResponse(
        parts=[TextPart("ok")], usage=usage
    )

    with pytest.raises(ValueError, match="Invalid generation usage"):
        generate_text(model, MESSAGES)

    model.generate.assert_not_called()


def test_legacy_conversion_keeps_adjacent_text_parts_in_one_assistant_message():
    assert to_chat_messages([ModelResponse(parts=[TextPart("A "), TextPart("B")])]) == [
        {"role": "assistant", "content": "A B"}
    ]


def test_legacy_input_conversion_does_not_drop_unsupported_fields():
    with pytest.raises(ValueError, match="only role"):
        from_chat_messages(
            [{"role": "assistant", "content": "Answer", "tool_calls": []}]
        )


def test_removed_draft_types_stay_importable_with_a_warning():
    from DashAI.back.core import generation

    with pytest.warns(DeprecationWarning, match="pydantic_ai.messages"):
        GenerationResult = generation.GenerationResult
    with pytest.warns(DeprecationWarning, match="ReasoningPart"):
        ReasoningPart = generation.ReasoningPart
    with pytest.warns(DeprecationWarning, match="TextPart"):
        LegacyTextPart = generation.TextPart
    result = GenerationResult(
        parts=[ReasoningPart(text="Plan"), LegacyTextPart(text="Answer")]
    )
    assert result.text == "Answer"
    name = "Missing"
    with pytest.raises(AttributeError):
        getattr(generation, name)


def test_plugin_written_for_the_draft_interface_still_works():
    """Mirrors an enriched plugin that uses request.to_messages() and the DTOs."""
    from DashAI.back.core import generation_legacy as old

    class DraftPlugin:
        def generate_result(self, request):
            assert request.to_messages() == [{"role": "user", "content": "Hi"}]
            assert request.messages[0].role == "user"
            return old.GenerationResult(
                parts=[old.ReasoningPart(text="Plan"), old.TextPart(text="Answer")],
                usage=old.GenerationUsage(
                    prompt_tokens=3, completion_tokens=2, generation_seconds=1.5
                ),
                finish_reason="stop",
            )

    with pytest.warns(DeprecationWarning, match="GenerationResult"):
        response = generate_text(DraftPlugin(), [{"role": "user", "content": "Hi"}])
    assert [type(p) for p in response.parts] == [ThinkingPart, TextPart]
    assert text_answer(response) == "Answer"
    assert (response.usage.input_tokens, response.usage.output_tokens) == (3, 2)
    assert response.finish_reason == "stop"
    assert response.provider_details == {"generation_seconds": 1.5}


def test_unknown_draft_finish_reason_is_kept_in_provider_details():
    from DashAI.back.core import generation_legacy as old

    result = old.GenerationResult(
        parts=[old.TextPart(text="A")], finish_reason="load"
    ).to_model_response()
    assert result.finish_reason is None
    assert result.provider_details == {"finish_reason": "load"}


def test_model_with_only_generate_result_works_and_exposes_generate():
    class Enriched(TextToTextGenerationTaskModel):
        def __init__(self, **kwargs):
            pass

        def generate_result(self, messages):
            return ModelResponse(parts=[ThinkingPart("Plan"), TextPart("Answer")])

    model = Enriched()
    assert generate_text(model, [{"role": "user", "content": "Hi"}]).parts[1].content
    assert model.generate([{"role": "user", "content": "Hi"}]) == ["Answer"]


def test_model_must_override_generate_or_generate_result():
    class Empty(TextToTextGenerationTaskModel):
        def __init__(self, **kwargs):
            pass

    messages = [{"role": "user", "content": "Hi"}]
    with pytest.raises(NotImplementedError):
        Empty().generate(messages)
    with pytest.raises(NotImplementedError):
        generate_text(Empty(), messages)
