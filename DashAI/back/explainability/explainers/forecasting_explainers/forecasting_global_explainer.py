"""Base class for global explainers specialized for forecasting tasks.

Provides common functionality for explaining forecasting models:
- Timestamp column detection and handling
- Frequency inference and validation
- Exogenous variable management
- Time series data preparation

All global explainers for forecasting tasks should inherit from this class.
"""

from abc import abstractmethod
from typing import List, Optional, Tuple

import pandas as pd
from datasets import DatasetDict

from DashAI.back.explainability.global_explainer import BaseGlobalExplainer
from DashAI.back.models import BaseModel


class ForecastingGlobalExplainer(BaseGlobalExplainer):
    """Base class for global explainers specialized for forecasting.

    Provides common utilities for handling time series data:
    - Timestamp column detection
    - Frequency inference
    - Exogenous variable extraction
    - Data validation for forecasting

    Subclasses must implement:
    - explain(): Generate the explanation
    - plot(): Create visualizations
    """

    # All forecasting explainers are compatible with ForecastingTask
    COMPATIBLE_COMPONENTS = ["ForecastingTask"]

    def __init__(self, model: BaseModel, **kwargs):
        """Initialize forecasting global explainer.

        Parameters
        ----------
        model : BaseModel
            Trained forecasting model to explain
        **kwargs : dict
            Additional parameters passed to parent class
        """
        super().__init__(model, **kwargs)

        # Cache for model metadata
        self._timestamp_col: Optional[str] = None
        self._target_col: Optional[str] = None
        self._exog_cols: Optional[List[str]] = None
        self._frequency: Optional[str] = None

    def _get_timestamp_column(self) -> Optional[str]:
        """Get timestamp column name from model.

        Returns
        -------
        str or None
            Name of timestamp column, or None if not available
        """
        if self._timestamp_col is not None:
            return self._timestamp_col

        # Try to get from model
        if hasattr(self.model, "timestamp_col"):
            self._timestamp_col = getattr(self.model, "timestamp_col", None)
        elif hasattr(self.model, "get_column_names"):
            try:
                col_names = self.model.get_column_names()  # type: ignore
                self._timestamp_col = col_names.get("timestamp")
            except Exception:
                pass

        return self._timestamp_col

    def _get_target_column(self) -> Optional[str]:
        """Get target column name from model.

        Returns
        -------
        str or None
            Name of target column, or None if not available
        """
        if self._target_col is not None:
            return self._target_col

        # Try to get from model
        if hasattr(self.model, "target_col"):
            self._target_col = getattr(self.model, "target_col", None)
        elif hasattr(self.model, "get_column_names"):
            try:
                col_names = self.model.get_column_names()  # type: ignore
                self._target_col = col_names.get("target")
            except Exception:
                pass

        return self._target_col

    def _get_exogenous_columns(self) -> List[str]:
        """Get exogenous variable names from model.

        Uses model's interface to get exogenous columns in original format.

        Returns
        -------
        List[str]
            List of exogenous variable names
        """
        if self._exog_cols is not None:
            return self._exog_cols

        # Try to get from model using ForecastingModel interface
        if hasattr(self.model, "get_exogenous_columns"):
            try:
                self._exog_cols = self.model.get_exogenous_columns()  # type: ignore
                return self._exog_cols or []
            except Exception:
                pass

        # Fallback: check exog_cols attribute
        if hasattr(self.model, "exog_cols"):
            self._exog_cols = getattr(self.model, "exog_cols", [])
            return self._exog_cols or []

        return []

    def _get_frequency(self) -> Optional[str]:
        """Get time series frequency from model.

        Returns
        -------
        str or None
            Frequency string (e.g., 'D', 'H', 'M'), or None if not available
        """
        if self._frequency is not None:
            return self._frequency

        # Try to get from model
        if hasattr(self.model, "frequency"):
            self._frequency = getattr(self.model, "frequency", None)

        return self._frequency

    def _extract_timestamps(
        self, dataset: DatasetDict, split: str = "test"
    ) -> pd.Series:
        """Extract timestamp column from dataset.

        Parameters
        ----------
        dataset : DatasetDict
            Dataset containing time series data
        split : str
            Which split to extract from (default: "test")

        Returns
        -------
        pd.Series
            Series with timestamps as datetime

        Raises
        ------
        ValueError
            If timestamp column not found or cannot be converted
        """
        timestamp_col = self._get_timestamp_column()

        if timestamp_col is None:
            raise ValueError(
                "Cannot determine timestamp column. "
                "Model must store timestamp_col or implement get_column_names()"
            )

        if split not in dataset:
            raise ValueError(f"Split '{split}' not found in dataset")

        ds = dataset[split]

        if timestamp_col not in ds.column_names:
            raise ValueError(
                f"Timestamp column '{timestamp_col}' not found in dataset. "
                f"Available columns: {ds.column_names}"
            )

        # Convert to pandas Series with datetime
        timestamps = pd.to_datetime(ds.to_pandas()[timestamp_col])

        return timestamps

    def _prepare_dataset_with_timestamps(
        self, dataset: DatasetDict, split: str = "test"
    ) -> pd.DataFrame:
        """Prepare dataset as DataFrame with all required columns.

        Includes timestamp column, exogenous variables, and target (if available).
        This is useful when explainers need the full context for predictions.

        Parameters
        ----------
        dataset : DatasetDict
            Dataset to prepare
        split : str
            Which split to use (default: "test")

        Returns
        -------
        pd.DataFrame
            DataFrame with timestamps, exogenous variables, and target
        """
        if split not in dataset:
            raise ValueError(f"Split '{split}' not found in dataset")

        split_df = dataset[split].to_pandas()

        # Ensure timestamp column is datetime
        timestamp_col = self._get_timestamp_column()
        if timestamp_col and timestamp_col in split_df.columns:
            split_df[timestamp_col] = pd.to_datetime(split_df[timestamp_col])

        return split_df

    def _validate_has_exogenous_variables(self) -> bool:
        """Check if model uses exogenous variables.

        Returns
        -------
        bool
            True if model has exogenous variables
        """
        if hasattr(self.model, "has_exogenous_variables"):
            try:
                return self.model.has_exogenous_variables()  # type: ignore
            except Exception:
                pass

        # Fallback: check if exog_cols is non-empty
        exog_cols = self._get_exogenous_columns()
        return len(exog_cols) > 0

    def _infer_frequency(self, timestamps: pd.Series) -> Optional[str]:
        """Infer frequency from timestamp series.

        Parameters
        ----------
        timestamps : pd.Series
            Series of datetime values

        Returns
        -------
        str or None
            Inferred frequency (e.g., 'D', 'H'), or None if cannot infer
        """
        try:
            # Use pandas infer_freq
            freq = pd.infer_freq(timestamps)
            return freq
        except Exception:
            # Try getting from model
            return self._get_frequency()

    @abstractmethod
    def explain(self, dataset: Tuple[DatasetDict, DatasetDict]) -> dict:
        """Generate explanation for the forecasting model.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            Tuple with (input_features, targets)
            Note: For forecasting, input_features may need timestamp column

        Returns
        -------
        dict
            Explanation results
        """

    @abstractmethod
    def plot(self, explanation: dict) -> List[dict]:
        """Create visualizations for the explanation.

        Parameters
        ----------
        explanation : dict
            Explanation dictionary from explain()

        Returns
        -------
        List[dict]
            List of plotly JSON figures
        """
