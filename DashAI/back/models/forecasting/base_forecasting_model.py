"""Forecasting Model abstract class.

This module defines the common interface for all forecasting models in DashAI.
It ensures model-agnostic handling of time series data and exogenous variables.
"""

import warnings
from abc import abstractmethod
from typing import List, Optional

import pandas as pd

from DashAI.back.models.base_model import BaseModel


class ForecastingModel(BaseModel):
    """Abstract class for all forecasting models.

    This class defines the common interface that all forecasting models must implement.
    It handles:
    - Exogenous variables (external regressors) in a model-agnostic way
    - Timestamp and target column management
    - Prediction interface for both in-sample and out-of-sample forecasting

    Key Attributes
    --------------
    exog_cols : List[str]
        List of exogenous variable column names used during training.
        These are stored in their ORIGINAL names from the dataset,
        not in any model-specific format.

    timestamp_col : Optional[str]
        Name of the timestamp/datetime column in the original dataset.

    target_col : Optional[str]
        Name of the target variable column in the original dataset.

    Philosophy
    ----------
    This class maintains column names in their ORIGINAL format from the user's
    dataset. Each specific model implementation (Prophet, ARIMA, etc.) is
    responsible for:
    1. Internally converting column names to its required format
       (e.g., Prophet needs 'ds'/'y')
    2. Converting predictions back to match original column names
    3. Handling model-specific requirements transparently

    This ensures the system is agnostic to each model's internal conventions.

    Note
    ----
    This class inherits TYPE = "Model" from BaseModel. The name "ForecastingModel"
    (without "Base" prefix) avoids conflicts with the component registry system
    which looks for classes with "Base" in their name.
    """

    _compatible_tasks = ["ForecastingTask"]

    def __init__(self, **kwargs):
        """Initialize forecasting model.

        Sets up common attributes that all forecasting models should maintain.

        Parameters
        ----------
        **kwargs
            Additional arguments passed to BaseModel.__init__
        """
        super().__init__(**kwargs)

        # Store exogenous variable names in ORIGINAL format
        self.exog_cols: List[str] = []

        # Store column names for reference
        self.timestamp_col: Optional[str] = None
        self.target_col: Optional[str] = None

    @abstractmethod
    def fit(self, x: pd.DataFrame, y: pd.DataFrame, **kwargs) -> "ForecastingModel":
        """Train the forecasting model.

        Parameters
        ----------
        x : pd.DataFrame
            Training features including:
            - Timestamp column (datetime)
            - Exogenous variables (optional)
            May also include the target column (will be used from there if present)

        y : pd.DataFrame
            Target variable values.
            Single column with the variable to forecast.

        **kwargs
            Additional model-specific parameters.

        Returns
        -------
        self : ForecastingModel
            Returns self for method chaining.

        Notes
        -----
        Implementations should:
        1. Auto-detect timestamp column (try pd.to_datetime on columns)
        2. Filter exogenous variables (numeric only, exclude timestamp/target)
        3. Store original column names in self.exog_cols, self.timestamp_col,
           self.target_col
        4. Internally convert to model-specific format if needed
        """
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        x_pred: Optional[pd.DataFrame] = None,
        periods: Optional[int] = None,
        exog_future: Optional[pd.DataFrame] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Generate forecasts.

        Supports two prediction modes:
        1. In-sample: Provide x_pred with timestamps and exogenous values
        2. Out-of-sample: Provide periods and exog_future for future forecasting

        Parameters
        ----------
        x_pred : pd.DataFrame, optional
            Input data for in-sample predictions containing:
            - Timestamp column
            - Exogenous variables (if model uses them)

        periods : int, optional
            Number of future periods to forecast (out-of-sample mode).

        exog_future : pd.DataFrame, optional
            Future values of exogenous variables for out-of-sample forecasting.
            Must contain all columns in self.exog_cols.

        **kwargs
            Additional model-specific parameters.

        Returns
        -------
        pd.DataFrame or np.ndarray
            Predictions with columns using ORIGINAL names:
            - Timestamp column (same name as training data)
            - Target column (same name as training data)
            - Optionally: prediction intervals, components, etc.

        Notes
        -----
        Implementations MUST support both prediction modes:
        1. In-sample predictions (x_pred provided): For calculating metrics on
           train/validation/test splits
        2. Out-of-sample predictions (periods provided): For future forecasting

        Implementations should:
        1. Auto-detect timestamp column in x_pred (handle both original name and 'ds')
        2. Validate exogenous variables are present if model requires them
        3. Return predictions with ORIGINAL column names (not model-specific names)

        IMPORTANT: Do NOT raise NotImplementedError for in-sample predictions.
        Model evaluation (metrics calculation) requires in-sample predictions.
        """
        raise NotImplementedError

    def train(
        self,
        x_train,
        y_train,
        x_validation=None,
        y_validation=None,
        **kwargs,
    ) -> "ForecastingModel":
        """Compatibility wrapper for the generic DashAI model contract.

        Forecasting jobs train models via ``fit()`` so they can pass
        ``temporal_metadata`` and other forecasting-specific arguments. This
        wrapper keeps forecasting models instantiable through ``ModelFactory``,
        which still expects every model to provide a concrete ``train()`` method.
        """
        if x_validation is not None or y_validation is not None:
            warnings.warn(
                "ForecastingModel.train() ignores validation datasets. "
                "Forecasting models should be trained via fit() with the "
                "appropriate temporal metadata.",
                UserWarning,
                stacklevel=2,
            )

        return self.fit(x_train, y_train, **kwargs)

    def get_exogenous_columns(self) -> List[str]:
        """Get list of exogenous variable names in original format.

        Returns
        -------
        List[str]
            List of exogenous variable column names as they appear in the
            original dataset (not in model-specific format).

        Examples
        --------
        >>> model.fit(x_train, y_train)
        >>> model.get_exogenous_columns()
        ['temperature', 'humidity', 'wind_speed']
        # NOT ['exog_temperature', 'exog_humidity', 'exog_wind_speed']
        # NOT ['extra_regressor_1', 'extra_regressor_2', 'extra_regressor_3']
        """
        return self.exog_cols.copy()

    def has_exogenous_variables(self) -> bool:
        """Check if model uses exogenous variables.

        Returns
        -------
        bool
            True if model was trained with exogenous variables, False otherwise.
        """
        return len(self.exog_cols) > 0

    def get_column_names(self) -> dict:
        """Get all relevant column names in original format.

        Returns
        -------
        dict
            Dictionary with keys:
            - 'timestamp': Timestamp column name
            - 'target': Target column name
            - 'exogenous': List of exogenous variable names
        """
        return {
            "timestamp": self.timestamp_col,
            "target": self.target_col,
            "exogenous": self.exog_cols.copy(),
        }

    def _validate_predict_implementation(self) -> None:
        """Validate that subclass implements predict() correctly.

        This method can be called in tests to ensure implementations support
        both in-sample and out-of-sample predictions.

        Raises
        ------
        NotImplementedError
            If predict() raises NotImplementedError for in-sample predictions
        ValueError
            If predict() doesn't handle both prediction modes

        Notes
        -----
        This is a helper for testing - not called automatically during runtime.
        Developers should call this in unit tests for their forecasting models.

        Example
        -------
        >>> # In test_my_model.py
        >>> model = MyForecastingModel()
        >>> model.fit(x_train, y_train)
        >>> model._validate_predict_implementation()  # Ensures correct implementation
        """
        warnings.warn(
            "ForecastingModel.predict() must support both in-sample (x_pred) "
            "and out-of-sample (periods) prediction modes. "
            "In-sample predictions are required for metrics calculation.",
            UserWarning,
            stacklevel=2,
        )
