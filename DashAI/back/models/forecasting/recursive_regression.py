"""Forecasting by reduction to regression, with skforecast."""

from typing import Any


def sklearn_estimator(regressor: Any):
    """The plain scikit-learn estimator inside a DashAI regressor.

    skforecast clones the estimator it is handed, and scikit-learn's ``clone``
    rebuilds an estimator from ``get_params``. A DashAI regressor takes
    ``**kwargs``, which scikit-learn's ``_get_param_names`` cannot read, so
    ``get_params`` is empty and the clone silently falls back to the defaults:
    a forest configured with 7 trees would be fitted with 100. The estimator
    built here is the regressor's own scikit-learn class, instantiated with
    the values the regressor holds, so a clone of it keeps them.

    It is built on every fit rather than once, so it sees the values a search
    sets on the nested regressor for each trial.

    Parameters
    ----------
    regressor : object
        A DashAI regressor that is also a scikit-learn estimator, as the
        ``SklearnLikeRegressor`` models are. It is not modified.

    Returns
    -------
    sklearn.base.RegressorMixin
        An unfitted scikit-learn regressor with the same hyperparameters.

    Raises
    ------
    TypeError
        If no concrete scikit-learn regressor is among the regressor's
        classes: a torch model such as ``MLPRegression``, or a classifier.
    """
    import inspect

    from sklearn.base import RegressorMixin

    for cls in type(regressor).__mro__:
        if (
            cls.__module__.split(".")[0] == "sklearn"
            and cls is not RegressorMixin
            and issubclass(cls, RegressorMixin)
            and not inspect.isabstract(cls)
        ):
            names = cls._get_param_names()
            return cls(**{name: getattr(regressor, name) for name in names})
    raise TypeError(
        f"{type(regressor).__name__} is not a scikit-learn regressor: the "
        "reduction model regresses on the lags with one of the "
        "SklearnLikeRegressor models."
    )
