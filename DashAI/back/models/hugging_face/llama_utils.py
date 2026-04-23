import ctypes
import logging
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

from packaging.version import Version

logger = logging.getLogger(__name__)

try:
    import llama_cpp
except ImportError:
    llama_cpp = None


# llama_log_callback signature: void (*)(ggml_log_level level, const char * text, void * user_data)
_LOG_CB_T = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)

_log_capture: list[str] = []


@_LOG_CB_T
def _capturing_log_cb(level, msg, user_data):
    if not msg:
        return
    try:
        text = msg.decode("utf-8", errors="ignore")
    except Exception:
        return
    _log_capture.append(text)
    logger.debug("llama: %s", text.rstrip("\n"))


def _lib_dir() -> Path:
    return Path(os.path.dirname(llama_cpp.__file__)) / "lib"


@lru_cache(maxsize=1)
def _load_llama_lib():
    """Load llama.dll and install our own log callback so CUDA init output
    can be captured in _log_capture instead of printed to the real stderr."""
    if llama_cpp is None:
        return None
    lib = llama_cpp.llama_cpp.load_shared_library("llama", _lib_dir())
    if hasattr(lib, "llama_log_set"):
        try:
            lib.llama_log_set.argtypes = [_LOG_CB_T, ctypes.c_void_p]
            lib.llama_log_set.restype = None
            lib.llama_log_set(_capturing_log_cb, None)
        except Exception as e:
            logger.debug("llama_log_set failed: %s", e)
    return lib


@lru_cache(maxsize=1)
def _all_ggml_libs() -> tuple:
    """Load every shared lib in llama_cpp/lib/ so backend symbols are reachable."""
    if llama_cpp is None:
        return ()
    if sys.platform.startswith("win"):
        patterns = ("*.dll",)
    elif sys.platform == "darwin":
        patterns = ("*.dylib",)
    else:
        patterns = ("*.so", "*.so.*")

    base = _lib_dir()
    if not base.is_dir():
        return ()

    libs = []
    seen = set()
    for pat in patterns:
        for f in base.glob(pat):
            if f.name in seen:
                continue
            seen.add(f.name)
            try:
                libs.append(ctypes.CDLL(str(f)))
            except OSError as e:
                logger.debug("skip lib %s: %s", f.name, e)
    return tuple(libs)


def _find_symbol(libs, name):
    for lib in libs:
        if hasattr(lib, name):
            return lib
    return None


def _parse_compute_caps(log: str) -> dict[int, str]:
    """Extract `Device N: ..., compute capability X.Y` from captured log."""
    pattern = r"Device\s*(\d+):\s*[^,]+,\s*compute capability\s*([\d.]+)"
    return {int(m.group(1)): m.group(2) for m in re.finditer(pattern, log)}


def _enum_via_cuda_api(libs, caps: dict[int, str]) -> list[str]:
    lib = _find_symbol(libs, "ggml_backend_cuda_get_device_count")
    if lib is None or not hasattr(lib, "ggml_backend_cuda_get_device_description"):
        return []

    lib.ggml_backend_cuda_get_device_count.restype = ctypes.c_int
    lib.ggml_backend_cuda_get_device_description.restype = None
    lib.ggml_backend_cuda_get_device_description.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]

    count = lib.ggml_backend_cuda_get_device_count()
    devices = []
    for i in range(count):
        buf = ctypes.create_string_buffer(256)
        lib.ggml_backend_cuda_get_device_description(i, buf, 256)
        name = buf.value.decode("utf-8", errors="ignore").strip() or "CUDA device"
        cap = caps.get(i)
        if cap:
            devices.append(f"GPU {i}: {name} - Compute Capability {cap}")
        else:
            devices.append(f"GPU {i}: {name}")
    return devices


def _enum_via_ggml_dev_api(libs, caps: dict[int, str]) -> list[str]:
    lib = _find_symbol(libs, "ggml_backend_dev_count")
    required = (
        "ggml_backend_dev_get",
        "ggml_backend_dev_type",
        "ggml_backend_dev_description",
        "ggml_backend_dev_name",
    )
    if lib is None or not all(hasattr(lib, s) for s in required):
        return []

    lib.ggml_backend_dev_count.restype = ctypes.c_size_t
    lib.ggml_backend_dev_get.restype = ctypes.c_void_p
    lib.ggml_backend_dev_get.argtypes = [ctypes.c_size_t]
    lib.ggml_backend_dev_type.restype = ctypes.c_int
    lib.ggml_backend_dev_type.argtypes = [ctypes.c_void_p]
    lib.ggml_backend_dev_description.restype = ctypes.c_char_p
    lib.ggml_backend_dev_description.argtypes = [ctypes.c_void_p]
    lib.ggml_backend_dev_name.restype = ctypes.c_char_p
    lib.ggml_backend_dev_name.argtypes = [ctypes.c_void_p]

    # GGML_BACKEND_DEVICE_TYPE_CPU = 0, GPU = 1, ACCEL = 2
    count = lib.ggml_backend_dev_count()
    devices = []
    gpu_idx = 0
    for i in range(count):
        dev = lib.ggml_backend_dev_get(i)
        if not dev:
            continue
        if lib.ggml_backend_dev_type(dev) == 0:
            continue
        desc = lib.ggml_backend_dev_description(dev) or lib.ggml_backend_dev_name(dev)
        name = desc.decode("utf-8", errors="ignore").strip() if desc else "GPU"
        cap = caps.get(gpu_idx)
        if cap:
            devices.append(f"GPU {gpu_idx}: {name} - Compute Capability {cap}")
        else:
            devices.append(f"GPU {gpu_idx}: {name}")
        gpu_idx += 1
    return devices


@lru_cache(maxsize=1)
def get_llama_gpu_devices_formatted() -> list[str]:
    """GPU device strings visible to llama_cpp (not torch).
    Example: ["GPU 0: NVIDIA GeForce RTX 5080 - Compute Capability 12.0"]
    """
    if llama_cpp is None:
        return []

    try:
        _load_llama_lib()  # installs log callback
        libs = _all_ggml_libs()
        if not libs:
            return []

        # Trigger CUDA init so compute-capability line lands in _log_capture
        cuda_lib = _find_symbol(libs, "ggml_backend_cuda_get_device_count")
        if cuda_lib is not None:
            cuda_lib.ggml_backend_cuda_get_device_count.restype = ctypes.c_int
            try:
                cuda_lib.ggml_backend_cuda_get_device_count()
            except Exception:
                pass

        caps = _parse_compute_caps("".join(_log_capture))
        devices = _enum_via_cuda_api(libs, caps)
        if devices:
            return devices
        return _enum_via_ggml_dev_api(libs, caps)
    except Exception as e:
        logger.warning("Error enumerating llama GPUs: %s", e)
        return []


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
    lib = _load_llama_lib()
    return bool(lib.llama_supports_gpu_offload())


def __is_gpu_available_for_llama_cpp_v02() -> bool:
    lib = llama_cpp.llama_cpp._load_shared_library("llama")
    return hasattr(lib, "ggml_init_cublas")
