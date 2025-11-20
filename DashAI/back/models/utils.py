import torch

from DashAI.back.models.hugging_face.llama_utils import (
    get_llama_gpu_devices_formatted,
    is_gpu_available_for_llama_cpp,
)

DEVICE_ENUM: list[str] = ["CPU"]
DEVICE_PLACEHOLDER: str = "CPU"
DEVICE_TO_IDX: dict[str, int] = {"CPU": -1}
GPU_OR_CPU: list[str] = ["CPU"]
GPU_OR_CPU_PLACEHOLDER: str = "CPU"

if torch.cuda.is_available():
    GPU_OR_CPU.insert(0, "GPU")
    GPU_OR_CPU_PLACEHOLDER = "GPU"
    cuda_devices = []
    for i in range(torch.cuda.device_count()):
        cuda_devices.append(
            f"GPU {i}: {torch.cuda.get_device_name(i)} - "
            f"Compute Capability {torch.cuda.get_device_capability(i)[0]}."
            f"{torch.cuda.get_device_capability(i)[1]}"
        )
    DEVICE_ENUM = cuda_devices + ["CPU"]
    DEVICE_PLACEHOLDER = DEVICE_ENUM[0]
    DEVICE_TO_IDX.update({name: i for i, name in enumerate(cuda_devices)})

LLAMA_DEVICE_ENUM: list[str] = ["CPU"]
LLAMA_DEVICE_PLACEHOLDER: str = "CPU"
LLAMA_DEVICE_TO_IDX: dict[str, int] = {"CPU": -1}
if is_gpu_available_for_llama_cpp():
    cuda_devices = get_llama_gpu_devices_formatted()
    LLAMA_DEVICE_ENUM = cuda_devices + ["CPU"]
    LLAMA_DEVICE_PLACEHOLDER = LLAMA_DEVICE_ENUM[0]
    LLAMA_DEVICE_TO_IDX.update({name: i - 1 for i, name in enumerate(cuda_devices)})
