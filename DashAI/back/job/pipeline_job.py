import asyncio
import logging
from typing import Any, Dict, List

from kink import di
from sqlalchemy.orm import sessionmaker

from DashAI.back.dependencies.database.models import Pipeline
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)


class PipelineJob(BaseJob):
    def set_status_as_delivered(self) -> None:
        """Pipeline job delivered. No persistent status to update."""
        log.debug("PipelineJob marked as delivered.")

    def set_status_as_error(self) -> None:
        """Pipeline job errored. No persistent status to update."""
        log.debug("PipelineJob marked as error.")

    def get_job_name(self) -> str:
        """Return a descriptive name for the pipeline job."""
        pipeline_id = self.kwargs.get("id")
        if not pipeline_id:
            return "Pipeline"

        try:
            session_factory: sessionmaker = di["session_factory"]
            with session_factory() as db:
                pipeline: Pipeline | None = db.get(Pipeline, pipeline_id)
                if pipeline and getattr(pipeline, "name", None):
                    return f"Pipeline: {pipeline.name}"
        except Exception:
            pass

        return f"Pipeline ({pipeline_id})"

    def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> None:
        """Execute the pipeline synchronously, awaiting async node runs internally."""
        session_factory: sessionmaker = di["session_factory"]
        pipeline_id: int | None = self.kwargs.get("id")

        if not pipeline_id:
            raise JobError("No id provided to execute the pipeline.")

        with session_factory() as db:
            pipeline: Pipeline | None = db.get(Pipeline, pipeline_id)
            if pipeline is None:
                raise JobError(f"Pipeline with id {pipeline_id} not found.")

            steps: List[Dict[str, Any]] = self.kwargs.get("steps", []) or (
                pipeline.steps or []
            )
            if not steps:
                raise JobError("No steps provided to execute the pipeline.")

            log.info(f"Starting pipeline execution for pipeline {pipeline_id}...")
            context: Dict[str, Any] = {"pipeline_id": pipeline_id}

            async def _execute_steps() -> None:
                for idx, step in enumerate(steps):
                    node_id = step.get("id")
                    node_type = step.get("type")
                    node_config = step.get("config", {})

                    log.debug(
                        f"Pipeline {pipeline_id}: Executing step {idx + 1}/{len(steps)} - "
                        f"{node_type} ({node_id})"
                    )

                    try:
                        node_class = component_registry(di)[node_type]["class"]
                    except KeyError as e:
                        error_msg = f"Component type {node_type} not found in registry"
                        raise JobError(
                            f"Error in node {node_id} ({node_type}): {error_msg}"
                        ) from e

                    try:
                        node_instance = node_class(**node_config)
                    except Exception as e:
                        error_msg = f"Error in node {node_id} ({node_type}): {str(e)}"
                        log.exception(error_msg)
                        raise JobError(error_msg) from e

                    try:
                        output = await node_instance.run(context=context)
                        self._update_context(
                            context, pipeline, node_type, node_id, output
                        )
                        log.debug(f"Node {node_id} executed successfully.")
                    except Exception as e:
                        error_msg = (
                            f"Error in node {node_id} ({node_type}): {str(e)}"
                        )
                        log.exception(error_msg)
                        raise JobError(error_msg) from e

            # Run async nodes in a new event loop
            asyncio.run(_execute_steps())

            log.info(f"Pipeline {pipeline_id} execution completed successfully.")
            db.add(pipeline)
            db.commit()
            self.set_status_as_delivered()

    def _update_context(
        self,
        context: Dict[str, Any],
        pipeline: Pipeline,
        node_type: str,
        node_id: str,
        output: Dict[str, Any],
    ) -> None:
        """
        Update the pipeline context and database object based on node type.

        Args:
            context: The pipeline context dictionary
            pipeline: The pipeline database object
            node_type: The type of node that was executed
            node_id: The ID of the node that was executed
            output: The output from the node execution
        """
        if node_type == "DataSelector":
            context["dataset"] = output.get("dataset")
        elif node_type == "DataExploration":
            context["exploration"] = output.get("exploration")
            pipeline.exploration = context["exploration"]
        elif node_type == "Train":
            context["train"] = output.get("train")
            pipeline.train = context["train"]
        elif node_type == "RetrieveModel":
            context["retrieve"] = output.get("retrieve")
        elif node_type == "Prediction":
            context["prediction"] = output.get("prediction")
            pipeline.prediction = context["prediction"]
        else:
            context[node_id] = output
