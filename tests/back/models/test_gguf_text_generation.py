"""Tests for the per-checkpoint GGUF text-generation components."""

import pathlib
import sys
from types import SimpleNamespace

import pytest
from kink import di
from llama_cpp import Llama as RealLlama
from llama_cpp.llama_chat_format import Jinja2ChatFormatter

from DashAI.back.dependencies.downloads.downloadable import HFDownloadableMixin
from DashAI.back.initial_components import get_initial_components
from DashAI.back.models.hugging_face import llama_utils
from DashAI.back.models.hugging_face.llama_model import (
    Llama31_8BInstruct,
    Llama32_1BInstruct,
    Llama32_3BInstruct,
)
from DashAI.back.models.hugging_face.mistral_model import (
    Mistral7BInstructV03,
    MistralNemoInstruct2407,
)
from DashAI.back.models.hugging_face.mixtral_model import (
    Mixtral8x7BInstructQ2K,
    Mixtral8x7BInstructQ4KM,
)
from DashAI.back.models.hugging_face.phi_4_mini_instruct_model import (
    Phi4MiniInstructModel,
)
from DashAI.back.models.hugging_face.qwen_model import (
    Qwen3_8B,
    Qwen25_05BInstruct,
    Qwen25_3BInstruct,
    Qwen25_7BInstruct,
    Qwen25_15BInstruct,
)
from DashAI.back.models.hugging_face.smol_lm_model import (
    SmolLM2_17BInstruct,
    SmolLM2_360MInstruct,
)

ALL_CHECKPOINTS = [
    Qwen25_05BInstruct,
    Qwen25_15BInstruct,
    Qwen25_3BInstruct,
    Qwen25_7BInstruct,
    Qwen3_8B,
    SmolLM2_360MInstruct,
    SmolLM2_17BInstruct,
    Llama31_8BInstruct,
    Llama32_1BInstruct,
    Llama32_3BInstruct,
    Mistral7BInstructV03,
    MistralNemoInstruct2407,
    Mixtral8x7BInstructQ4KM,
    Mixtral8x7BInstructQ2K,
]


@pytest.fixture
def component_root(tmp_path):
    sentinel = object()
    old = di["config"] if "config" in di else sentinel  # noqa: SIM401
    di["config"] = {"COMPONENT_PATH": str(tmp_path)}
    yield pathlib.Path(tmp_path)
    if old is sentinel:
        del di["config"]
    else:
        di["config"] = old


@pytest.fixture(autouse=True)
def _isolate_llama_log():
    """Keep the module-level llama.cpp log capture isolated per test."""
    saved = list(llama_utils._log_capture)
    llama_utils.reset_llama_log()
    yield
    llama_utils._log_capture[:] = saved


@pytest.mark.parametrize("cls", ALL_CHECKPOINTS)
def test_checkpoint_is_downloadable(cls):
    assert issubclass(cls, HFDownloadableMixin)
    assert cls.REQUIRES_DOWNLOAD is True
    assert cls.DOWNLOAD_SIZE_BYTES is not None
    assert cls.REPO_ID
    assert cls.GGUF_PATTERN


@pytest.mark.parametrize("cls", ALL_CHECKPOINTS)
def test_hf_repos_single_file_entry(cls):
    assert cls.hf_repos() == [(cls.REPO_ID, "model", [cls.GGUF_PATTERN])]


@pytest.mark.parametrize("cls", ALL_CHECKPOINTS)
def test_metadata_flags_download(cls):
    meta = cls.get_metadata()
    assert meta["requires_download"] is True
    assert meta["download_size_bytes"] == cls.DOWNLOAD_SIZE_BYTES


def test_is_downloaded_reflects_component_dir(component_root):
    cls = Qwen25_05BInstruct
    assert cls.is_downloaded() is False

    repo_dir = component_root / cls.__name__ / cls.REPO_ID.split("/")[-1]
    repo_dir.mkdir(parents=True)
    (repo_dir / "model-q8_0.gguf").write_text("weights")
    assert cls.is_downloaded() is True


