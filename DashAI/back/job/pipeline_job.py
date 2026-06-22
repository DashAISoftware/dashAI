import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List

from kink import di, inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import NodeRun, Pipeline, PipelineRun
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.job.node_job import NodeJob

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

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

            pipeline_run = PipelineRun(
                pipeline_id=pipeline_id,
                steps=steps,
                edges=edges,
            )
            pipeline_run.set_status_as_started()
            db.add(pipeline_run)
            NodeJob._commit_with_retry(db, readd=[pipeline_run])
            db.refresh(pipeline_run)

            log.info(f"Starting pipeline execution for pipeline {pipeline_id}...")
            base_context: Dict[str, Any] = {"pipeline_id": pipeline_id}
            node_contexts: Dict[str, Dict[str, Any]] = {}
            predecessor_map = self._build_predecessor_map(steps, edges)
            successor_map = self._build_successor_map(steps, edges)
            step_map = {step.get("id"): step for step in steps if step.get("id")}

            async def _execute_graph() -> None:
                pending = set(step_map.keys())
                if not pending:
                    raise JobError("Pipeline steps are missing ids.")

                ready = [
                    node_id for node_id in pending if not predecessor_map.get(node_id)
                ]
                if not ready:
                    raise JobError(
                        "No starting nodes found. Check for cycles or missing roots."
                    )

                task_map: Dict[asyncio.Task, str] = {}
                update_lock = asyncio.Lock()
                exclusive_lock = asyncio.Lock()
                exclusive_types = {"TaskAndModel", "Train"}

                async def _run_node(node_id: str) -> None:
                    step = step_map.get(node_id, {})
                    node_type = step.get("type")
                    node_config = step.get("config", {})
                    node_context = self._build_node_context(
                        node_id=node_id,
                        predecessor_map=predecessor_map,
                        node_contexts=node_contexts,
                        base_context=base_context,
                    )
                    node_context["_node_id"] = node_id

                    node_run_id = None
                    try:
                        with session_factory() as run_db:
                            node_run = NodeRun(
                                pipeline_run_id=pipeline_run.id,
                                node_id=node_id,
                                node_type=node_type or "Unknown",
                                config=node_config,
                            )
                            node_run.set_status_as_delivered()
                            run_db.add(node_run)
                            NodeJob._commit_with_retry(run_db, readd=[node_run])
                            node_run_id = node_run.id
                    except exc.OperationalError as e:
                        if "database is locked" in str(e).lower():
                            log.warning("NodeRun insert skipped due to database lock.")
                            node_run_id = None
                        else:
                            raise

                    node_job = NodeJob(
                        node_run_id=node_run_id,
                        node_id=node_id,
                        node_type=node_type,
                        node_config=node_config,
                        context=node_context,
                    )

                    if node_type in exclusive_types:
                        async with exclusive_lock:
                            output = await asyncio.to_thread(node_job.run)
                    else:
                        output = await asyncio.to_thread(node_job.run)

                    async with update_lock:
                        self._update_context(
                            node_context, pipeline, node_type, node_id, output
                        )
                        node_contexts[node_id] = node_context

                async def _schedule(node_id: str) -> None:
                    task = asyncio.create_task(_run_node(node_id))
                    task_map[task] = node_id

                for node_id in ready:
                    await _schedule(node_id)

                while task_map:
                    done, _ = await asyncio.wait(
                        task_map.keys(), return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in done:
                        node_id = task_map.pop(task)
                        pending.discard(node_id)

                        try:
                            task.result()
                        except Exception as e:
                            for pending_task in task_map:
                                pending_task.cancel()
                            raise JobError(
                                f"Error executing node {node_id}: {str(e)}"
                            ) from e

                        for successor in successor_map.get(node_id, []):
                            if successor not in pending:
                                continue
                            predecessors = predecessor_map.get(successor, [])
                            if all(pred in node_contexts for pred in predecessors):
                                await _schedule(successor)

                if pending:
                    raise JobError(
                        "Pipeline execution stalled: unresolved dependencies remain."
                    )

            try:
                asyncio.run(_execute_graph())
                pipeline_run.set_status_as_finished()
                db.add(pipeline)
                db.add(pipeline_run)
                NodeJob._commit_with_retry(db, readd=[pipeline_run, pipeline])
                self.set_status_as_delivered()
                log.info(f"Pipeline {pipeline_id} execution completed successfully.")
            except Exception as e:
                pipeline_run.set_status_as_error(str(e))
                db.add(pipeline_run)
                NodeJob._commit_with_retry(db, readd=[pipeline_run])
                raise

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

    def _build_successor_map(
        self,
        steps: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """Build a mapping source_node_id -> [target_node_ids]."""
        step_ids = {step.get("id") for step in steps if step.get("id")}
        successor_map: Dict[str, List[str]] = {step_id: [] for step_id in step_ids}

        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source in step_ids and target in step_ids:
                successor_map[source].append(target)

        return successor_map

    def _build_node_context(
        self,
        node_id: str,
        predecessor_map: Dict[str, List[str]],
        node_contexts: Dict[str, Dict[str, Any]],
        base_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build execution context for a node from all predecessor branches."""
        if not node_id:
            raise JobError("Pipeline step is missing an id.")

        predecessors = predecessor_map.get(node_id, [])
        if not predecessors:
            return dict(base_context)

        merged_context: Dict[str, Any] = dict(base_context)
        branches: List[Dict[str, Any]] = []
        for predecessor_id in predecessors:
            predecessor_context = node_contexts.get(predecessor_id)
            if predecessor_context is None:
                raise JobError(
                    f"Cannot resolve predecessor context for node {node_id} "
                    f"from source {predecessor_id}."
                )
            branches.append(dict(predecessor_context))
            merged_context.update(predecessor_context)

        merged_context["_branches"] = branches
        return merged_context

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
            exploration_key = (
                node_id or f"DataExploration-{len(aggregated_exploration)}"
            )
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
            if isinstance(current_metrics_result, list):
                for idx, entry in enumerate(current_metrics_result):
                    metrics_key = entry.get("model_node_id") or f"{node_id}-{idx}"
                    aggregated_metrics_result[metrics_key] = {
                        "node_id": node_id,
                        **entry,
                    }
            else:
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
            if isinstance(current_prediction, list):
                for idx, entry in enumerate(current_prediction):
                    prediction_key = entry.get("model_node_id") or f"{node_id}-{idx}"
                    aggregated_prediction[prediction_key] = {
                        "node_id": node_id,
                        **entry,
                    }
            else:
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
