import logging
import os
from pathlib import Path

from packaging.version import Version

logger = logging.getLogger(__name__)

try:
    import llama_cpp
except ImportError:
    llama_cpp = None


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
