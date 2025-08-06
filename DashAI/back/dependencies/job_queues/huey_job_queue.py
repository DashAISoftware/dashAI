# DashAI/back/dependencies/job_queues/huey_job_queue.py


import asyncio
import sqlite3

import dill
from huey import SqliteHuey
from huey.serializer import Serializer as BaseSerializer
from huey.signals import (
    SIGNAL_COMPLETE,
    SIGNAL_ENQUEUED,
    SIGNAL_ERROR,
    SIGNAL_EXECUTING,
)

from DashAI.back.dependencies.job_queues.base_job_queue import (
    BaseJobQueue,
    JobQueueError,
)
from DashAI.back.job.base_job import BaseJob


class DillSerializer(BaseSerializer):
    def _serialize(self, data):
        return dill.dumps(data)

    def _deserialize(self, blob):
        return dill.loads(blob)


class HueyJobQueue(BaseJobQueue):
    """JobQueue implementation using Huey+SQLite."""

    def __init__(self, queue_name: str):
        self.db_path = queue_name.strip() + ".db"
        self.serializer = DillSerializer()
        self.huey = SqliteHuey(
            name=queue_name,
            filename=self.db_path,
            serializer=self.serializer,
            immediate=False,
            immediate_use_memory=False,
        )
        self._ensure_task_copy_table()
        self._register_signals()

        @self.huey.task()
        def _execute_base_job(job: BaseJob):
            result = job.run()
            return result

        self._execute = _execute_base_job

    def _register_signals(self):
        """Attach Huey lifecycle signal handlers to keep 'task_copy' in sync:
        - SIGNAL_ENQUEUED: insert or replace a row with status `not_started`
        - SIGNAL_EXECUTING: update the row to status `started`
        - SIGNAL_COMPLETE: update the row to status `finished`
        - SIGNAL_ERROR: update the row to status `error` and store the
          exception message
        """

        def exec_sql(sql, params=()):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(sql, params)

        @self.huey.signal(SIGNAL_ENQUEUED)
        def on_enqueue(signal, task):
            exec_sql(
                (
                    "INSERT OR REPLACE INTO task_copy "
                    "(id, task_type, status) VALUES (?, ?, ?)"
                ),
                (
                    task.id,
                    task.name,
                    "not_started",
                ),
            )

        @self.huey.signal(SIGNAL_EXECUTING)
        def on_start(signal, task):
            exec_sql(
                (
                    "UPDATE task_copy SET status=?, last_update=CURRENT_TIMESTAMP "
                    "WHERE id=?"
                ),
                ("started", task.id),
            )

        @self.huey.signal(SIGNAL_COMPLETE)
        def on_success(signal, task, *args):
            exec_sql(
                (
                    "UPDATE task_copy SET status=?, last_update=CURRENT_TIMESTAMP "
                    "WHERE id=?"
                ),
                ("finished", task.id),
            )

        @self.huey.signal(SIGNAL_ERROR)
        def on_error(signal, task, exc):
            exec_sql(
                (
                    "UPDATE task_copy SET status=?, last_update=CURRENT_TIMESTAMP, "
                    "error_msg=? WHERE id=?"
                ),
                ("error", str(exc), task.id),
            )

    def _ensure_task_copy_table(self):
        """Ensure the 'task_copy' table exists.

        Columns:
        - id (TEXT PRIMARY KEY): unique identifier for the job (UUID as text)
        - task_type (TEXT NOT NULL): the name of the Huey task
        - enqueued_at (DATETIME NOT NULL): timestamp when the job was enqueued
          (defaults to CURRENT_TIMESTAMP)
        - status (TEXT NOT NULL): current job status, one of:
            'not_started', 'started', 'finished', 'deleted', 'error'
        - last_update (DATETIME NOT NULL): timestamp of the last status change
          (defaults to CURRENT_TIMESTAMP)
        - error_msg (TEXT): optional error message when a task fails
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_copy (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    enqueued_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    error_msg TEXT
                )
                """
            )

    def status(self, job_id: int) -> dict:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, last_update, error_msg
            FROM task_copy WHERE id = ?
            """,
            (job_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            raise JobQueueError(f"No job with id={job_id}")
        return {"status": row[0], "updated": row[1], "error": row[2]}

    def put(self, job: BaseJob) -> int:
        result = self._execute(job)
        return result

    def to_list(self) -> list[BaseJob]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, data FROM task WHERE queue = ? "
                "ORDER BY priority DESC, id ASC",
                (self.huey.storage.name,),
            )
            rows = cur.fetchall()
        jobs = []
        for _, blob in rows:
            payload = self.serializer.loads(blob)
            job = payload[6][0]
            jobs.append(job)
        return jobs

    def peek(self, job_id: int | None = None) -> BaseJob:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            if job_id is not None:
                cur.execute(
                    "SELECT data FROM task WHERE id = ? AND queue = ? LIMIT 1",
                    (job_id, self.huey.storage.name),
                )
            else:
                cur.execute(
                    (
                        "SELECT data FROM task WHERE queue = ? "
                        "ORDER BY priority DESC, id ASC LIMIT 1"
                    ),
                    (self.huey.storage.name,),
                )
            row = cur.fetchone()
        if not row:
            raise JobQueueError("Queue is empty")
        payload = self.serializer.loads(row[0])
        return payload[6][0]

    def get(self, job_id: int | None = None) -> BaseJob:
        with sqlite3.connect(self.db_path) as conn:
            conn.isolation_level = None
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            if job_id is not None:
                cur.execute(
                    "SELECT id, data FROM task WHERE id = ? AND queue = ? LIMIT 1",
                    (job_id, self.huey.storage.name),
                )
            else:
                cur.execute(
                    (
                        "SELECT id, data FROM task WHERE queue = ? "
                        "ORDER BY priority DESC, id ASC LIMIT 1"
                    ),
                    (self.huey.storage.name,),
                )
            row = cur.fetchone()
            if not row:
                conn.execute("ROLLBACK")
                raise JobQueueError("Queue is empty")
            jid, blob = row
            cur.execute("DELETE FROM task WHERE id = ?", (jid,))
            conn.execute("COMMIT")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                (
                    "UPDATE task_copy SET status = ?, last_update = CURRENT_TIMESTAMP "
                    "WHERE id = ?"
                ),
                ("deleted", jid),
            )
        return self.serializer.loads(blob)[6][0]

    def is_empty(self) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM task WHERE queue = ? LIMIT 1", (self.huey.storage.name,)
            )
            empty = cur.fetchone() is None
        return empty

    async def async_get(self) -> BaseJob:
        while True:
            try:
                return self.get()
            except JobQueueError:
                await asyncio.sleep(0.1)


_job_queue = HueyJobQueue("job_queue")
huey = _job_queue.huey


@huey.on_startup()
def create_container_huey():
    import os
    from pathlib import Path

    from DashAI.back.container import build_container
    from DashAI.back.dependencies.config_builder import build_config_dict

    local_path_str = os.environ.get("DASHAI_LOCAL_PATH")
    if local_path_str:
        # Convertir el string a Path y expandir ~ al directorio home
        print("paso por aki pathstr")
        local_path = Path(os.path.expanduser(local_path_str))
    else:
        # Ruta por defecto
        local_path = Path.home() / ".DashAI"

    logging_level = os.environ.get("DASHAI_LOGGING_LEVEL", "INFO")

    config = build_config_dict(local_path=local_path, logging_level=logging_level)
    build_container(config)
