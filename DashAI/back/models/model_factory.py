from kink import di

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
        self.model, self.fixed_parameters, self.optimizable_parameters = (
            self._extract_parameters(model, params)
        )

        self.num_labels = n_labels

        if self.num_labels is not None:
            self.model.num_labels_from_factory = self.num_labels

        self.fitted = False

    def _extract_parameters(self, model_class, parameters: dict):
        """
        Recursively instantiate a DashAI model and
        its subcomponents from a parameters dict,
        and collect references to optimizable parameters
        including their ranges.

        Parameters
        ----------
        model_class : type
            The class of the model to instantiate.
        parameters : dict
            A dictionary of parameters for the model, which may include
            nested DashAI components and optimizable parameters.

        Returns
        -------
        tuple
            A tuple containing:
            - The instantiated model.
            - A dictionary of fixed parameters.
            - A list of tuples representing optimizable parameters,
              each containing
              (object reference, parameter name, (lower_bound, upper_bound)).
        """
        fixed_params = {}
        optimizable_refs = []

        # Instantiate main model without calling __init__
        model_instance = model_class.__new__(model_class)

        for key, val in parameters.items():
            fixed_val, refs = self._process_param(model_instance, key, val)
            fixed_params[key] = fixed_val
            optimizable_refs.extend(refs)

        # Initialize model with fixed params
        if hasattr(model_instance, "__init__"):
            model_instance.__init__(**fixed_params)

        return model_instance, fixed_params, optimizable_refs

    def _process_param(self, obj, key, value):
        """
        Recursively process each parameter and
        bind optimizable refs to the final model graph.

        Parameters
        ----------
        obj : object
            The object to which the parameter belongs.
        key : str
            The name of the parameter.
        value : any
            The value of the parameter, which may be a nested component,
            an optimizable parameter, or a fixed value.

        Returns
        -------
        tuple
            A tuple containing:
            - The fixed value of the parameter.
            - A list of tuples representing optimizable parameters,
              each containing
              (object reference, parameter name, (lower_bound, upper_bound)).
        """
        local_refs = []
        component_registry = di["component_registry"]

        component = {
            key: value
            for key, value in component_registry[obj.__class__.__name__].items()
            if key != "class"
        }
        component_params = component.get("schema").get("properties")

        # Unwrap 'properties' if present
        if isinstance(value, dict) and "properties" in value and len(value) == 1:
            value = value["properties"]

        # --- Case 1: Nested DashAI component ---
        if isinstance(value, dict) and "component" in value:
            parent_component_name = value["component"]
            component = value.get("params", {}).get("comp", {})

            if component == {}:
                component_name = parent_component_name
                params_dict = value.get("params", {})
            else:
                component_name = component.get("component")
                params_dict = component.get("params", {})

            sub_model_class = component_registry[component_name]["class"]

            # Recursively build the submodel
            sub_model_instance, _, sub_refs = self._extract_parameters(
                sub_model_class, params_dict
            )

            # Attach submodel to the *real* parent object
            setattr(obj, key, sub_model_instance)

            # Rebind all sub_refs to point to this same instance (no duplicates needed)
            local_refs.extend(sub_refs)
            fixed_val = sub_model_instance

        # --- Case 2: Optimizable parameter ---
        elif isinstance(value, dict) and value.get("optimize") is True:
            lower, upper = value.get("lower_bound"), value.get("upper_bound")
            fixed_value = value.get("fixed_value")

            setattr(obj, key, fixed_value)
            local_refs.append(
                (obj, key, (lower, upper), component_params[key].get("type"))
            )

            fixed_val = fixed_value

        # --- Case 3: Fixed parameter ---
        elif isinstance(value, dict) and "fixed_value" in value:
            fixed_value = value["fixed_value"]
            setattr(obj, key, fixed_value)
            fixed_val = fixed_value

        # --- Case 4: Primitive value ---
        else:
            setattr(obj, key, value)
            fixed_val = value

        return fixed_val, local_refs

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

        multiclass = None
        if hasattr(self, "num_labels") and self.num_labels is not None:
            multiclass = self.num_labels > 2

        results = {}
        for split in ["train", "validation", "test"]:
            split_results = {}
            if x[split].shape[0] == 0:
                split_results = {metric.__name__: None for metric in metrics}
                results[split] = split_results
                continue
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
