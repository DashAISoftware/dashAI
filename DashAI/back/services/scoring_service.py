"""Scoring service for model comparison using weighted metric profiles."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from kink import inject

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)


class ScoringService:
    """Service for calculating weighted model comparison scores.

    Profiles are defined at the Task level (BaseTask.SCORING_PROFILES).
    This service fetches them from the registry and applies normalization
    across different metric ranges, producing 0–100 scores per model.

    Component registry is injected when needed via @inject decorator.
    """

    @inject
    def _get_metric_metadata(
        self,
        component_registry: "ComponentRegistry" = lambda di: di["component_registry"],
    ) -> Dict[str, Dict[str, Any]]:
        """Get metric metadata (maximize, normalize_ref) from registry.

        Parameters
        ----------
        component_registry : ComponentRegistry
            Registry to look up metrics (injected).

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Map of metric name (str) to metadata dict.
        """
        metadata = {}
        metrics = component_registry.get_components_by_types(select=["Metric"])
        for metric_dict in metrics:
            name = metric_dict["name"]
            metadata[name] = {
                "maximize": metric_dict.get("metadata", {}).get("maximize"),
                "normalize_ref": metric_dict.get("metadata", {}).get("normalize_ref"),
            }
        return metadata

    @inject
    def _get_all_profiles(
        self,
        component_registry: "ComponentRegistry" = lambda di: di["component_registry"],
    ) -> Dict[str, Dict[str, Any]]:
        """Get all profiles from all tasks in the registry.

        Parameters
        ----------
        component_registry : ComponentRegistry
            Registry to look up tasks and their SCORING_PROFILES (injected).

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Map of profile_id → {description, weights, task_name}.
        """
        all_profiles = {}
        tasks = component_registry.get_components_by_types(select=["Task"])

        for task_dict in tasks:
            task_name = task_dict["name"]
            try:
                # Get task class from registry to access SCORING_PROFILES
                full_task_dict = component_registry[task_name]
                task_class = full_task_dict.get("class")

                if task_class and hasattr(task_class, "SCORING_PROFILES"):
                    profiles = task_class.SCORING_PROFILES
                    for profile_id, profile_data in profiles.items():
                        all_profiles[profile_id] = {
                            "description": profile_data["description"],
                            "weights": profile_data["weights"],
                            "task_name": task_name,
                        }
            except KeyError:
                log.debug(f"Task {task_name} not found in registry")
            except Exception as e:
                log.warning(f"Error accessing SCORING_PROFILES for {task_name}: {e}")

        return all_profiles

    @inject
    def get_available_profiles(
        self,
        task_name: Optional[str],
        component_registry: "ComponentRegistry" = lambda di: di["component_registry"],
    ) -> List[Dict[str, Any]]:
        """Get profiles available for a given task.

        Fetches profiles from the task's SCORING_PROFILES class attribute
        in the registry.

        Parameters
        ----------
        task_name : Optional[str]
            Task class name (e.g., "TabularClassificationTask") or None.
            If None, returns all profiles from all tasks.
        component_registry : ComponentRegistry
            Registry to look up task class (injected).

        Returns
        -------
        List[Dict[str, Any]]
            List of profile dicts with keys: id, description, weights.
        """
        if task_name:
            # Access the task class directly to avoid profile-ID collisions
            # that occur when multiple tasks share the same profile ID keys
            # (e.g. TabularClassificationTask and ImageClassificationTask both
            # define "balanced").
            try:
                full_task_dict = component_registry[task_name]
                task_class = full_task_dict.get("class")
                if task_class and hasattr(task_class, "SCORING_PROFILES"):
                    return [
                        {
                            "id": profile_id,
                            "description": profile_data["description"],
                            "weights": profile_data["weights"],
                        }
                        for profile_id, profile_data in (
                            task_class.SCORING_PROFILES.items()
                        )
                    ]
            except KeyError:
                log.debug(f"Task {task_name} not found in registry")
            except Exception as e:
                log.warning(f"Error accessing SCORING_PROFILES for {task_name}: {e}")
            return []

        # No task specified — return one entry per unique profile ID across all tasks.
        all_profiles = self._get_all_profiles()
        return [
            {
                "id": profile_id,
                "description": profile_data["description"],
                "weights": profile_data["weights"],
            }
            for profile_id, profile_data in all_profiles.items()
        ]

    def normalize_metric_value(
        self,
        value: float,
        maximize: Optional[bool],
        normalize_ref: Optional[float],
        all_values: Optional[List[float]] = None,
    ) -> float:
        """Normalize a metric value to [0, 1] where 1 = best.

        Three strategies:
        1. MAXIMIZE=True  →  clamp(value, 0, 1)
           Handles metrics like CohenKappa/R² that can go negative.
        2. MAXIMIZE=False, fixed normalize_ref (e.g. HammingDistance)
           →  1 − min(value / ref, 1)
        3. MAXIMIZE=False, no fixed ref (MAE, RMSE, LogLoss, TER, …)
           →  data-driven: (maxVal − value) / (maxVal − minVal)

        Parameters
        ----------
        value : float
            The metric value to normalize.
        maximize : Optional[bool]
            Whether higher values are better. None treated as True.
        normalize_ref : Optional[float]
            Fixed reference value for minimize metrics. None → data-driven.
        all_values : Optional[List[float]]
            All values of this metric across the comparison set.
            Used for data-driven normalization.

        Returns
        -------
        float
            Normalized value in [0, 1].
        """
        if maximize is not False:
            # Maximize: clamp to [0, 1]
            return max(0.0, min(1.0, value))

        if normalize_ref is not None:
            # Fixed reference: 1 − min(value / ref, 1)
            return max(0.0, 1.0 - min(value / normalize_ref, 1.0))

        # Data-driven range normalization for unbounded minimize metrics
        if all_values and len(all_values) > 0:
            if len(all_values) == 1:
                return 1.0  # Single value = best by definition
            max_val = max(all_values)
            min_val = min(all_values)
            range_val = max_val - min_val
            if range_val < 1e-9:
                return 1.0  # All tied = all best
            return max(0.0, min(1.0, (max_val - value) / range_val))

        # Fallback when no range available: normalize against log(10)
        # This should rarely occur; ideally all_values is always provided for
        # data-driven metrics. Used only as a safety fallback.
        return max(0.0, 1.0 - min(value / 2.303, 1.0))

    def compute_score(
        self,
        metrics_dict: Dict[str, float],
        profile_id: str,
        metric_ranges: Optional[Dict[str, List[float]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Compute the weighted score [0–100] for a model given its metrics.

        Only metrics present in both the profile and metrics_dict are used.
        Their weights are re-normalized so the score is meaningful even when
        some metrics haven't been computed yet.

        Parameters
        ----------
        metrics_dict : Dict[str, dict]
            Metrics for this model, keyed by metric name
            (e.g., {"Accuracy": {"value": 0.95, "std_value": 0.05}}).
        profile_id : str
            ID of the profile to use.
        metric_ranges : Optional[Dict[str, List[float]]]
            For data-driven normalization: {metric_name: [all_values]}.

        Returns
        -------
        Optional[Dict[str, Any]]
            Dict with:
            - score: float [0, 100]
            - breakdown: List[{metric_name, value, normalized_weight}]
            Or None if no profile metrics are available in this model.
        """
        all_profiles = self._get_all_profiles()
        if profile_id not in all_profiles:
            return None

        profile_data = all_profiles[profile_id]
        profile_weights = profile_data["weights"]
        metric_metadata = self._get_metric_metadata()

        # Find metrics that are both in the profile and in the model data
        available_entries = [
            (metric_name, weight)
            for metric_name, weight in profile_weights.items()
            if metric_name in metrics_dict and metrics_dict[metric_name] is not None
        ]

        if not available_entries:
            return None

        # Re-normalize weights to sum to 1
        total_weight = sum(w for _, w in available_entries)
        score = 0.0
        breakdown = []

        for metric_name, weight in available_entries:
            normalized_weight = weight / total_weight
            value = float(metrics_dict[metric_name]["value"])
            meta = metric_metadata.get(metric_name, {})
            maximize = meta.get("maximize")
            normalize_ref = meta.get("normalize_ref")
            all_values = metric_ranges.get(metric_name) if metric_ranges else None

            normalized = self.normalize_metric_value(
                value, maximize, normalize_ref, all_values
            )
            score += normalized_weight * normalized
            breakdown.append(
                {
                    "metric_name": metric_name,
                    "value": value,
                    "normalized_weight": normalized_weight,
                    "normalized_value": normalized,
                }
            )

        return {"score": score * 100, "breakdown": breakdown}

    def compute_scores_for_comparison(
        self,
        runs_metrics: List[Dict[str, Any]],
        profile_id: str,
    ) -> Dict[int, Optional[Dict[str, Any]]]:
        """Compute scores for all runs in a comparison.

        Collects metric ranges for data-driven normalization, then computes
        per-run scores.

        Parameters
        ----------
        runs_metrics : List[Dict[str, Any]]
            List of dicts, each with:
            - run_id: int
            - metrics: Dict[str, float] (metric name → value)
        profile_id : str
            ID of the profile to use.

        Returns
        -------
        Dict[int, Optional[Dict[str, Any]]]
            Map of run_id → score dict (or None if no profile metrics).
        """
        all_profiles = self._get_all_profiles()
        if profile_id not in all_profiles:
            return {}

        profile_data = all_profiles[profile_id]
        profile_weights = profile_data["weights"]

        # Collect all values for each metric in the profile
        metric_ranges: Dict[str, List[float]] = {
            metric_name: [] for metric_name in profile_weights
        }

        for run_data in runs_metrics:
            metrics = run_data.get("metrics", {})
            for metric_name in profile_weights:
                if metric_name in metrics and metrics[metric_name] is not None:
                    metric_ranges[metric_name].append(
                        float(metrics[metric_name]["value"])
                    )

        # Compute scores
        result = {}
        for run_data in runs_metrics:
            run_id = run_data["run_id"]
            metrics = run_data.get("metrics", {})
            score_data = self.compute_score(metrics, profile_id, metric_ranges)
            result[run_id] = score_data

        return result
