import asyncio
import json
import logging
import subprocess

import psutil
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


def get_system_usage():
    # --- CPU ---
    cpu_usage = psutil.cpu_percent(interval=None)

    # --- RAM ---
    virtual_mem = psutil.virtual_memory()
    ram_total = virtual_mem.total / (1024**3)  # GB
    ram_used = virtual_mem.used / (1024**3)
    ram_percent = virtual_mem.percent

    # --- GPU ---
    gpu_info = []

    # --- Try NVIDIA GPUs first ---
    try:
        import GPUtil

        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            gpu_info.append(
                {
                    "id": gpu.id,
                    "name": gpu.name,
                    "load_percent": gpu.load * 100,
                    "vram_total_GB": round(gpu.memoryTotal / 1024, 2),
                    "vram_used_GB": round(gpu.memoryUsed / 1024, 2),
                    "vram_free_GB": round(gpu.memoryFree / 1024, 2),
                    "temperature_C": gpu.temperature,
                    "vendor": "NVIDIA",
                }
            )
    except Exception:
        pass  # GPUtil not available or no NVIDIA GPU

    # --- Try AMD GPUs (rocm-smi) ---
    if not gpu_info:
        try:
            # rocm-smi supports JSON output since ROCm 5.4+
            result = subprocess.run(
                [
                    "rocm-smi",
                    "--showtemp",
                    "--showuse",
                    "--showmeminfo",
                    "vram",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)

            # Data structure may vary by version — handle flexibly
            for gpu_id, gpu_data in data.items():
                temp = gpu_data.get("Temperature (Sensor edge) (C)", 0)
                usage = gpu_data.get("GPU use (%)", 0)
                mem_total = gpu_data.get("VRAM Total Memory (B)", 0) / (1024**3)
                mem_used = gpu_data.get("VRAM Used Memory (B)", 0) / (1024**3)
                mem_free = gpu_data.get("VRAM Free Memory (B)", 0) / (1024**3)

                gpu_info.append(
                    {
                        "id": int(gpu_id.strip("card")),
                        "name": "AMD GPU",
                        "load_percent": usage,
                        "vram_total_GB": round(mem_total, 2),
                        "vram_used_GB": round(mem_used, 2),
                        "vram_free_GB": round(mem_free, 2),
                        "temperature_C": temp,
                        "vendor": "AMD",
                    }
                )
        except Exception:
            pass  # rocm-smi not available or not an AMD system

    # --- Final structure ---
    return {
        "cpu_usage_percent": cpu_usage,
        "ram_total_GB": round(ram_total, 2),
        "ram_used_GB": round(ram_used, 2),
        "ram_usage_percent": ram_percent,
        "gpu_devices": gpu_info,
    }


@router.websocket("/ws/system")
async def system_stats_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            stats = get_system_usage()
            await websocket.send_json(stats)
            await asyncio.sleep(1)  # update every second
    except WebSocketDisconnect:
        log.info("WebSocket disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
        await websocket.close()
