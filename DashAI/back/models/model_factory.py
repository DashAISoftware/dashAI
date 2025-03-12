import numpy as np
import torch
from sklearn.exceptions import NotFittedError

from DashAI.back.metrics.classification_metric import ClassificationMetric
from DashAI.back.models.scikit_learn.sklearn_like_model import SklearnLikeModel


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

    def __init__(self, model, params: dict, n_labels = None):


        self.fixed_parameters, self.optimizable_parameters = self._extract_parameters(
            params
        )

        if n_labels is not None:
            self._adjust_params_for_num_labels(n_labels, model.__class__)
            self.num_labels = n_labels

        print("LOsparametros son", self.fixed_parameters)
        self.model = model(**self.fixed_parameters)
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

    def _adjust_params_for_num_labels(self, num_labels, model_class):
        """
        Adjust model parameters based on the number of labels.
        
        Parameters
        ----------
        num_labels : int
            Number of unique labels in the classification task.
        model_class : class
            The class of the model being created.
        """
        # Check if it's a scikit-learn model
        if hasattr(model_class, '__mro__') and any('SklearnLikeModel' in str(cls) for cls in model_class.__mro__):
            # For models that explicitly need n_classes
            if hasattr(model_class.__init__, "__code__"):
                init_params = model_class.__init__.__code__.co_varnames
                if "n_classes" in init_params and "n_classes" not in self.fixed_parameters:
                    self.fixed_parameters["n_classes"] = num_labels
                elif "n_components" in init_params and "n_components" not in self.fixed_parameters:
                    self.fixed_parameters["n_components"] = num_labels

                
        # Check if it's a HuggingFace model 
        else:
            self.fixed_parameters["num_labels"] = num_labels

        print("model_class es", str(model_class).lower())

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

        # Determine if we're dealing with multiclass classification
        # based on the number of unique labels in training data
        multiclass = None
        if hasattr(self, "num_labels") and self.num_labels is not None:
            multiclass = self.num_labels > 2

        results = {}
        for split in ["train", "validation", "test"]:
            split_results = {}
            predictions = self.model.predict(x[split])

            for metric in metrics:
                # Check if the metric is a classification metric that supports multiclass
                if (isinstance(metric, type) and 
                    issubclass(metric, ClassificationMetric) and 
                    "multiclass" in metric.score.__code__.co_varnames and
                    multiclass is not None):

                    print("metric is", metric)
                    print("multiclass is", multiclass)
                    print("y[split] is", y[split])
                    score = metric.score(y[split], predictions, multiclass=multiclass)
                else:
                    # For metrics that don't accept the multiclass parameter
                    score = metric.score(y[split], predictions)

                split_results[metric.__name__] = score

            results[split] = split_results

        return results
