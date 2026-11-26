import json

from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.models.generation_result import (
    GenerationResult,
    ReasoningPart,
    TextPart,
    ToolCallPart,
    Usage,
)


def test_text_joins_text_parts_only():
    r = GenerationResult(parts=(TextPart("a"), ReasoningPart("x"), TextPart("b")))
    assert r.text == "ab"
    assert r.to_outputs() == ["ab"]


def test_from_outputs_keeps_raw_list():
    raw = ["hello", {"path": "img.png"}]
    r = GenerationResult.from_outputs(raw)
    assert r.to_outputs() is raw
    assert r.parts == (TextPart("hello"),)
    assert r.metadata() is None


def test_metadata_shape():
    r = GenerationResult(
        parts=(ReasoningPart("think"), TextPart("hi"), ToolCallPart("c1", "f", "{}")),
        usage=Usage(prompt_tokens=42, completion_tokens=17),
        finish_reason="stop",
    )
    assert r.usage.total_tokens == 59
    assert r.metadata() == {
        "version": 1,
        "usage": {"prompt_tokens": 42, "completion_tokens": 17},
        "finish_reason": "stop",
        "parts": [
            {"type": "reasoning", "text": "think"},
            {"type": "tool_call", "id": "c1", "name": "f", "arguments": "{}"},
        ],
    }
    json.dumps(r.metadata())


def test_metadata_omits_absent_values():
    r = GenerationResult(parts=(TextPart("hi"),), finish_reason="length")
    assert r.metadata() == {"version": 1, "finish_reason": "length"}


class _LegacyModel(BaseGenerativeModel):
    def __init__(self):
        pass

    def generate(self, input):
        return ["legacy", "second"]


def test_default_generate_result_wraps_generate():
    r = _LegacyModel().generate_result("prompt")
    assert r.to_outputs() == ["legacy", "second"]
    assert r.usage is None
    assert r.finish_reason is None
