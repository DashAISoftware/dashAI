"""Import-order guard for llama_cpp vs torch (issue #1043).

In CUDA builds, importing ``llama_cpp`` before ``torch`` makes torch skip its
NCCL preload, and ``import torch`` then fails with
"undefined symbol: ncclCommShrink". These checks run in a fresh interpreter
because the current test process has already imported both libraries.
"""

import subprocess
import sys
import textwrap


def _run(code: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr


def test_gguf_base_imports_torch_before_llama_cpp():
    _run(
        """
        import sys
        import DashAI.back.models.hugging_face.gguf_text_generation_base  # noqa: F401
        modules = list(sys.modules)
        if "llama_cpp" in modules:
            assert modules.index("torch") < modules.index("llama_cpp"), (
                "llama_cpp was imported before torch"
            )
        """
    )
