import asyncio
import json
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Dict

from kink import di, inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import NodeRun
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry import ComponentRegistry


log = logging.getLogger(__name__)

_DB_WRITE_LOCK = threading.Lock()


class NodeJob(BaseJob):
    """Execute a single pipeline node and persist run metadata."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        node_run_id = self.kwargs.get("node_run_id")
        if not node_run_id:
            return

        with session_factory() as db:
            node_run: NodeRun | None = db.get(NodeRun, node_run_id)
            if node_run is None:
                raise JobError(f"NodeRun with id {node_run_id} not found.")

            try:
                node_run.set_status_as_delivered()
                self._commit_with_retry(db)
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Error while setting node run status as delivered.") from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        node_run_id = self.kwargs.get("node_run_id")
        if not node_run_id:
            return

        with session_factory() as db:
            node_run: NodeRun | None = db.get(NodeRun, node_run_id)
            if node_run is None:
                raise JobError(f"NodeRun with id {node_run_id} not found.")

            try:
                node_run.set_status_as_error("Node job failed.")
                self._commit_with_retry(db)
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Error while setting node run status as error.") from e

    def get_job_name(self) -> str:
        node_type = self.kwargs.get("node_type", "Node")
        node_id = self.kwargs.get("node_id")
        if node_id:
            return f"{node_type} ({node_id})"
        return str(node_type)

    @inject
    def run(
        self,
        session_factory: "sessionmaker" = lambda di: di["session_factory"],
        component_registry: "ComponentRegistry" = lambda di: di["component_registry"],
    ) -> Dict[str, Any]:
        node_type = self.kwargs.get("node_type")
        node_config = self.kwargs.get("node_config", {})
        context = self.kwargs.get("context", {})
        node_run_id = self.kwargs.get("node_run_id")

        if not node_type:
            raise JobError("Node type is required to execute a node job.")
        if not node_run_id:
            try:
                node_class = component_registry[node_type]["class"]
            except KeyError as e:
                raise JobError(
                    f"Component type {node_type} not found in registry"
                ) from e

            try:
                node_instance = node_class(**node_config)
            except Exception as e:
                raise JobError(
                    f"Error instantiating node {node_type}: {str(e)}"
                ) from e

            return self._run_node_instance(node_instance, context)

        with session_factory() as db:
            node_run: NodeRun | None = db.get(NodeRun, node_run_id)
            if node_run is None:
                raise JobError(f"NodeRun with id {node_run_id} not found.")

            try:
                node_run.set_status_as_started()
                node_run.input = self._safe_payload(context)
                self._commit_with_retry(db)
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Error while setting node run status as started.") from e

        try:
            node_class = component_registry[node_type]["class"]
        except KeyError as e:
            raise JobError(f"Component type {node_type} not found in registry") from e

        try:
            node_instance = node_class(**node_config)
        except Exception as e:
            raise JobError(
                f"Error instantiating node {node_type}: {str(e)}"
            ) from e

        try:
            output = self._run_node_instance(node_instance, context)
        except Exception as e:
            with session_factory() as db:
                node_run = db.get(NodeRun, node_run_id)
                if node_run is None:
                    raise JobError(
                        f"NodeRun with id {node_run_id} not found after failure."
                    ) from e

                try:
                    node_run.set_status_as_error(str(e))
                    self._commit_with_retry(db)
                except exc.SQLAlchemyError as db_error:
                    log.exception(db_error)
                    raise JobError(
                        "Error while setting node run status as error."
                    ) from db_error

            raise

        with session_factory() as db:
            node_run = db.get(NodeRun, node_run_id)
            if node_run is None:
                raise JobError(f"NodeRun with id {node_run_id} not found.")

            try:
                node_run.output = self._safe_payload(output)
                node_run.set_status_as_finished()
                self._commit_with_retry(db)
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Error while setting node run status as finished.") from e

        return output

    @staticmethod
    def _run_node_instance(node_instance: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        result = node_instance.run(context=context)
        if asyncio.iscoroutine(result):
            return asyncio.run(result)
        return result

    @staticmethod
    def _commit_with_retry(
        db,
        attempts: int = 5,
        base_delay: float = 0.1,
        readd: list[Any] | None = None,
    ) -> None:
        readd = readd or []
        with _DB_WRITE_LOCK:
            for attempt in range(attempts):
                try:
                    for obj in readd:
                        if obj is not None:
                            db.add(obj)
                    db.commit()
                    return
                except exc.OperationalError as error:
                    if "database is locked" not in str(error).lower():
                        raise
                    db.rollback()
                    if attempt >= attempts - 1:
                        raise
                    time.sleep(base_delay * (2**attempt))

    @staticmethod
    def _safe_payload(value: Any) -> Any:
        if isinstance(value, dict):
            sanitized: Dict[str, Any] = {}
            for key, item in value.items():
                if key == "dataset":
                    continue
                sanitized_item = NodeJob._safe_payload(item)
                if sanitized_item is not None:
                    sanitized[key] = sanitized_item
            return sanitized
        if isinstance(value, list):
            sanitized_list = []
            for item in value:
                sanitized_item = NodeJob._safe_payload(item)
                if sanitized_item is not None:
                    sanitized_list.append(sanitized_item)
            return sanitized_list
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value)
