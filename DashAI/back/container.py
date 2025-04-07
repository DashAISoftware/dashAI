import logging
from typing import Dict

from kink import Container, di

from DashAI.back.dependencies.database import setup_sqlite_db
from DashAI.back.dependencies.job_queues import SimpleJobQueue
from DashAI.back.dependencies.registry import ComponentRegistry

logger = logging.getLogger(__name__)


def build_container(config: Dict[str, str]) -> Container:
    """
    Creates a dependency injection container for the application.

    Parameters
    ----------
    config : Dict[str, str]
        A dictionary containing configuration settings.

    Returns
    -------
    Container
        A dependency injection container instance populated with
        essential services. These services include:
            * 'config': The provided configuration dictionary.
            * Engine: The created SQLAlchemy engine for the SQLite database.
            * sessionmaker: A session factory for creating database sessions.
            * ComponentRegistry: The app component registry.
            * BaseJobQueue: The app job queue.
    """
    engine, session_factory = setup_sqlite_db(config)

    di["config"] = config
    di["engine"] = engine
    di["session_factory"] = session_factory
    di["component_registry"] = ComponentRegistry(
        initial_components=config["INITIAL_COMPONENTS"]
    )
    di["job_queue"] = SimpleJobQueue()

    return di
