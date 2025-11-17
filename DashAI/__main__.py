"""Main module for DashAI package.

Contains the main function that is executed when the package is called from the
command line.
"""

import logging
import os
import pathlib
import signal
import subprocess
import sys
import threading
import webbrowser
from contextlib import suppress

import typer
import uvicorn
from typing_extensions import Annotated

from DashAI.back.app import create_app
from DashAI.back.core.enums.logging_levels import LoggingLevel


def open_browser() -> None:
    url = "http://localhost:8000/app/"
    webbrowser.open(url=url, new=0, autoraise=True)


def _start_huey_thread() -> threading.Thread:
    from huey.bin.huey_consumer import consumer_main

    def dummy_signal(signalnum, handler):
        return None

    signal.signal = dummy_signal

    sys.argv = [
        "huey_consumer",
        "DashAI.back.dependencies.job_queues.huey_job_queue.huey",
        "--delay",
        "0.1",
        "--backoff",
        "1",
    ]

    t = threading.Thread(target=consumer_main, daemon=True)
    t.start()
    return t


def main(
    local_path: Annotated[
        pathlib.Path,
        typer.Option(
            "--local-path",
            "-lp",
            help="Path where DashAI files will be stored.",
        ),
    ] = "~/.DashAI",  # type: ignore
    logging_level: Annotated[
        LoggingLevel,
        typer.Option(
            "--logging-level",
            "-ll",
            help=(
                "DashAI App Logging level. "
                "Only in DEBUG mode, SQLAlchemy logging is enabled."
            ),
        ),
    ] = LoggingLevel.INFO,
    no_browser: Annotated[
        bool,
        typer.Option(
            "--no-browser",
            "-nb",
            help="Run without automatically opening the browser.",
            is_flag=True,
        ),
    ] = False,
) -> None:
    logging.getLogger(name=__package__).setLevel(level=logging_level.value)
    logger = logging.getLogger(__name__)

    logger.info("Starting DashAI application.")
    huey_process = None

    resolved_local = pathlib.Path(local_path).expanduser().absolute()
    os.environ["DASHAI_LOCAL_PATH"] = str(resolved_local)
    os.environ["DASHAI_LOGGING_LEVEL"] = logging_level.value
    child_env = os.environ.copy()

    logger.info("Starting Huey consumer.")

    if getattr(sys, "frozen", False):
        # Ejecutable PyInstaller: usar hilo embebido (sin -m).
        _start_huey_thread()
        logger.info("Started embedded Huey consumer (thread).")
    else:
        # Desarrollo: proceso externo con python -m.
        huey_cmd = [
            sys.executable,
            "-m",
            "huey.bin.huey_consumer",
            "DashAI.back.dependencies.job_queues.huey_job_queue.huey",
            "--delay",
            "0.1",
            "--backoff",
            "1",
        ]
        huey_process = subprocess.Popen(huey_cmd, env=child_env)
        logger.info(f"Started external Huey consumer (PID: {huey_process.pid})")

    if not no_browser:
        logger.info("Opening browser.")
        timer = threading.Timer(interval=1, function=open_browser)
        timer.start()
    else:
        logger.info("Browser auto-open disabled (--no-browser/-nb).")

    try:
        logger.info("Starting Uvicorn server application.")
        uvicorn.run(
            app=create_app(
                local_path=resolved_local,
                logging_level=logging_level.value,
            ),
            host="127.0.0.1",
            port=8000,
        )
    finally:
        if huey_process:
            logger.info(f"Terminating Huey consumer (PID: {huey_process.pid})")
            with suppress(Exception):
                huey_process.terminate()
                huey_process.wait(timeout=5)


def run():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
