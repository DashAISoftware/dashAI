import torch
from sklearn.exceptions import NotFittedError


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

    def __init__(self, model, params: dict):
        self.fixed_parameters, self.optimizable_parameters = self._extract_parameters(
            params
        )
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
        """Computes metrics only if the model is fitted."""
        if not self.fitted:
            raise NotFittedError("Model must be trained before evaluating metrics.")
        return {
            split: {
                metric.__name__: metric.score(y[split], self.model.predict(x[split]))
                for metric in metrics
            }
            for split in ["train", "validation", "test"]
        }
