import logging

import torch
from sklearn.exceptions import NotFittedError

from DashAI.back.metrics.classification_metric import ClassificationMetric

log = logging.getLogger(__name__)


class ModelFactory:
    """
    A factory class for creating and configuring models.

    Attributes
    ----------
    fixed_parameters : dict
        A dictionary of parameters that are fixed and not intended to be optimized.
    optimizable_parameters : dict
        A dictionary of parameters that are intended to be optimized, with their
        respective lower and upper bounds.
    model : BaseModel
        An instance of the model initialized with the fixed parameters.

    Methods
    -------
    _extract_parameters(parameters: dict) -> tuple
        Extracts fixed and optimizable parameters from a dictionary.
    """

    def __init__(self, model, params: dict, n_labels=None):
        self.fixed_parameters, self.optimizable_parameters = self._extract_parameters(
            params
        )

        self.num_labels = n_labels

        model_constructor_params = self.fixed_parameters.copy()
        if self.num_labels is not None:
            model_constructor_params["num_labels_from_factory"] = self.num_labels

        try:
            self.model = model(**model_constructor_params)
        except TypeError as e:
            if "num_labels_from_factory" in str(e):
                model_constructor_params.pop("num_labels_from_factory", None)
                self.model = model(**model_constructor_params)
            else:
                raise e

        self.fitted = False

        if hasattr(self.model, "optimizable_params"):
            self.optimizable_parameters = self.model.optimizable_params

        if hasattr(self.model, "fit"):
            self.original_fit = self.model.fit
            self.model.fit = self.wrapped_fit

    def wrapped_fit(self, *args, **kwargs):
        """Wrapped version of the model's fit method that handles CUDA
        memory and fitted state."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        result = self.original_fit(*args, **kwargs)
        self.fitted = True
        return result

    def _extract_parameters(self, parameters: dict) -> tuple:
        """
        Extract fixed and optimizable parameters from a dictionary.

        Parameters
        ----------
        parameters : dict
            A dictionary containing parameter names as keys and parameter
            specifications as values.

        Returns
        -------
        tuple
            A tuple containing two dictionaries:
            - fixed_params: A dictionary of parameters that are fixed.
            - optimizable_params: A dictionary of parameters that are intended to
            be optimized.
        """
        fixed_params = {}
        for key, param_spec in parameters.items():
            if isinstance(param_spec, dict):
                fixed_params[key] = param_spec.get("fixed_value", param_spec)
            else:
                fixed_params[key] = param_spec

        optimizable_params = {
            key: (param_spec["lower_bound"], param_spec["upper_bound"])
            for key, param_spec in parameters.items()
            if isinstance(param_spec, dict) and param_spec.get("optimize") is True
        }
        return fixed_params, optimizable_params

    def evaluate(self, x, y, metrics):
        """
        Computes metrics only if the model is fitted.

        Parameters
        ----------
        x : dict
            Dictionary with input data for each split.
        y : dict
            Dictionary with output data for each split.
        metrics : list
            List of metric classes to evaluate.

        Returns
        -------
        dict
            Dictionary with metrics scores for each split.
        """
        if not self.fitted:
            raise NotFittedError("Model must be trained before evaluating metrics.")

        # ✅ Determine if this is a multiclass problem
        multiclass = False
        if hasattr(self, "num_labels") and self.num_labels is not None:
            multiclass = self.num_labels > 2

        results = {}
        for split in ["train", "validation", "test"]:
            split_results = {}

            # ✅ Calculate and store loss if model supports it
            if hasattr(self.model, "evaluate_loss"):
                try:
                    loss_value = self.model.evaluate_loss(x[split], y[split])
                    split_results["Loss"] = loss_value
                    log.info(f"{split.capitalize()} Loss: {loss_value:.4f}")

                    # Store in model for later retrieval
                    if split == "train":
                        self.model.train_loss = loss_value
                    elif split == "validation":
                        self.model.val_loss = loss_value
                    elif split == "test":
                        self.model.test_loss = loss_value

                except Exception as e:
                    log.warning(f"Could not calculate loss for {split}: {e}")

            # Get predictions
            try:
                predictions = self.model.predict(x[split])
            except Exception as e:
                log.error(f"Failed to get predictions for {split}: {e}")
                continue

            # ✅ Auto-detect multiclass from predictions if not already set
            if not multiclass:
                from DashAI.back.metrics.classification_metric import prepare_to_metric

                try:
                    _, pred_labels = prepare_to_metric(y[split], predictions)
                    unique_preds = len(set(pred_labels))
                    multiclass = unique_preds > 2
                    log.info(
                        f"Detected {unique_preds} classes, multiclass={multiclass}"
                    )
                except Exception as e:
                    log.warning(f"Could not auto-detect multiclass: {e}")

            # Calculate metrics
            for metric in metrics:
                metric_name = metric.__name__
                try:
                    # Check if metric is a ClassificationMetric and supports multiclass parameter
                    if isinstance(metric, type) and issubclass(
                        metric, ClassificationMetric
                    ):
                        # Use macro average for multiclass problems
                        if multiclass:
                            # Try to use macro averaging
                            try:
                                from sklearn.metrics import (
                                    f1_score,
                                    precision_score,
                                    recall_score,
                                )

                                from DashAI.back.metrics.classification_metric import (
                                    prepare_to_metric,
                                )

                                true_labels, pred_labels = prepare_to_metric(
                                    y[split], predictions
                                )

                                if metric_name == "F1":
                                    score = f1_score(
                                        true_labels,
                                        pred_labels,
                                        average="macro",
                                        zero_division=0,
                                    )
                                elif metric_name == "Precision":
                                    score = precision_score(
                                        true_labels,
                                        pred_labels,
                                        average="macro",
                                        zero_division=0,
                                    )
                                elif metric_name == "Recall":
                                    score = recall_score(
                                        true_labels,
                                        pred_labels,
                                        average="macro",
                                        zero_division=0,
                                    )
                                else:
                                    # For other metrics, try normal calculation
                                    score = metric.score(y[split], predictions)

                                split_results[metric_name] = score
                                log.info(f"{split} {metric_name}: {score:.4f}")

                            except Exception as e:
                                log.warning(
                                    f"Metric {metric_name} failed for {split} with macro: {e}"
                                )
                                split_results[metric_name] = 0.0
                        else:
                            # Binary classification
                            score = metric.score(y[split], predictions)
                            split_results[metric_name] = score
                    else:
                        # For non-classification metrics
                        score = metric.score(y[split], predictions)
                        split_results[metric_name] = score

                except Exception as e:
                    log.warning(f"Metric {metric_name} failed for {split}: {e}")
                    split_results[metric_name] = 0.0

            results[split] = split_results

        return results
