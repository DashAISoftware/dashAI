"""Main module for DashAI package.

Contains the main function that is executed when the package is called from the
command line.
"""

import logging
import pathlib
import threading
import webbrowser

import typer
import uvicorn
from typing_extensions import Annotated

from DashAI.back.app import create_app
from DashAI.back.core.enums.logging_levels import LoggingLevel


def open_browser() -> None:
    url = "http://localhost:8000/app/"
    webbrowser.open(url=url, new=0, autoraise=True)


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
    if not no_browser:
        logger.info("Opening browser.")
        timer = threading.Timer(interval=1, function=open_browser)
        timer.start()
    else:
        logger.info("Browser auto-open disabled (--no-browser/-nb).")

    logger.info("Starting Uvicorn server application.")
    uvicorn.run(
        app=create_app(
            local_path=local_path,
            logging_level=logging_level.value,
        ),
        host="127.0.0.1",
        port=8000,
    )


def run():
    typer.run(main)


if __name__ == "__main__":
    typer.run(main)
