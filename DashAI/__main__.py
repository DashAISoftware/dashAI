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
import warnings
import webbrowser
from contextlib import suppress

import typer
from typing_extensions import Annotated

from DashAI.back.core.enums.logging_levels import LoggingLevel

# Suppress noisy third-party startup warnings
warnings.filterwarnings(
    "ignore",
    message=".*mediapipe.*",
    category=UserWarning,
    module="controlnet_aux",
)
warnings.filterwarnings(
    "ignore",
    message=".*Importing from timm.models.layers.*",
    category=FutureWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*Importing from timm.models.registry.*",
    category=FutureWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*Overwriting tiny_vit.*",
    category=UserWarning,
    module="controlnet_aux",
)
warnings.filterwarnings(
    "ignore",
    message=".*found in sys.modules after import.*",
    category=RuntimeWarning,
)


def open_browser() -> None:
    _wait_for_backend_server(timeout=120)
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


def _start_backend_server(
    local_path: pathlib.Path, logging_level: LoggingLevel
) -> None:
    import uvicorn

    from DashAI.back.app import create_app

    app = create_app(
        local_path=local_path,
        logging_level=logging_level.value,
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Uvicorn server on http://127.0.0.1:8000")

    uvicorn.run(
        app=app,
        host="127.0.0.1",
        port=8000,
    )


def _wait_for_backend_server(host="127.0.0.1", port=8000, timeout=15):
    """Wait for the backend server to start by attempting to connect to the specified
    host and port."""
    import socket
    import time

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)
    return False


def _start_webview(local_path: pathlib.Path, logger: logging.Logger) -> None:
    import webview

    window = webview.create_window("DashAI", "http://127.0.0.1:8000", hidden=True)

    def load_logic():
        if _wait_for_backend_server(timeout=120):
            logger.info("Backend server is up. Loading webview.")
            window.load_url("http://127.0.0.1:8000/app/")
            window.show()
        else:
            logger.error("Failed to connect to backend server. Timeout.")
            window.destroy()

    # create cache directory for webview (if doesn't exist)
    cache_dir = local_path / "web_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    webview.start(load_logic, private_mode=False, storage_path=str(cache_dir))


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
    webview: Annotated[
        bool,
        typer.Option(
            "--window-mode",
            "-wm",
            help="Run in windowed mode (using webview).",
            is_flag=True,
        ),
    ] = False,
) -> None:
    import threading

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
        logger.info("Running inside PyInstaller bundle.")
        _start_huey_thread()
        logger.info("Started embedded Huey consumer (thread).")
    else:
        logger.info("Running in development mode.")

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

    try:
        if webview:
            logger.info("Creating FastAPI application...")

            t = threading.Thread(
                target=_start_backend_server,
                args=(resolved_local, logging_level),
                daemon=True,
            )
            t.start()

            _start_webview(local_path=resolved_local, logger=logger)
        else:
            if not no_browser:
                logger.info("Opening browser.")
                timer = threading.Timer(interval=1, function=open_browser)
                timer.start()
            else:
                logger.info("Browser auto-open disabled (--no-browser/-nb).")

            _start_backend_server(
                local_path=resolved_local, logging_level=logging_level
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
