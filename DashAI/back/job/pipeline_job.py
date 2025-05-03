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
        db: Session = self.kwargs["db"]
        steps: List[Dict[str, Any]] = self.kwargs.get("steps", [])
        id: int = self.kwargs.get("id", None)
        pipeline: Pipeline = db.get(Pipeline, id)

        if not steps:
            raise JobError("No steps provided to execute the pipeline.")

        log.info("Starting pipeline execution...")

        context: Dict[str, Any] = {"pipeline_id": id}

        for idx, step in enumerate(steps):
            node_id = step.get("id")
            node_type = step.get("type")
            node_label = step.get("label")
            node_config = step.get("config", {})

            log.info(f"Executing node {idx + 1}/{len(steps)}: {node_label} ({node_type})")

            try:
                node_class = component_registry[node_type][0]["class"]
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
                elif node_type == "Train":
                    context["train"] = output["train"]
                    pipeline.train = context["train"]
                elif node_type == "Prediction":
                    context["prediction"] = output["prediction"]
                    pipeline.prediction = context["prediction"]
                elif node_type == "TaskSelector":
                    context["task"] = output["task"]
                elif node_type == "SplitData":
                    context["splits"] = output["splits"]
                elif node_type == "TaskModel":
                    context["model"] = output["model"]
                elif node_type == "Metrics":
                    context["metrics"] = output["metrics"]
                else:
                    context[node_id] = output

                log.info(f"Node {node_id} executed successfully.")

            except Exception as e:
                log.exception(e)
                raise JobError(f"Execution failed on node {node_id} of type {node_type}") from e

        log.info("Pipeline execution completed.")
        db.add(pipeline)
        db.commit()
        self.set_status_as_delivered()


def run_pipeline(sqlite_db_path: Path,  logging_level: int, pipeline_id: int) -> None:
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
            id = pipeline.id
            pipeline_job = PipelineJob(kwargs={"steps": steps, "id": id, "db": db})

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
from DashAI.back.pipeline.TrainNode import Train
from DashAI.back.pipeline.SplitDataNode import SplitData
from DashAI.back.pipeline.PredictionNode import Prediction

component_registry.register("DataLoader", DataLoader)
component_registry.register("DataExploration", DataExploration)
component_registry.register("TaskSelector", TaskSelector)
component_registry.register("Metrics", Metrics)
component_registry.register("Train", Train)
component_registry.register("SplitData", SplitData)
component_registry.register("Prediction", Prediction)

print("Componentes registrados:", component_registry)
