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

        self.model = model(**self.fixed_parameters)
        self.fitted = False
        if n_labels is not None:
            self._adjust_params_after_init(n_labels)

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

    def _adjust_params_after_init(self, num_labels):
        """
        Adjust model parameters based on the number of labels after model
        initialization.

        This method checks the instantiated model to see if it has num_labels attribute
        and updates it accordingly.

        Parameters
        ----------
        num_labels : int
            Number of unique labels in the classification task.
        """
        # For Hugging Face models
        if hasattr(self.model, "config") and hasattr(self.model.config, "num_labels"):
            self.model.config.num_labels = num_labels
            return

        # For scikit-learn models
        if hasattr(self.model, "n_classes_"):
            self.model.n_classes_ = num_labels
            return

        # For other models that have the num_labels attribute
        if hasattr(self.model, "num_labels"):
            self.model.num_labels = num_labels
            return

    def _extract_parameters(self, parameters: dict) -> dict:
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
        fixed_params = {
            key: (
                param["fixed_value"]
                if isinstance(param, dict) and "optimize" in param
                else param
            )
            for key, param in parameters.items()
        }
        optimizable_params = {
            key: (param["lower_bound"], param["upper_bound"])
            for key, param in parameters.items()
            if isinstance(param, dict) and param.get("optimize") is True
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