def _fake_checkpoint(component_root, cls):
    """Create a fake downloaded GGUF file for ``cls`` under ``component_root``."""
    repo_dir = component_root / cls.__name__ / cls.REPO_ID.split("/")[-1]
    repo_dir.mkdir(parents=True)
    gguf_path = repo_dir / "model-Q4_K_M.gguf"
    gguf_path.write_text("weights")
    return gguf_path


def test_partial_download_is_not_downloaded_and_error_is_actionable(component_root):
    """A repo dir with only non-checkpoint files is not a completed download."""
    cls = Llama32_1BInstruct
    repo_dir = component_root / cls.__name__ / cls.REPO_ID.split("/")[-1]
    repo_dir.mkdir(parents=True)
    (repo_dir / "README.md").write_text("readme")
    (repo_dir / ".cache").mkdir()
    (repo_dir / "model-Q4_K_M.gguf.incomplete").write_text("partial")

    assert cls.is_downloaded() is False

    with pytest.raises(RuntimeError) as exc_info:
        cls._local_gguf_path()

    message = str(exc_info.value)
    assert cls.__name__ in message
    assert cls.REPO_ID in message
    assert cls.GGUF_PATTERN in message
    assert "missing or incomplete" in message
    assert "re-download" in message


def test_matching_gguf_is_downloaded_and_path_resolves(component_root):
    """A file matching GGUF_PATTERN makes the component downloaded."""
    cls = Llama32_1BInstruct
    gguf_path = _fake_checkpoint(component_root, cls)

    assert cls.is_downloaded() is True
    assert cls._local_gguf_path() == gguf_path


def test_qwen_7b_split_shards_are_downloaded_and_first_shard_resolves(
    component_root,
):
    """The 7B q8_0 checkpoint ships split in three shards that must match.

    The shard names carry a ``qwen2.5-7b-instruct-`` prefix and a
    ``-NNNNN-of-NNNNN`` suffix, so a pattern anchored at ``-q8_0`` matches
    nothing: ``snapshot_download`` would fetch no files and the component would
    stay permanently "not downloaded".
    """
    cls = Qwen25_7BInstruct
    repo_dir = component_root / cls.__name__ / cls.REPO_ID.split("/")[-1]
    repo_dir.mkdir(parents=True)
    shards = [
        repo_dir / f"qwen2.5-7b-instruct-q8_0-0000{index}-of-00003.gguf"
        for index in (1, 2, 3)
    ]
    for shard in shards:
        shard.write_text("weights")

    assert cls.is_downloaded() is True
    assert cls._local_gguf_path() == shards[0]


class _FakeLlama:
    """Minimal llama.cpp backend exposing the close lifecycle hook."""

    def __init__(self):
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class _RaisingCloseLlama(_FakeLlama):
    """Backend whose close fails after recording the call."""

    def close(self) -> None:
        self.close_calls += 1
        raise RuntimeError("inner llama close exploded")


def _wrapper_with_backend(cls, backend):
    """Build a model instance around ``backend`` without loading llama.cpp."""
    wrapper = cls.__new__(cls)
    wrapper.model = backend
    return wrapper


#: Trimmed excerpt of the ``chat_template`` shipped in ``Qwen/Qwen3-8B``: the
#: message loop and the generation prompt, including the ``enable_thinking``
#: branch that appends an empty think block. Tool and reasoning branches are
#: omitted because the tests only exercise the rendering path.
QWEN3_STYLE_TEMPLATE = (
    "{%- for message in messages %}"
    "{{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>\\n' }}"
    "{%- endfor %}"
    "{%- if add_generation_prompt %}"
    "{{- '<|im_start|>assistant\\n' }}"
    "{%- if enable_thinking is defined and enable_thinking is false %}"
    "{{- '<think>\\n\\n</think>\\n\\n' }}"
    "{%- endif %}"
    "{%- endif %}"
)

#: Same message loop and generation prompt with no ``enable_thinking`` branch.
PLAIN_CHATML_TEMPLATE = (
    "{%- for message in messages %}"
    "{{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>\\n' }}"
    "{%- endfor %}"
    "{%- if add_generation_prompt %}{{- '<|im_start|>assistant\\n' }}{%- endif %}"
)

