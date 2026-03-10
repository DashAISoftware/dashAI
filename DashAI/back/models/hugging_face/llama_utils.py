import logging
import os
import re
import subprocess
import sys
import textwrap
from functools import lru_cache
from pathlib import Path

from packaging.version import Version

logger = logging.getLogger(__name__)

try:
    import llama_cpp
except ImportError:
    llama_cpp = None


@lru_cache(maxsize=1)
def get_llama_gpu_devices_formatted() -> list[str]:
    """
    Return a list of formatted GPU device strings detected by llama_cpp.
    Example: ["GPU 0: NVIDIA GeForce RTX 3070 - Compute Capability 8.6"]
    """
    if llama_cpp is None:
        return []

    # Python code executed in a child process to trigger llama's CUDA init logging
    code = textwrap.dedent(
        """
        import os, re
        from pathlib import Path
        import llama_cpp

        lib = llama_cpp.llama_cpp.load_shared_library(
            "llama", Path(os.path.dirname(llama_cpp.__file__)) / "lib"
        )
        try:
            _ = lib.llama_supports_gpu_offload()
        except Exception:
            pass
        """
    )

    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )

    captured = proc.stdout + proc.stderr

    # Parse the CUDA log output
    pattern = r"Device\s*(\d+):\s*([^,]+),\s*compute capability\s*([\d.]+)"
    formatted_devices = []
    for m in re.finditer(pattern, captured):
        index = int(m.group(1))
        name = m.group(2).strip()
        compute_cap = m.group(3)
        formatted_devices.append(
            f"GPU {index}: {name} - Compute Capability {compute_cap}"
        )

    return formatted_devices


def is_gpu_available_for_llama_cpp() -> bool:
    if llama_cpp is None:
        return False

    try:
        if Version(llama_cpp.__version__) > Version("0.3.0"):
            return __is_gpu_available_for_llama_cpp_v03()
        else:
            return __is_gpu_available_for_llama_cpp_v02()

    except Exception as e:
        logger.warning(
            "Error checking GPU availability for llama_cpp. Will use CPU only.\n"
            f"Details: {e}"
        )
        return False


def __is_gpu_available_for_llama_cpp_v03() -> bool:
    lib = llama_cpp.llama_cpp.load_shared_library(
        "llama", Path(os.path.dirname(llama_cpp.__file__)) / "lib"
    )
    return bool(lib.llama_supports_gpu_offload())


def __is_gpu_available_for_llama_cpp_v02() -> bool:
    lib = llama_cpp.llama_cpp._load_shared_library("llama")
    return hasattr(lib, "ggml_init_cublas")
