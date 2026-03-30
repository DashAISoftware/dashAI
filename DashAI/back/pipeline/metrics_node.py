import logging
from typing import Any, Dict, List

from kink import di

from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.metrics.base_metric import BaseMetric

log = logging.getLogger(__name__)


class MetricsEval(BaseJob):
    """Pipeline node that evaluates the trained model with selected metrics.

    It expects both the split data **and** the trained model factory to
    already be available in the pipeline context (populated by the
    *SplitData* and *TaskAndModel* nodes respectively).

    Parameters
    ----------
    metrics : List[str]
        Names of the metrics to compute (must be registered in the
        component registry).
    """

    def __init__(self, metrics: List[str]) -> None:
        super().__init__(kwargs={"metrics": metrics})
        self.metrics = metrics

    # -- BaseJob interface ---------------------------------------------------

    def set_status_as_delivered(self) -> None:
        log.debug("MetricsEval executed successfully.")

    def set_status_as_error(self) -> None:
        log.error("MetricsEval encountered an error.")

    def get_job_name(self) -> str:
        return "MetricsEval"

    # -- Execution -----------------------------------------------------------

    async def run(
        self,
        context: Dict[str, Any],
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> Dict[str, Any]:
        """Compute metrics for the trained model.

        Reads from ``context``:
        * ``trained_x``, ``trained_y`` – from *TaskAndModel*
        * ``model_factory`` – ``ModelFactory`` instance from *TaskAndModel*

        Returns
        -------
        dict
            ``{"metrics_result": { ... }}`` with per-metric scores.
        """
        factory = context.get("model_factory")
        x = context.get("trained_x")
        y = context.get("trained_y")

        if factory is None or x is None or y is None:
            raise JobError(
                "MetricsEval requires a trained model. "
                "Make sure TaskAndModel runs before this node."
            )

        # Resolve metric classes from registry
        all_metrics = {
            component_dict["name"]: component_dict
            for component_dict in component_registry(di).get_components_by_types(
                select="Metric"
            )
        }

        metric_classes: List[BaseMetric] = []
        for metric_name in self.metrics:
            entry = all_metrics.get(metric_name)
            if entry and entry.get("class"):
                metric_classes.append(entry["class"])
            else:
                log.warning(f"Metric '{metric_name}' not found in registry.")

        if not metric_classes:
            raise JobError("No valid metrics found to evaluate.")

        try:
            model_metrics = factory.evaluate(x, y, metric_classes)
        except Exception as e:
            log.exception(e)
            raise JobError("Metrics calculation failed") from e

        return {
            "metrics_result": {
                "metric_names": self.metrics,
                "results": model_metrics,
            },
        }
