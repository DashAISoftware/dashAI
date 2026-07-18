"""Fixtures for RAG API integration tests.

Shares the same client fixture as the api/ tests so that generative
session / prompt endpoints are available.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from DashAI.back.app import create_app
from DashAI.back.dependencies.database.models import Document
from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue


def _create_test_document(client: TestClient, suffix: str = "") -> int:
    """Create a minimal test document in the DB and return its ID.

    Uses ``tempfile.gettempdir()`` for a cross-platform temporary path.
    """
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        doc = Document(
            file_name=f"test_doc{suffix}.txt",
            file_type="txt",
            file_path=os.path.join(tempfile.gettempdir(), f"test_doc{suffix}.txt"),
            file_hash=f"test_hash_123_{suffix}" if suffix else "test_hash_123",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc.id


def remove_dir_with_retry(directory, max_attempts=5, sleep_seconds=1):
    for attempt in range(max_attempts):
        try:
            shutil.rmtree(directory)
            break
        except PermissionError as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")
            time.sleep(sleep_seconds)
    else:
        print(f"Failed to remove directory after {max_attempts} attempts.")


@pytest.fixture(scope="module")
def client(test_path: Path):
    app = create_app(
        local_path=test_path,
        logging_level="ERROR",
    )

    job_queue = app.container._services.get("job_queue")
    if job_queue and isinstance(job_queue, HueyJobQueue):
        job_queue.set_test_mode(True)

    test_client = TestClient(app)
    yield test_client

    if job_queue and isinstance(job_queue, HueyJobQueue):
        job_queue.set_test_mode(False)

    app.container._services["engine"].dispose()
    remove_dir_with_retry(app.container._services["config"]["LOCAL_PATH"])
