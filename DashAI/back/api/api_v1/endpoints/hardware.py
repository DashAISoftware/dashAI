import logging

import psutil
from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

_HAS_CPU_FREQ = hasattr(psutil, "cpu_freq")


def _get_gpu_info() -> list[dict]:
    """Collect GPU info from NVIDIA (via pynvml) and AMD (via rocm-smi)."""
    import platform
    import shutil
    import subprocess

    gpus = []

    # NVIDIA GPUs via pynvml
    try:
        import pynvml

        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            try:
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = utilization.gpu
            except pynvml.NVMLError:
                gpu_util = None
            try:
                temp = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )
            except pynvml.NVMLError:
                temp = None

            gpus.append(
                {
                    "name": name,
                    "vendor": "NVIDIA",
                    "utilization": gpu_util,
                    "temperature": temp,
                    "memory_used": mem_info.used,
                    "memory_total": mem_info.total,
                    "memory_percent": (
                        round(mem_info.used / mem_info.total * 100, 1)
                        if mem_info.total > 0
                        else 0
                    ),
                }
            )
        pynvml.nvmlShutdown()
    except Exception:
        pass

    # AMD GPUs via rocm-smi (Linux) or fallback
    if shutil.which("rocm-smi"):
        try:
            result = subprocess.run(
                [
                    "rocm-smi",
                    "--showuse",
                    "--showtemp",
                    "--showmeminfo",
                    "vram",
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)
                for card_key, card_data in data.items():
                    if not card_key.startswith("card"):
                        continue
                    gpus.append(
                        {
                            "name": card_data.get("Card Series", f"AMD GPU {card_key}"),
                            "vendor": "AMD",
                            "utilization": _parse_float(card_data.get("GPU use (%)")),
                            "temperature": _parse_float(
                                card_data.get("Temperature (Sensor edge) (C)")
                            ),
                            "memory_used": _parse_int(
                                card_data.get("VRAM Total Used Memory (B)")
                            ),
                            "memory_total": _parse_int(
                                card_data.get("VRAM Total Memory (B)")
                            ),
                            "memory_percent": None,
                        }
                    )
                    gpu = gpus[-1]
                    if gpu["memory_used"] is not None and gpu["memory_total"]:
                        gpu["memory_percent"] = round(
                            gpu["memory_used"] / gpu["memory_total"] * 100, 1
                        )
        except Exception:
            pass

    # AMD GPUs via WMI on Windows
    if platform.system() == "Windows" and not any(g["vendor"] == "AMD" for g in gpus):
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | "
                    "Where-Object { $_.Name -match 'AMD|Radeon' } | "
                    "Select-Object Name, AdapterRAM | "
                    "ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                import json

                amd_data = json.loads(result.stdout)
                if isinstance(amd_data, dict):
                    amd_data = [amd_data]
                for card in amd_data:
                    adapter_ram = card.get("AdapterRAM")
                    gpus.append(
                        {
                            "name": card.get("Name", "AMD GPU"),
                            "vendor": "AMD",
                            "utilization": None,
                            "temperature": None,
                            "memory_used": None,
                            "memory_total": adapter_ram,
                            "memory_percent": None,
                        }
                    )
        except Exception:
            pass

    return gpus


def _parse_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except (ValueError, TypeError):
        return None


def _parse_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _collect_stats() -> dict:
    """Collect a snapshot of hardware stats."""
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_freq = psutil.cpu_freq() if _HAS_CPU_FREQ else None
    cpu_count = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)
    per_cpu = psutil.cpu_percent(interval=None, percpu=True)

    mem = psutil.virtual_memory()

    gpus = _get_gpu_info()

    return {
        "cpu": {
            "percent": cpu_percent,
            "per_cpu": per_cpu,
            "frequency_mhz": round(cpu_freq.current, 0) if cpu_freq else None,
            "cores_physical": cpu_count_physical,
            "cores_logical": cpu_count,
        },
        "ram": {
            "percent": mem.percent,
            "used": mem.used,
            "total": mem.total,
            "available": mem.available,
        },
        "gpus": gpus,
    }


@router.get("/")
async def get_hardware_stats():
    """Get a one-time snapshot of hardware stats."""
    return _collect_stats()


@router.websocket("/ws")
async def hardware_stats_websocket(websocket: WebSocket):
    """Stream hardware stats over WebSocket at ~1s intervals."""
    import asyncio
    import contextlib

    await websocket.accept()

    # Prime psutil's cpu_percent (first call returns 0.0)
    psutil.cpu_percent(interval=None)
    psutil.cpu_percent(interval=None, percpu=True)

    try:
        while True:
            stats = _collect_stats()
            await websocket.send_json(stats)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("Hardware WebSocket error: %s", e)
        with contextlib.suppress(Exception):
            await websocket.close(code=1011)
