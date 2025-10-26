"""
MultiOutput regression model for DashAI.

This model is a wrapper around sklearn.multioutput.MultiOutputRegressor.
By default it uses LinearRegression as base estimator but you can select
other sklearn regressors by passing the `base_estimator` parameter and,
optionally, `base_params` (a dict with kwargs for the base estimator).
"""

from typing import Any, Dict, Optional

from sklearn.ensemble import RandomForestRegressor as _RandomForestRegressor
from sklearn.linear_model import LinearRegression as _LinearRegression
from sklearn.linear_model import Ridge as _Ridge
from sklearn.multioutput import MultiOutputRegressor

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.models.regression_model import RegressionModel
from DashAI.back.models.scikit_learn.sklearn_like_regressor import SklearnLikeRegressor


class MultiOutputRegressionSchema(BaseSchema):
    """Multi-output regression using sklearn's MultiOutputRegressor.

    This meta-estimator fits one regressor per target variable, allowing you to
    predict multiple continuous outputs simultaneously. Choose from different base
    estimators depending on your needs: linear models for interpretability,
    tree-based models for non-linear relationships.
    """

    base_estimator: schema_field(
        enum_field(enum=["linear", "ridge", "random_forest"]),
        placeholder="linear",
        description="Base estimator to use for each output target. "
        "'linear': Fast linear regression (no regularization). "
        "'ridge': Linear regression with L2 regularization (prevents overfitting). "
        "'random_forest': Tree-based ensemble (handles non-linear relationships).",
    ) = "linear"  # type: ignore


class MultiOutputRegression(RegressionModel, SklearnLikeRegressor):
    """Meta-model using sklearn's MultiOutputRegressor."""

    SCHEMA = MultiOutputRegressionSchema

    COMPATIBLE_COMPONENTS = ["RegressionTask"]

    def __init__(
        self,
        base_estimator: str = "linear",
        base_params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        base_estimator : str
            Identifier of the base estimator. Supported: "linear", "ridge",
            "random_forest"
        base_params : dict, optional
            Keyword args to forward to the base estimator constructor.
        kwargs : dict
            Extra args (kept for compatibility with existing infrastructure).
        """
        super().__init__(**kwargs)

        if base_params is None:
            base_params = {}

        # Map string identifiers to sklearn estimators (you can extend with more).
        estimators = {
            "linear": _LinearRegression,
            "ridge": _Ridge,
            "random_forest": _RandomForestRegressor,
        }

        if base_estimator not in estimators:
            raise ValueError(
                f"Unknown base_estimator '{base_estimator}'. "
                f"Supported: {list(estimators.keys())}"
            )

        base_cls = estimators[base_estimator]
        base_instance = base_cls(**base_params)

        # The actual sklearn model we will fit/predict with
        self.sklearn_model = MultiOutputRegressor(base_instance)

    # If SklearnLikeRegressor expects certain attributes/methods, adapt accordingly.
    # We implement fit/predict here to be explicit.

    def fit(self, x_train: DashAIDataset, y_train: DashAIDataset, **fit_params):
        """
        Fit the multioutput regressor.
        x_train: DashAIDataset with input features
        y_train: DashAIDataset with output targets
        """
        import numpy as np

        # CRITICAL: Convert DashAI datasets to pandas first
        x_pandas = x_train.to_pandas()
        y_pandas = y_train.to_pandas()

        # Convert pandas to numpy arrays
        X = np.asarray(x_pandas)
        y = np.asarray(y_pandas)

        # KEY FIX: Ensure y is 2D for MultiOutputRegressor
        # sklearn's MultiOutputRegressor requires y to have at least 2 dimensions
        if y.ndim == 1:
            print(
                f"[MultiOutputRegression] Converting 1D y (shape {y.shape}) "
                f"to 2D for multi-output regression"
            )
            y = y.reshape(-1, 1)

        print(
            f"[MultiOutputRegression] Training with X shape: {X.shape}, "
            f"y shape: {y.shape}"
        )
        print(f"[MultiOutputRegression] X columns: {list(x_pandas.columns)}")
        print(f"[MultiOutputRegression] y columns: {list(y_pandas.columns)}")

        # Now this will work with both 1D and 2D y arrays
        self.sklearn_model.fit(X, y, **fit_params)
        return self

    def predict(self, x_pred: DashAIDataset):
        """
        Predict multi-output targets.
        x_pred: DashAIDataset with input features
        Returns array shape (n_samples, n_outputs)
        """
        import numpy as np

        # CRITICAL: Convert DashAI dataset to pandas first (same as fit method)
        x_pandas = x_pred.to_pandas()

        # Convert pandas to numpy array
        X = np.asarray(x_pandas)

        print(f"[MultiOutputRegression] Predicting with X shape: {X.shape}")

        # Now this will work with clean numpy array
        return self.sklearn_model.predict(X)

    # If DashAI base classes expect `save` and `load`, SklearnLikeRegressor
    # if not, you should rely on the SklearnLikeRegressor implementations. If necessary,
    # override save/load following the project's conventions.
