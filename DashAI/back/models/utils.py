import torch

DEVICE_ENUM: list[str] = ["CPU"]
DEVICE_PLACEHOLDER: str = "CPU"
NAME_TO_DEVICE: dict[str, str] = {"CPU": "cpu"}

if torch.cuda.is_available():
    cuda_devices = []
    for i in range(torch.cuda.device_count()):
        cuda_devices.append(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    DEVICE_ENUM = cuda_devices + ["CPU"]
    DEVICE_PLACEHOLDER = f"GPU 0: {torch.cuda.get_device_name(0)}"
    NAME_TO_DEVICE.update({name: f"cuda:{i}" for i, name in enumerate(cuda_devices)})
