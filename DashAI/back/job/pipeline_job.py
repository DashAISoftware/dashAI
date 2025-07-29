import logging
from typing import Any, Dict, List

from kink import di, inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.dependencies.database.models import Pipeline

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class PipelineJob(BaseJob):
    def set_status_as_delivered(self) -> None:
        log.info("Pipeline execution finished successfully.")

    async def run(
        self, 
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> None:
        db: Session = self.kwargs["db"]
        id: int = self.kwargs.get("id", None)
        pipeline: Pipeline = db.get(Pipeline, id)
        steps: List[Dict[str, Any]] = self.kwargs.get("steps", []) or pipeline.steps

        if not id:
            raise JobError("No id provided to execute the pipeline.")
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
                node_class = component_registry(di)[node_type]["class"]
            except KeyError:
                raise JobError(f"Component type {node_type} not found in registry.")

            try:
                node_instance = node_class(**node_config)
            except Exception as e:
                log.exception(e)
                raise JobError(f"Error instantiating node {node_id} of type {node_type}") from e

            try:
                output = await node_instance.run(context=context)
                if node_type == "DataSelector":
                    context["dataset"] = output["dataset"]
                elif node_type == "DataExploration":
                    context["exploration"] = output["exploration"]
                    pipeline.exploration = context["exploration"]
                elif node_type == "Train":
                    context["train"] = output["train"]
                    pipeline.train = context["train"]
                elif node_type == "RetrieveModel":
                    context["retrieve"] = output["retrieve"]
                elif node_type == "Prediction":
                    context["prediction"] = output["prediction"]
                    pipeline.prediction = context["prediction"]
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
