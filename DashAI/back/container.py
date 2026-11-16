import logging
import os
import pathlib
from typing import Dict

from kink import Container, di

from DashAI.back.credentials.encryptor import CredentialEncryptor, load_or_create_key
from DashAI.back.credentials.store import CredentialStore
from DashAI.back.dependencies.database import setup_sqlite_db
from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.plugins.bootstrap import sync_installed_plugins
from DashAI.back.plugins.dependencies import PluginDependencies
from DashAI.back.plugins.disk.storage import PluginStorage
from DashAI.back.plugins.plugin_installer import PluginInstaller
from DashAI.back.plugins.sources import default_sources
from DashAI.back.plugins.store.store import PluginStore, index_url
from DashAI.back.plugins.store.updates import PluginUpdates

logger = logging.getLogger(__name__)


def _github_token():
    """The stored GitHub token if it was verified, else None (see GitHubSource)."""
    store = di["credential_store"]
    if not store.is_verified("GithubCredential"):
        return None
    return store.load("GithubCredential")


def build_container(config: Dict[str, str], load_plugins: bool = True) -> Container:
    """
    Creates a dependency injection container for the application.

    ``load_plugins=False``: the API loads them itself, after recovering what a
    closed dashAI left half done.

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
    credentials_key = load_or_create_key(
        pathlib.Path(config["CREDENTIALS_KEY_PATH"]),
        env_value=os.getenv("DASHAI_CREDENTIALS_SECRET"),
    )
    encryptor = CredentialEncryptor(credentials_key)
    di["credential_encryptor"] = encryptor
    di["credential_store"] = CredentialStore(session_factory, encryptor)
    di["plugin_storage"] = PluginStorage.at(config["LOCAL_PATH"])
    di["plugin_dependencies"] = PluginDependencies(config["LOCAL_PATH"])
    di["plugin_store"] = PluginStore(di["plugin_storage"]) if index_url() else None
    di["plugin_installer"] = PluginInstaller(
        di["plugin_storage"],
        di["component_registry"],
        di["plugin_dependencies"],
        sources=default_sources(github_token=_github_token),
        # Read when needed: the job queue is created just below.
        jobs_running=lambda: di["job_queue"].has_running_jobs(),
        store=di["plugin_store"],
    )
    di["plugin_updates"] = PluginUpdates(
        di["plugin_storage"],
        di["plugin_installer"].sources,
        di["plugin_store"],
        apply_removed=di["plugin_installer"].apply_removed,
    )
    if load_plugins:
        sync_installed_plugins(di["plugin_storage"], di["component_registry"])
    job_queue = HueyJobQueue("job_queue", path_db=config["LOCAL_PATH"])

    di["job_queue"] = job_queue

    return di
