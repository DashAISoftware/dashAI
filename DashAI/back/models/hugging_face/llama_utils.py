import os
from pathlib import Path

import llama_cpp


def is_gpu_available_for_llama_cpp() -> bool:
    """
    Utility method to check if GPU offloading is supported for Llama models.

    Returns:
        bool: True if GPU offloading is supported, False otherwise or if fails.
    """
    try:
        lib = llama_cpp.llama_cpp.load_shared_library(
            "llama", Path(os.path.dirname(llama_cpp.__file__)) / "lib"
        )
        return bool(lib.llama_supports_gpu_offload())
    except Exception:
        return False
