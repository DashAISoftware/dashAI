import pytest

from DashAI.back.models.generation_result import (
    Usage,
    result_from_chat_completion,
)
from DashAI.back.models.hugging_face.gguf_text_generation_base import (
    GGUFTextGenerationModel,
)
from DashAI.back.models.hugging_face.phi_4_mini_instruct_model import (
    Phi4MiniInstructModel,
)

RESPONSE = {
    "choices": [
        {"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59},
}


class _FakeLlama:
    def __init__(self, response):
        self._response = response

    def create_chat_completion(self, **kwargs):
        return self._response


def _model(cls, response):
    m = object.__new__(cls)
    m.model = _FakeLlama(response)
    m.max_tokens = 16
    m.temperature = 0.0
    m.frequency_penalty = 0.0
    return m


@pytest.mark.parametrize("cls", [GGUFTextGenerationModel, Phi4MiniInstructModel])
def test_generate_result_reads_usage_and_finish_reason(cls):
    r = _model(cls, RESPONSE).generate_result([{"role": "user", "content": "x"}])
    assert r.text == "hi"
    assert r.usage == Usage(prompt_tokens=42, completion_tokens=17)
    assert r.finish_reason == "stop"


@pytest.mark.parametrize("cls", [GGUFTextGenerationModel, Phi4MiniInstructModel])
def test_generate_keeps_legacy_list(cls):
    assert _model(cls, RESPONSE).generate([{"role": "user", "content": "x"}]) == ["hi"]


def test_none_content_gives_empty_text():
    resp = {"choices": [{"message": {"content": None}, "finish_reason": "tool_calls"}]}
    assert result_from_chat_completion(resp).to_outputs() == [""]


@pytest.mark.parametrize(
    "resp",
    [
        {"choices": [{"message": {"content": "a"}, "finish_reason": "length"}]},
        {
            "choices": [{"message": {"content": "a"}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 3},
        },
    ],
)
def test_missing_usage_is_none(resp):
    r = result_from_chat_completion(resp)
    assert r.usage is None
    assert r.metadata() == {"version": 1, "finish_reason": "length"}


def test_subclass_overriding_generate_is_respected():
    class Custom(GGUFTextGenerationModel):
        def generate(self, prompt):
            return ["custom"]

    m = _model(Custom, RESPONSE)
    assert m.generate_result([]).to_outputs() == ["custom"]


@pytest.mark.parametrize("base", [GGUFTextGenerationModel, Phi4MiniInstructModel])
def test_subclass_calling_super_generate_terminates(base):
    class Post(base):
        def generate(self, prompt):
            return [s.upper() for s in super().generate(prompt)]

    m = _model(Post, RESPONSE)
    assert m.generate([]) == ["HI"]
    assert m.generate_result([]).to_outputs() == ["HI"]
