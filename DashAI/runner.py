# DashAI/runner.py

import signal
import subprocess
import sys
import time
from contextlib import suppress

UVICORN_CMD = [
    sys.executable,
    "-m",
    "uvicorn",
    "DashAI.back.app:create_app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000",
]
HUEY_CMD = [
    sys.executable,
    "-m",
    "huey.bin.huey_consumer",
    "DashAI.back.dependencies.job_queues.huey_job_queue.huey",
    "--delay",
    "0.1",
    "--backoff",
    "1",
]


def _start(cmd):
    p = subprocess.Popen(cmd)
    print(f"Started: {' '.join(cmd)} (pid={p.pid})")
    return p


def main():
    procs = []
    try:
        procs.append(_start(UVICORN_CMD))
        procs.append(_start(HUEY_CMD))
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    sys.exit(ret or 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            with suppress(Exception):
                p.send_signal(signal.SIGTERM)
