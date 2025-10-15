"""Main module for DashAI package.

Contains the main function that is executed when the package is called from the
command line.
"""

import atexit
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


def launch_huey_thread(resolved_local: pathlib.Path, env: dict) -> subprocess.Popen:
    """Launch the Huey consumer in a background thread and ensure cleanup."""
    huey_cmd = [
        sys.executable,
        "-u",
        "-m",
        "huey.bin.huey_consumer",
        "DashAI.back.dependencies.job_queues.huey_job_queue.huey",
        "--delay", "0.1",
        "--backoff", "1",
        "-v",
    ]

    log_path = os.path.join(resolved_local, "huey.log")
    huey_log = open(log_path, "a")

    proc = subprocess.Popen(
        huey_cmd,
        env=env,
        stdout=huey_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # permite matar todo el grupo fácilmente
    )

    def monitor_and_clean():
        try:
            proc.wait()
        except Exception:
            pass

    t = threading.Thread(target=monitor_and_clean, daemon=True)
    t.start()

    def cleanup(*_):
        if proc.poll() is None:
            print(f"\n[DashAI] Terminating Huey consumer (PID={proc.pid})")
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                with suppress(Exception):
                    proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass

    # Ejecutar cleanup al salir
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    return proc


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
    """Main function for DashAI package."""
    logging.getLogger(name=__package__).setLevel(level=logging_level.value)
    logger = logging.getLogger(__name__)

    logger.info("Starting DashAI application.")

    resolved_local = pathlib.Path(local_path).expanduser().absolute()
    os.environ["DASHAI_LOCAL_PATH"] = str(resolved_local)
    os.environ["DASHAI_LOGGING_LEVEL"] = logging_level.value
    child_env = os.environ.copy()

    # Lanzar Huey en hilo supervisado
    logger.info("Starting Huey consumer thread.")
    huey_process = launch_huey_thread(resolved_local, child_env)
    logger.info(f"Started Huey consumer with PID {huey_process.pid}")
    logger.info(f"Huey logs are being written to: {resolved_local / 'huey.log'}")

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
                os.killpg(os.getpgid(huey_process.pid), signal.SIGTERM)
                huey_process.wait(timeout=5)
                if huey_process.poll() is None:
                    huey_process.terminate()


def run():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