_QWEN3_EOS_ID = 151645
_CHAT_TEMPLATE_KEY = "tokenizer.chat_template"
_DEFAULT_CHAT_FORMAT = "chat_template.default"


def _chatml_formatter(template):
    """Build the public Jinja formatter the way llama.cpp does for GGUF metadata."""
    return Jinja2ChatFormatter(
        template=template,
        eos_token="<|im_end|>",
        bos_token="",
        stop_token_ids=[_QWEN3_EOS_ID],
    )


class _FakeLlamaShell:
    """Llama-shaped backend with no weights that reuses the real chat dispatch.

    ``create_chat_completion`` is the installed ``llama_cpp.Llama`` method, so
    handler selection, the Jinja rendering, and the response conversion all run
    for real. Only tokenization and the raw completion call are stubbed. Every
    access to the private ``_chat_handlers`` table is recorded so tests can
    assert that DashAI never reads it.
    """

    create_chat_completion = RealLlama.create_chat_completion

    def __init__(self, template, reply, chat_format=_DEFAULT_CHAT_FORMAT):
        self.metadata = {} if template is None else {_CHAT_TEMPLATE_KEY: template}
        self.chat_format = chat_format
        self.chat_handler = None
        self.verbose = False
        self.reply = reply
        self.completion_calls = []
        self.rendered_prompts = []
        self.private_reads = []
        self.close_calls = 0
        self._template = template

    @property
    def _chat_handlers(self):
        self.private_reads.append("_chat_handlers")
        if self._template is None:
            return {}
        handler = _chatml_formatter(self._template).to_chat_handler()
        return {_DEFAULT_CHAT_FORMAT: handler}

    def token_eos(self):
        return _QWEN3_EOS_ID

    def token_bos(self):
        return -1

    def detokenize(self, tokens, prev_tokens=None, special=False):
        return b"<|im_end|>"

    def tokenize(self, data, add_bos=True, special=False):
        self.rendered_prompts.append(data.decode("utf-8"))
        return [1, 2, 3]

    def create_completion(self, **kwargs):
        self.completion_calls.append(kwargs)
        return {
            "id": "cmpl-fake",
            "object": "text_completion",
            "created": 0,
            "model": "fake",
            "choices": [
                {
                    "text": self.reply,
                    "index": 0,
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def close(self) -> None:
        self.close_calls += 1


def _chat_wrapper(cls, template, reply):
    """Return a model wrapper and its weightless backend (not yet configured)."""
    backend = _FakeLlamaShell(template, reply)
    wrapper = _wrapper_with_backend(cls, backend)
    wrapper.max_tokens = 300
    wrapper.temperature = 0.1
    wrapper.frequency_penalty = 0.1
    return wrapper, backend


def _last_prompt(backend):
    """Return the Jinja-rendered prompt text of the most recent completion."""
    return backend.rendered_prompts[-1]


QWEN3_NO_THINK_PROMPT_TAIL = "<|im_start|>assistant\n<think>\n\n</think>\n\n"


def test_qwen3_generation_renders_empty_think_block():
    """Free-form generation on Qwen3 also gets ``enable_thinking=False``.

    The flag is global for the checkpoint, so this is the documented effect:
    every chat turn starts with an empty think block.
    """
    wrapper, backend = _chat_wrapper(Qwen3_8B, QWEN3_STYLE_TEMPLATE, "hello")
    wrapper._install_chat_template_kwargs()

    assert wrapper.generate([{"role": "user", "content": "hi"}]) == ["hello"]
    assert _last_prompt(backend) == (
        "<|im_start|>user\nhi<|im_end|>\n" + QWEN3_NO_THINK_PROMPT_TAIL
    )


def test_qwen3_function_call_renders_empty_think_block_and_constrains_output():
    """The forced tool call uses the same template and a grammar-constrained call."""
    wrapper, backend = _chat_wrapper(
        Qwen3_8B, QWEN3_STYLE_TEMPLATE, '{"sufficient": true}'
    )
    wrapper._install_chat_template_kwargs()

    result = wrapper.generate_function_call(
        [{"role": "user", "content": "are the chunks enough?"}],
        [{"name": "evaluate_retrieval", "parameters": {"type": "object"}}],
    )

    assert result.name == "evaluate_retrieval"
    assert result.arguments == '{"sufficient": true}'
    assert _last_prompt(backend).endswith(QWEN3_NO_THINK_PROMPT_TAIL)
    assert backend.completion_calls[-1]["grammar"] is not None


def test_qwen3_install_does_not_read_private_chat_handlers():
    """Composition uses the public chat handler and the GGUF template metadata."""
    wrapper, backend = _chat_wrapper(Qwen3_8B, QWEN3_STYLE_TEMPLATE, "hello")

    wrapper._install_chat_template_kwargs()

    assert backend.private_reads == []
    assert backend.chat_handler is not None


def test_qwen3_install_is_idempotent():
    """A second install keeps the same handler and does not render the block twice."""
    wrapper, backend = _chat_wrapper(Qwen3_8B, QWEN3_STYLE_TEMPLATE, "hello")
    wrapper._install_chat_template_kwargs()
    installed = backend.chat_handler

    wrapper._install_chat_template_kwargs()
    wrapper.generate([{"role": "user", "content": "hi"}])

    assert backend.chat_handler is installed
    assert _last_prompt(backend).count("<think>") == 1


def test_non_qwen3_checkpoints_keep_default_chat_handler_and_prompt():
    """Checkpoints without template variables keep llama.cpp's own handler."""
    wrapper, backend = _chat_wrapper(Llama32_1BInstruct, PLAIN_CHATML_TEMPLATE, "hi")

    wrapper._install_chat_template_kwargs()
    wrapper.generate([{"role": "user", "content": "hi"}])

    assert backend.chat_handler is None
    assert (
        _last_prompt(backend)
        == "<|im_start|>user\nhi<|im_end|>\n<|im_start|>assistant\n"
    )


def test_install_without_backend_fails_instead_of_skipping():
    """A Qwen3 model with no backend must not silently report success."""
    wrapper = Qwen3_8B.__new__(Qwen3_8B)
    wrapper.model = None

    with pytest.raises(RuntimeError, match="no llama.cpp backend"):
        wrapper._install_chat_template_kwargs()


def test_install_rejects_chat_format_that_cannot_carry_kwargs():
    """A named builtin format (not a GGUF Jinja template) cannot accept kwargs."""
    backend = _FakeLlamaShell(QWEN3_STYLE_TEMPLATE, "x", chat_format="llama-2")
    wrapper = _wrapper_with_backend(Qwen3_8B, backend)

    with pytest.raises(RuntimeError, match="chat_format"):
        wrapper._install_chat_template_kwargs()
    assert backend.chat_handler is None


def test_install_rejects_missing_chat_template():
    """Without the GGUF template there is nothing to render the variables into."""
    backend = _FakeLlamaShell(None, "x")
    wrapper = _wrapper_with_backend(Qwen3_8B, backend)

    with pytest.raises(RuntimeError, match="chat template"):
        wrapper._install_chat_template_kwargs()


def test_install_rejects_template_that_ignores_kwargs():
    """A template without an ``enable_thinking`` branch would silently ignore it."""
    backend = _FakeLlamaShell(PLAIN_CHATML_TEMPLATE, "x")
    wrapper = _wrapper_with_backend(Qwen3_8B, backend)

    with pytest.raises(RuntimeError, match="enable_thinking"):
        wrapper._install_chat_template_kwargs()
    assert backend.chat_handler is None


def test_install_refuses_to_overwrite_custom_chat_handler():
    """A backend that already routes chats elsewhere is not silently rerouted."""
    backend = _FakeLlamaShell(QWEN3_STYLE_TEMPLATE, "x")
    backend.chat_handler = lambda **kwargs: None
    wrapper = _wrapper_with_backend(Qwen3_8B, backend)

    with pytest.raises(RuntimeError, match="custom chat handler"):
        wrapper._install_chat_template_kwargs()


def test_init_releases_backend_when_chat_template_setup_fails(
    component_root, monkeypatch
):
    """A setup error after the GGUF load closes the backend and reports the cause."""
    cls = Qwen3_8B
    repo_dir = component_root / cls.__name__ / cls.REPO_ID.split("/")[-1]
    repo_dir.mkdir(parents=True)
    (repo_dir / "Qwen3-8B-Q6_K.gguf").write_text("weights")
    backend = _FakeLlamaShell(PLAIN_CHATML_TEMPLATE, "x")
    monkeypatch.setitem(
        sys.modules,
        "llama_cpp",
        SimpleNamespace(Llama=lambda **kwargs: backend),
    )

    with pytest.raises(RuntimeError, match="enable_thinking"):
        cls(
            device="CPU",
            context_window=512,
            max_tokens=10,
            temperature=0.7,
            frequency_penalty=0.1,
        )

    assert backend.close_calls == 1


@pytest.mark.parametrize("cls", [Llama32_1BInstruct, Phi4MiniInstructModel])
def test_close_calls_backend_close_and_is_idempotent(cls):
    backend = _FakeLlama()
    wrapper = _wrapper_with_backend(cls, backend)

    wrapper.close()

    assert backend.close_calls == 1
    assert wrapper.model is None

    wrapper.close()
    assert backend.close_calls == 1


@pytest.mark.parametrize("cls", [Llama32_1BInstruct, Phi4MiniInstructModel])
def test_close_suppresses_backend_failure_and_drops_reference(cls):
    backend = _RaisingCloseLlama()
    wrapper = _wrapper_with_backend(cls, backend)

    wrapper.close()  # must not propagate the inner failure

    assert backend.close_calls == 1
    assert wrapper.model is None


def test_init_wraps_llama_load_failure_for_cpu(component_root, monkeypatch):
    cls = Llama32_1BInstruct
    gguf_path = _fake_checkpoint(component_root, cls)
    original = ValueError("Failed to load model from file: fake.gguf")

    # Simulate a stale GPU free-memory line left behind by an earlier load; the
    # per-load reset must keep it out of this CPU failure report.
    llama_utils._log_capture[:] = [
        "llama_prepare_model_devices: using device CUDA0 (Fake GPU) "
        "(0000:01:00.0) - 0 MiB free\n",
    ]

    def _raise_load_error(*args, **kwargs):
        raise original

    monkeypatch.setitem(
        sys.modules, "llama_cpp", SimpleNamespace(Llama=_raise_load_error)
    )

    with pytest.raises(RuntimeError) as exc_info:
        cls(
            device="CPU",
            context_window=512,
            max_tokens=10,
            temperature=0.7,
            frequency_penalty=0.1,
        )

    message = str(exc_info.value)
    assert cls.__name__ in message
    assert "device: CPU" in message
    assert str(gguf_path) in message
    assert "context_window: 512" in message
    assert "llama.cpp: Failed to load model from file: fake.gguf" in message
    assert "system memory" in message
    assert "MiB free" not in message
    assert exc_info.value.__cause__ is original


def test_build_load_error_reports_gpu_memory_and_ascii_safe_log():
    llama_utils._log_capture[:] = [
        "llama_prepare_model_devices: using device CUDA0 (Fake GPU) "
        "(0000:01:00.0) - 0 MiB free\n",
        "llama_model_load: error loading model: invalid vector subscript\n",
        "print_info: LF token = 198 '\u010a'\n",
    ]

    original = ValueError("llama.cpp failed to load the model")
    error = llama_utils.build_llama_load_error(
        model_label="TestModel",
        model_path="model.gguf",
        device="GPU 0",
        context_window=512,
        original=original,
    )
    message = str(error)

    assert "llama.cpp reported 0 MiB free on CUDA0 (Fake GPU)." in message
    assert "Another GGUF model may already be occupying the GPU" in message
    assert "invalid vector subscript" in message
    assert "llama.cpp: llama.cpp failed to load the model" in message
    assert message.isascii()
    assert "\u010a" not in message


@pytest.mark.parametrize("device", ["CPU", None])
def test_build_load_error_cpu_does_not_report_stale_gpu_memory(device):
    llama_utils._log_capture[:] = [
        "llama_prepare_model_devices: using device CUDA0 (Fake GPU) "
        "(0000:01:00.0) - 0 MiB free\n",
    ]

    error = llama_utils.build_llama_load_error(
        model_label="TestModel",
        model_path="model.gguf",
        device=device,
        context_window=512,
        original=MemoryError("allocation failed"),
    )
    message = str(error)

    assert "device: CPU" in message
    assert "system memory" in message
    assert "llama.cpp reported" not in message
    assert "Another GGUF model may already be occupying the GPU" not in message


def test_load_llama_or_raise_resets_capture_before_loading():
    llama_utils._log_capture[:] = ["stale line\n"]
    seen = {}

    def _loader():
        seen["capture"] = list(llama_utils._log_capture)
        return "loaded"

    result = llama_utils.load_llama_or_raise(
        _loader,
        model_label="TestModel",
        model_path="model.gguf",
        device="CPU",
        context_window=512,
    )

    assert result == "loaded"
    assert seen["capture"] == []


def test_load_llama_or_raise_propagates_unexpected_exception():
    def _raise_type_error():
        raise TypeError("unexpected programming error")

    with pytest.raises(TypeError, match="unexpected programming error"):
        llama_utils.load_llama_or_raise(
            _raise_type_error,
            model_label="TestModel",
            model_path="model.gguf",
            device="CPU",
            context_window=512,
        )


def test_phi4_init_wraps_from_pretrained_failure(monkeypatch):
    original = RuntimeError("Repository not found")

    class _FakeLlama:
        @classmethod
        def from_pretrained(cls, **kwargs):
            assert kwargs["repo_id"] == "unsloth/Phi-4-mini-instruct-GGUF"
            raise original

    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(Llama=_FakeLlama))

    with pytest.raises(RuntimeError) as exc_info:
        Phi4MiniInstructModel(
            model_name="unsloth/Phi-4-mini-instruct-GGUF",
            quantization="Phi-4-mini-instruct.Q8_0.gguf",
            device="CPU",
            context_window=256,
            max_tokens=10,
            temperature=0.7,
            frequency_penalty=0.1,
        )

    message = str(exc_info.value)
    assert "Phi4MiniInstructModel" in message
    assert "unsloth/Phi-4-mini-instruct-GGUF" in message
    assert "Phi-4-mini-instruct.Q8_0.gguf" in message
    assert "llama.cpp: Repository not found" in message
    assert exc_info.value.__cause__ is original


def test_reset_llama_log_clears_capture():
    llama_utils._log_capture[:] = ["first line\n", "second line\n"]

    llama_utils.reset_llama_log()

    assert llama_utils._log_capture == []


def test_log_capture_is_bounded():
    for index in range(llama_utils._LOG_CAPTURE_MAX_LINES + 50):
        llama_utils._capturing_log_cb(0, f"line {index}\n".encode(), None)

    assert len(llama_utils._log_capture) == llama_utils._LOG_CAPTURE_MAX_LINES
    assert llama_utils._log_capture[-1] == (
        f"line {llama_utils._LOG_CAPTURE_MAX_LINES + 49}\n"
    )


def test_recent_llama_log_sanitizes_non_ascii_signal_lines():
    llama_utils._log_capture[:] = [
        "device error: print_info: LF token = 198 '\u010a'\n",
    ]

    tail = llama_utils.recent_llama_log()

    assert tail.isascii()
    assert "\\u010a" in tail
    assert llama_utils.recent_llama_log(max_lines=0) == ""
    assert llama_utils.recent_llama_log(max_chars=0) == ""


def test_new_classes_registered_old_ones_gone():
    registered = {c.__name__ for c in get_initial_components()}
    for cls in ALL_CHECKPOINTS:
        assert cls.__name__ in registered
    for old in {
        "QwenModel",
        "SmolLMModel",
        "LlamaModel",
        "MistralModel",
        "MixtralModel",
    }:
        assert old not in registered
