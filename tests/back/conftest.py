import os
import pathlib
import shutil
import time
import uuid

import pytest

import DashAI.back.app as dashai_app
from DashAI.back.dependencies.database.migrate import run_migrations
from DashAI.back.dependencies.database.utils import resolve_db_url
from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue
from tests.back.scratch import clear_scratch

TEST_PATH = pathlib.Path("tmp")
TEST_DATASETS_PATH = pathlib.Path("./tests/back/test_datasets")
RANDOM_STATE = 50


@pytest.fixture(scope="session", autouse=True)
def test_path():
    return TEST_PATH


@pytest.fixture(scope="session", autouse=True)
def _clean_scratch_directories():
    """Drop the dataset caches the suite writes outside the repository."""
    clear_scratch()
    yield
    clear_scratch()


@pytest.fixture(scope="session", autouse=True)
def _migrate_the_database_once(tmp_path_factory):
    """Hand every new test app a database that is already migrated.

    Each test module builds its own app on an empty directory, and running
    every Alembic migration from scratch took about 14% of the API tests
    (#1011). The suite migrates one template database instead, and an app
    whose database file does not exist yet starts from a copy of it. The real
    migrate_on_startup still runs afterwards and finds nothing to apply.
    """
    if os.getenv("DATABASE_URL"):
        yield
        return

    template = tmp_path_factory.mktemp("migrated_db") / "db.sqlite"
    run_migrations(db_url=resolve_db_url(template))
    original = dashai_app.migrate_on_startup

    def migrate_from_template(sqlite_file_path: pathlib.Path) -> None:
        if not sqlite_file_path.exists():
            sqlite_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template, sqlite_file_path)
        original(sqlite_file_path=sqlite_file_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(dashai_app, "migrate_on_startup", migrate_from_template)
        yield


@pytest.fixture(scope="session", autouse=True)
def random_state():
    return RANDOM_STATE


@pytest.fixture(scope="session", autouse=True)
def test_datasets_path():
    os.makedirs(TEST_DATASETS_PATH, exist_ok=True)

    # .gitignore
    with open(TEST_DATASETS_PATH / ".gitignore", "w") as f:
        f.write("*")

    return TEST_DATASETS_PATH


@pytest.fixture(name="test_job_queue")
def fixture_test_job_queue():
    """Create a HueyJobQueue instance configured for testing."""
    queue_path = TEST_PATH / "job_queues"
    queue_path.mkdir(parents=True, exist_ok=True)

    queue_name = f"test_queue_{uuid.uuid4().hex}"

    queue = HueyJobQueue(queue_name, path_db=str(queue_path))

    db_file = queue_path / (queue_name.strip() + ".db")

    queue.set_test_mode(immediate=True)

    yield queue

    try:
        remove_dir_with_retry(queue_path)
        if queue_path.exists():
            os.remove(db_file)
            if os.path.exists(f"{db_file}-wal"):
                os.remove(f"{db_file}-wal")
            if os.path.exists(f"{db_file}-shm"):
                os.remove(f"{db_file}-shm")
    except Exception:
        pass


def remove_dir_with_retry(directory, max_attempts=5, sleep_seconds=1):
    for _attempt in range(max_attempts):
        try:
            shutil.rmtree(directory)
            break
        except Exception:
            time.sleep(sleep_seconds)
