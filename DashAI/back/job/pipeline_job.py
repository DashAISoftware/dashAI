import logging
from typing import Any, Dict, List
from pathlib import Path

from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.dependencies.registry import ComponentRegistry

from DashAI.back.dependencies.database.sqlite_database import setup_sqlite_db
from DashAI.back.dependencies.database.models import Pipeline
from DashAI.back.pipeline.registry import component_registry

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class PipelineJob(BaseJob):
    def set_status_as_delivered(self) -> None:
        log.info("Pipeline execution finished successfully.")

    def run(self, component_registry: ComponentRegistry) -> None:
        steps: List[Dict[str, Any]] = self.kwargs.get("steps", [])

        if not steps:
            raise JobError("No steps provided to execute the pipeline.")

        log.info("Starting pipeline execution...")

        context: Dict[str, Any] = {}

        for idx, step in enumerate(steps):
            node_id = step.get("id")
            node_type = step.get("type")
            node_label = step.get("label")
            node_config = step.get("config", {})

            log.info(f"Executing node {idx + 1}/{len(steps)}: {node_label} ({node_type})")

            try:
                node_class = component_registry[node_type]["class"]
            except KeyError:
                raise JobError(f"Component type {node_type} not found in registry.")

            try:
                node_instance = node_class(**node_config)
            except Exception as e:
                log.exception(e)
                raise JobError(f"Error instantiating node {node_id} of type {node_type}") from e

            try:
                output = node_instance.run(context=context)
                if node_type == "DataLoader":
                    context["dataset"] = output["dataset"]
                elif node_type == "DataExploration":
                    context["exploration"] = output["exploration"]
                elif node_type == "TaskSelector":
                    context["task"] = output["task"]
                elif node_type == "Metrics":
                    context["metrics"] = output["metrics"]
                else:
                    context[node_id] = output

                log.info(f"Node {node_id} executed successfully.")
            except Exception as e:
                log.exception(e)
                raise JobError(f"Execution failed on node {node_id} of type {node_type}") from e

        log.info("Pipeline execution completed.")
        self.set_status_as_delivered()


def print_pipeline(sqlite_db_path: Path, logging_level: int, pipeline_id: int = 6) -> None:

    config = {
        "SQLITE_DB_PATH": str(sqlite_db_path),
        "LOGGING_LEVEL": logging_level,
    }

    engine, session_factory = setup_sqlite_db(config)

    with session_factory() as db:
        pipeline = db.get(Pipeline, pipeline_id)

        if pipeline:
            print(f"Steps: {pipeline.steps}")
        else:
            print(f"No se encontró el pipeline con ID {pipeline_id}.")

def run_pipeline(sqlite_db_path: Path,  logging_level: int, pipeline_id: int = 6) -> None:
    config = {
        "SQLITE_DB_PATH": str(sqlite_db_path),
        "LOGGING_LEVEL": logging_level,
    }

    engine, session_factory = setup_sqlite_db(config)

    with session_factory() as db:
        pipeline = db.get(Pipeline, pipeline_id)

        if pipeline:
            print(f"Steps: {pipeline.steps}")

            steps = pipeline.steps
            pipeline_job = PipelineJob(kwargs={"steps": steps})
            pipeline_job.run(component_registry=component_registry)

            try:
                pipeline_job.run(component_registry=component_registry)
                print("✅ Pipeline ejecutado con éxito.")
            except JobError as e:
                print(f"❌ Error al ejecutar el pipeline: {e}")
        else:
            print(f"❌ No se encontró el pipeline con ID {pipeline_id}.")

from DashAI.back.pipeline.DataLoaderNode import DataLoader
from DashAI.back.pipeline.ExplorationNode import DataExploration   
from DashAI.back.pipeline.TaskNode import TaskSelector
from DashAI.back.pipeline.MetricsNode import Metrics

component_registry.register("DataLoader", DataLoader)
component_registry.register("DataExploration", DataExploration)
component_registry.register("TaskSelector", TaskSelector)
component_registry.register("Metrics", Metrics)