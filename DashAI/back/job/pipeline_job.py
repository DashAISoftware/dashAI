import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List

from kink import di, inject

from DashAI.back.dependencies.database.models import Pipeline
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry import ComponentRegistry

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
            session_factory: "sessionmaker" = di["session_factory"]
            with session_factory() as db:
                pipeline: Pipeline | None = db.get(Pipeline, pipeline_id)
                if pipeline and getattr(pipeline, "name", None):
                    return f"Pipeline: {pipeline.name}"
        except Exception:
            pass

        return f"Pipeline ({pipeline_id})"

    @inject
    def run(
        self,
        session_factory: "sessionmaker" = lambda di: di["session_factory"],
        component_registry: "ComponentRegistry" = lambda di: di["component_registry"],
    ) -> None:
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
            edges: List[Dict[str, Any]] = self.kwargs.get("edges", []) or (
                pipeline.edges or []
            )
            if not steps:
                raise JobError("No steps provided to execute the pipeline.")

            pipeline.exploration = None
            pipeline.train = None
            pipeline.prediction = None
            pipeline.split_data = None
            pipeline.task_and_model = None
            pipeline.metrics_result = None

            log.info(f"Starting pipeline execution for pipeline {pipeline_id}...")
            base_context: Dict[str, Any] = {"pipeline_id": pipeline_id}
            node_contexts: Dict[str, Dict[str, Any]] = {}
            predecessor_map = self._build_predecessor_map(steps, edges)

            async def _execute_steps() -> None:
                for idx, step in enumerate(steps):
                    node_id = step.get("id")
                    node_type = step.get("type")
                    node_config = step.get("config", {})
                    predecessor_id = None
                    node_context = None

                    log.debug(
                        f"Pipeline {pipeline_id}: "
                        f"Executing step {idx + 1}/{len(steps)} - "
                        f"{node_type} ({node_id})"
                    )

                    try:
                        node_class = component_registry[node_type]["class"]
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
                        predecessors = predecessor_map.get(node_id, [])
                        predecessor_id = predecessors[0] if predecessors else None
                        node_context = self._build_node_context(
                            node_id=node_id,
                            predecessor_map=predecessor_map,
                            node_contexts=node_contexts,
                            base_context=base_context,
                        )
                        node_context["_node_id"] = node_id
                        if node_context.get("dataset") is not None:
                            dataset_name = node_context.get("dataset_name")
                            try:
                                dataset_cols = len(
                                    list(node_context["dataset"].features.keys())
                                )
                            except Exception:
                                dataset_cols = "<unknown>"
                            log.debug(
                                "Node %s (%s) context from predecessor=%s, "
                                "dataset_name=%s, dataset_columns=%s",
                                node_id,
                                node_type,
                                predecessor_id,
                                dataset_name,
                                dataset_cols,
                            )
                        output = await node_instance.run(context=node_context)
                        self._update_context(
                            node_context, pipeline, node_type, node_id, output
                        )
                        if node_id:
                            node_contexts[node_id] = node_context
                        log.debug(f"Node {node_id} executed successfully.")
                    except Exception as e:
                        dataset_name = "<unknown>"
                        dataset_cols = "<unknown>"
                        if isinstance(node_context, dict):
                            dataset_name = node_context.get("dataset_name", "<unknown>")
                            if node_context.get("dataset") is not None:
                                try:
                                    dataset_cols = len(
                                        list(node_context["dataset"].features.keys())
                                    )
                                except Exception:
                                    dataset_cols = "<unknown>"

                        error_msg = (
                            f"Error in node {node_id} ({node_type}): {str(e)} "
                            f"[predecessor={predecessor_id}, "
                            f"dataset_name={dataset_name}, "
                            f"dataset_columns={dataset_cols}]"
                        )
                        log.exception(error_msg)
                        raise JobError(error_msg) from e

            # Run async nodes in a new event loop
            asyncio.run(_execute_steps())

            log.info(f"Pipeline {pipeline_id} execution completed successfully.")
            db.add(pipeline)
            db.commit()
            self.set_status_as_delivered()

    def _build_predecessor_map(
        self,
        steps: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """Build a mapping target_node_id -> [source_node_ids]."""
        step_ids = {step.get("id") for step in steps if step.get("id")}
        predecessor_map: Dict[str, List[str]] = {step_id: [] for step_id in step_ids}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in step_ids and target in step_ids:
                predecessor_map[target].append(source)

        return predecessor_map

    def _build_node_context(
        self,
        node_id: str,
        predecessor_map: Dict[str, List[str]],
        node_contexts: Dict[str, Dict[str, Any]],
        base_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build execution context for a node from its unique predecessor branch."""
        if not node_id:
            raise JobError("Pipeline step is missing an id.")

        predecessors = predecessor_map.get(node_id, [])
        if len(predecessors) > 1:
            raise JobError(
                f"Node {node_id} has multiple inputs, which is not supported."
            )

        if not predecessors:
            return dict(base_context)

        predecessor_id = predecessors[0]
        predecessor_context = node_contexts.get(predecessor_id)
        if predecessor_context is None:
            raise JobError(
                f"Cannot resolve predecessor context for node {node_id} "
                f"from source {predecessor_id}."
            )

        return dict(predecessor_context)

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
            context["dataset_name"] = output.get(
                "dataset_name", context.get("dataset_name")
            )
        elif node_type == "DataExploration":
            current_node_exploration = output.get("exploration") or {}
            context["exploration"] = current_node_exploration

            aggregated_exploration = (
                dict(pipeline.exploration)
                if isinstance(pipeline.exploration, dict)
                else {}
            )
            exploration_key = node_id or f"DataExploration-{len(aggregated_exploration)}"
            aggregated_exploration[exploration_key] = {
                "dataset_name": context.get("dataset_name")
                or output.get("dataset_name")
                or "Unknown Dataset",
                "explorations": current_node_exploration,
            }
            pipeline.exploration = aggregated_exploration
        elif node_type == "Train":
            current_train = output.get("train") or {}
            context["train"] = current_train
            context["model_node_id"] = node_id

            aggregated_train = (
                dict(pipeline.train) if isinstance(pipeline.train, dict) else {}
            )
            train_key = node_id or f"Train-{len(aggregated_train)}"
            aggregated_train[train_key] = {
                "node_id": node_id,
                "model_node_id": node_id,
                "dataset_name": context.get("dataset_name"),
                **current_train,
            }
            pipeline.train = aggregated_train
        elif node_type == "SplitData":
            context["split_data"] = output.get("split_data")
            pipeline.split_data = context["split_data"]
        elif node_type == "TaskAndModel":
            current_task_and_model = output.get("task_and_model") or {}
            context["task_and_model"] = current_task_and_model
            context["model_node_id"] = node_id

            aggregated_task_and_model = (
                dict(pipeline.task_and_model)
                if isinstance(pipeline.task_and_model, dict)
                else {}
            )
            task_model_key = node_id or f"TaskAndModel-{len(aggregated_task_and_model)}"
            aggregated_task_and_model[task_model_key] = {
                "node_id": node_id,
                "model_node_id": node_id,
                "dataset_name": context.get("dataset_name"),
                **current_task_and_model,
            }
            pipeline.task_and_model = aggregated_task_and_model
        elif node_type == "MetricsEval":
            current_metrics_result = output.get("metrics_result") or {}
            context["metrics_result"] = current_metrics_result

            aggregated_metrics_result = (
                dict(pipeline.metrics_result)
                if isinstance(pipeline.metrics_result, dict)
                else {}
            )
            metrics_key = node_id or f"MetricsEval-{len(aggregated_metrics_result)}"
            aggregated_metrics_result[metrics_key] = {
                "node_id": node_id,
                "model_node_id": context.get("model_node_id"),
                "dataset_name": context.get("dataset_name"),
                "model_name": context.get("model_name"),
                "task_name": context.get("task_name"),
                **current_metrics_result,
            }
            pipeline.metrics_result = aggregated_metrics_result
        elif node_type == "RetrieveModel":
            context["retrieve"] = output.get("retrieve")
        elif node_type == "Prediction":
            current_prediction = output.get("prediction")
            context["prediction"] = current_prediction

            aggregated_prediction = (
                dict(pipeline.prediction)
                if isinstance(pipeline.prediction, dict)
                else {}
            )
            prediction_key = node_id or f"Prediction-{len(aggregated_prediction)}"
            aggregated_prediction[prediction_key] = {
                "node_id": node_id,
                "model_node_id": context.get("model_node_id"),
                "dataset_name": context.get("dataset_name"),
                "model_name": context.get("model_name"),
                "task_name": context.get("task_name"),
                "prediction": current_prediction,
            }
            pipeline.prediction = aggregated_prediction
        else:
            context[node_id] = output
