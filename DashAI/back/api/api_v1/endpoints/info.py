import asyncio
import logging

import GPUtil
import psutil
from fastapi import APIRouter, WebSocket

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
    gpus = GPUtil.getGPUs()
    gpu_info = []
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
            }
        )

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
    except Exception:
        await websocket.close()
