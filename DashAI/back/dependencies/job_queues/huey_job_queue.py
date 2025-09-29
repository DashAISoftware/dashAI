import asyncio
import logging
import os
import sqlite3
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

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

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class DillSerializer(BaseSerializer):
    def _serialize(self, data):
        return dill.dumps(data)

    def _deserialize(self, blob):
        return dill.loads(blob)


class HueyJobQueue(BaseJobQueue):
    """JobQueue implementation using Huey+SQLite."""

    def __init__(self, queue_name: str, path_db: str):
        self.db_path = Path(path_db) / (queue_name.strip() + ".db")
        self.serializer = DillSerializer()
        self.huey = SqliteHuey(
            name=queue_name,
            filename=self.db_path,
            serializer=self.serializer,
            immediate=False,
            immediate_use_memory=False,
        )
        self._enable_wal()
        self._ensure_task_copy_table()
        self._register_signals()

        @self.huey.task(context=True, priority=0)
        def _execute_base_job(job: BaseJob, task=None):
            job.kwargs["huey_id"] = task.id
            result = job.run()
            return result

        self._execute = _execute_base_job

    def set_test_mode(self, immediate: bool) -> None:
        """
        Set the immediate mode of the Huey job queue for testing.
        """
        self.huey.immediate = immediate
        self.huey.immediate_use_memory = immediate

    @staticmethod
    def _normalize_to_utc_str(ts: str) -> str:
        """
        Accepts ISO8601 or 'YYYY-MM-DD HH:MM:SS[.ffffff]' with optional 'Z' or offset.
        Returns UTC as 'YYYY-MM-DD HH:MM:SS.ffffff'
        """
        if not ts:
            return "1970-01-01 00:00:00.000000"

        s = ts.strip()

        if s.endswith("Z"):
            s = s[:-1] + "+00:00"

        dt = None
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            try:
                if " " in s and "T" not in s:
                    dt = datetime.fromisoformat(s.replace(" ", "T"))
            except ValueError:
                dt = None

        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue

        if dt is None:
            return "1970-01-01 00:00:00.000000"

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")

    def _register_signals(self):
        """Attach Huey lifecycle signal handlers to keep 'task_copy' in sync:
        - SIGNAL_ENQUEUED: insert or replace a row with status `not_started`
        - SIGNAL_EXECUTING: update the row to status `started`
        - SIGNAL_COMPLETE: update the row to status `finished`
        - SIGNAL_ERROR: update the row to status `error` and store the exception
        All writes stamp last_update with microsecond precision to avoid same-second
        conflicts.
        """

        def exec_sql(sql, params=()):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(sql, params)

        NOW_MICRO = "STRFTIME('%Y-%m-%d %H:%M:%f','now')"

        @self.huey.signal(SIGNAL_ENQUEUED)
        def on_enqueue(signal, task):
            job_type = task.args[0].__class__.__name__
            job_name = None

            try:
                if hasattr(task.args[0], "get_job_name"):
                    job_name = task.args[0].get_job_name()
            except Exception:
                pass

            exec_sql(
                (
                    "INSERT OR REPLACE INTO task_copy "
                    "(id, task_type, job_name, status, last_update) "
                    f"VALUES (?, ?, ?, ?, {NOW_MICRO})"
                ),
                (task.id, job_type, job_name, "not_started"),
            )

        @self.huey.signal(SIGNAL_EXECUTING)
        def on_start(signal, task):
            exec_sql(
                (
                    "UPDATE task_copy SET status = ?, "
                    f"last_update = {NOW_MICRO} "
                    "WHERE id = ?"
                ),
                ("started", task.id),
            )

        @self.huey.signal(SIGNAL_COMPLETE)
        def on_success(signal, task, *args):
            exec_sql(
                (
                    "UPDATE task_copy SET status = ?, "
                    f"last_update = {NOW_MICRO} "
                    "WHERE id = ?"
                ),
                ("finished", task.id),
            )

        @self.huey.signal(SIGNAL_ERROR)
        def on_error(signal, task, exc):
            exec_sql(
                (
                    "UPDATE task_copy SET status = ?, "
                    f"last_update = {NOW_MICRO}, "
                    "error_msg = ? "
                    "WHERE id = ?"
                ),
                ("error", str(exc), task.id),
            )

    def _enable_wal(self):
        """
        Enable Write-Ahead Logging mode in SQLite to improve concurrent reads/writes.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

    def _ensure_task_copy_table(self):
        """Ensure the 'task_copy' table exists.

        Columns:
        - id (TEXT PRIMARY KEY): unique identifier for the job (UUID as text)
        - task_type (TEXT NOT NULL): the name of the Huey task
        - job_name (TEXT): a more descriptive name for the job (from get_job_name)
        - enqueued_at (DATETIME NOT NULL): defaults to CURRENT_TIMESTAMP (UTC)
        - status (TEXT NOT NULL): one of: 'not_started', 'started', 'finished',
        'deleted', 'error'
        - last_update (DATETIME NOT NULL): defaults to CURRENT_TIMESTAMP (UTC)
        - error_msg (TEXT): optional error message when a task fails
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_copy (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    job_name TEXT,
                    enqueued_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    error_msg TEXT
                )
                """
            )
            conn.execute(
                (
                    "CREATE INDEX IF NOT EXISTS idx_task_copy_last_update "
                    "ON task_copy(last_update, id)"
                )
            )

    def status(self, job_id: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, last_update, error_msg, job_name
            FROM task_copy WHERE id = ?
            """,
            (str(job_id),),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            raise JobQueueError(f"No job with id={job_id}")
        return {
            "status": row[0],
            "updated": row[1],
            "error": row[2],
            "job_name": row[3],
        }

    def put(self, job: BaseJob) -> int:
        result = self._execute(job)

        return result

    def to_list(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, task_type, job_name, enqueued_at, status, last_update,
                       error_msg
                FROM task_copy
                ORDER BY last_update DESC
                """
            )
            return [dict(row) for row in cur.fetchall()]

    def changes_since(self, since: str) -> list[dict]:
        """
        Return jobs whose last_update is strictly greater than the given timestamp.
        The 'since' timestamp is normalized to UTC with microseconds to avoid
        same-second race conditions.
        """
        cutoff = self._normalize_to_utc_str(since)
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, task_type, job_name, enqueued_at, status, last_update,
                        error_msg
                FROM task_copy
                WHERE last_update > ?
                ORDER BY last_update DESC
                """,
                (cutoff,),
            )
            return [dict(row) for row in cur.fetchall()]

    def peek(self, job_id: str | None = None) -> BaseJob:
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

    def get(self, job_id: str | None = None) -> BaseJob:
        """
        Get a job from the queue and remove it.
        If job_id is provided, get and remove that specific job.
        Otherwise, get the highest priority job.
        """
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
                    "UPDATE task_copy SET status = ?, "
                    "last_update = STRFTIME('%Y-%m-%d %H:%M:%f','now') "
                    "WHERE id = ?"
                ),
                ("deleted", jid),
            )
        return self.serializer.loads(blob)[6][0]

    def is_empty(self) -> bool:
        """
        Check if the queue is empty.
        Returns False if either:
        1. There are pending tasks in the 'task' table, OR
        2. There are tasks with 'started' status in the 'task_copy' table
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()

            cur.execute(
                "SELECT 1 FROM task WHERE queue = ? LIMIT 1",
                (self.huey.storage.name,),
            )
            task_empty = cur.fetchone() is None

            if not task_empty:
                return False

            cur.execute("SELECT 1 FROM task_copy WHERE status = 'started' LIMIT 1")
            no_started_tasks = cur.fetchone() is None

            return task_empty and no_started_tasks

    async def async_get(self) -> BaseJob:
        while True:
            try:
                return self.get()
            except JobQueueError:
                await asyncio.sleep(0.1)

    def delete_from_db(self, job_id: str) -> bool:
        """
        Delete a job from both task and task_copy tables.

        Args:
            job_id: The UUID of the job to delete

        Returns:
            bool: True if the job was deleted from at least one table
        """
        deleted_from_any = False

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                cur.execute(
                    "SELECT id, data FROM task WHERE queue = ?",
                    (self.huey.storage.name,),
                )

                numeric_id = None
                row_data = None

                for row in cur.fetchall():
                    try:
                        task_data = self.serializer._deserialize(row["data"])
                        if task_data[0] == job_id:
                            numeric_id = row["id"]
                            row_data = task_data
                            break
                    except Exception:
                        continue

                if numeric_id is not None:
                    cur.execute("DELETE FROM task WHERE id = ?", (numeric_id,))
                    try:
                        row_data[6][0].set_status_as_error()
                    except Exception as e:
                        log.exception(f"Error setting job status to error: {e}")
                    deleted_from_any = True

                cur.execute("DELETE FROM task_copy WHERE id = ?", (job_id,))
                if cur.rowcount > 0:
                    deleted_from_any = True

            return deleted_from_any
        except Exception as e:
            log.exception(f"Error deleting job: {e}")
            return False

    def delete_all_jobs(self) -> int:
        """
        Delete all jobs from both task and task_copy tables.

        Returns:
            int: Number of jobs deleted
        """
        deleted_count = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()

                cur.execute(
                    "SELECT id, data FROM task WHERE queue = ?",
                    (self.huey.storage.name,),
                )

                jobs_to_delete = []

                for row in cur.fetchall():
                    try:
                        job_data = self.serializer._deserialize(row["data"])
                        with suppress(Exception):
                            job_data[6][0].set_status_as_error()
                        jobs_to_delete.append(row["id"])
                    except Exception:
                        jobs_to_delete.append(row["id"])

                if jobs_to_delete:
                    placeholders = ",".join(["?"] * len(jobs_to_delete))
                    cur.execute(
                        f"DELETE FROM task WHERE id IN ({placeholders})", jobs_to_delete
                    )
                    deleted_count = cur.rowcount

                cur.execute("DELETE FROM task_copy")
                deleted_count += cur.rowcount

            return deleted_count
        except Exception as e:
            log.exception(f"Error deleting all jobs: {e}")
            return 0


_lp_str = os.environ.get("DASHAI_LOCAL_PATH")
_lp = Path(os.path.expanduser(_lp_str)) if _lp_str else Path.home() / ".DashAI"
_lp.mkdir(parents=True, exist_ok=True)
_job_queue = HueyJobQueue("job_queue", path_db=str(_lp))
huey = _job_queue.huey


@huey.on_startup()
def create_container_huey():
    from DashAI.back.container import build_container
    from DashAI.back.dependencies.config_builder import build_config_dict

    local_path = _lp
    logging_level = os.environ.get("DASHAI_LOGGING_LEVEL", "INFO")

    config = build_config_dict(local_path=local_path, logging_level=logging_level)
    build_container(config)
