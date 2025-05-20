import torch
from sklearn.exceptions import NotFittedError

from DashAI.back.metrics.classification_metric import ClassificationMetric


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

        multiclass = None
        if hasattr(self, "num_labels") and self.num_labels is not None:
            multiclass = self.num_labels > 2

        results = {}
        for split in ["train", "validation", "test"]:
            split_results = {}
            predictions = self.model.predict(x[split])
            for metric in metrics:
                if (
                    isinstance(metric, type)
                    and issubclass(metric, ClassificationMetric)
                    and "multiclass" in metric.score.__code__.co_varnames
                    and multiclass is not None
                ):
                    score = metric.score(y[split], predictions, multiclass=multiclass)
                else:
                    # For metrics that don't accept the multiclass parameter
                    score = metric.score(y[split], predictions)

                split_results[metric.__name__] = score

            results[split] = split_results

        return results
