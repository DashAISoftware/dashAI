"""Job queue side of plugin dependency changes: running jobs and worker restart."""

import sqlite3
import threading
import time
import uuid
from contextlib import suppress
from unittest.mock import Mock

import pytest

from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue
from DashAI.back.plugins.disk.trash import operation


@pytest.fixture
def queue(tmp_path):
    return HueyJobQueue("plugin_test_queue", path_db=str(tmp_path))


def _add_job(queue, status, pid):
    with sqlite3.connect(queue.db_path) as conn:
        conn.execute(
            "INSERT INTO task_copy (id, task_type, status, pid) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "job", status, pid),
        )


def test_a_started_job_whose_process_is_gone_does_not_block(queue):
    _add_job(queue, "started", 2**31 - 7)

    assert queue.has_running_jobs() is False


def test_worker_restarts_when_plugin_dependencies_changed_after_it_started(queue):
    queue._worker_proc = Mock(**{"is_alive.side_effect": [True, False]})
    queue._worker_in_q = Mock()
    queue._worker_started_at = time.time() - 60
    queue._plugin_restart_marker.parent.mkdir(parents=True, exist_ok=True)
    queue._plugin_restart_marker.touch()

    queue._restart_worker_if_plugins_changed()

    queue._worker_in_q.put.assert_called_once_with(None)  # a clean shutdown
    assert queue._worker_proc is None  # _ensure_worker starts a fresh one


def test_a_job_starts_only_after_a_plugin_operation_ends(queue, monkeypatch):
    started = threading.Event()

    def start_worker():
        started.set()
        raise RuntimeError("the test stops here")

    monkeypatch.setattr(queue, "_restart_worker_if_plugins_changed", start_worker)

    def run_job():
        with suppress(RuntimeError):
            queue._run_in_subprocess(None, "id")

    with operation(queue._plugin_restart_marker.parent):
        job = threading.Thread(target=run_job)
        job.start()
        assert not started.wait(0.3)
    assert started.wait(5)
    job.join(5)


def test_the_embedded_consumer_keeps_the_apis_container(monkeypatch):
    from kink import di

    from DashAI.back import container
    from DashAI.back.dependencies.job_queues import huey_job_queue as queue

    had = "plugin_installer" in di
    previous = di["plugin_installer"] if had else None
    installer = di["plugin_installer"] = object()

    def rebuild(*args, **kwargs):
        raise AssertionError("rebuilt the API's container")

    monkeypatch.setattr(container, "build_container", rebuild)
    ran = []
    monkeypatch.setattr(
        queue._job_queue, "reconcile_interrupted_jobs", lambda: ran.append("reconcile")
    )
    monkeypatch.setattr(
        queue._job_queue, "start_watchdog", lambda interval: ran.append("watchdog")
    )
    monkeypatch.setattr(
        queue._job_queue, "_ensure_worker", lambda: ran.append("worker")
    )

    try:
        queue.create_container_huey()

        assert di["plugin_installer"] is installer
        assert ran == ["reconcile", "watchdog", "worker"]
    finally:
        if had:
            di["plugin_installer"] = previous
        else:
            del di["plugin_installer"]
