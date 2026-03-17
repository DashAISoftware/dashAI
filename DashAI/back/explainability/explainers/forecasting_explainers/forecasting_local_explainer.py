"""Base class for local explainers specialized for forecasting tasks.

Provides common functionality for explaining individual forecasts:
- Instance selection from time series
- Window extraction for point-in-time explanations
- Temporal context management
- Per-forecast explanation generation

All local explainers for forecasting tasks should inherit from this class.
"""

from abc import abstractmethod
from typing import List, Optional, Tuple

import pandas as pd
from datasets import DatasetDict

from DashAI.back.explainability.local_explainer import BaseLocalExplainer
from DashAI.back.models import BaseModel


class ForecastingLocalExplainer(BaseLocalExplainer):
    """Base class for local explainers specialized for forecasting.

    Provides common utilities for explaining individual forecasts:
    - Timestamp handling for specific forecast points
    - Window extraction (e.g., last N days before forecast)
    - Exogenous variable context
    - Per-instance explanation generation

    Subclasses must implement:
    - fit(): Prepare explainer with training data
    - explain_instance(): Generate explanation for specific forecast
    - plot(): Create visualizations
    """

    # All forecasting local explainers are compatible with ForecastingTask
    COMPATIBLE_COMPONENTS = ["ForecastingTask"]

    def __init__(self, model: BaseModel, **kwargs):
        """Initialize forecasting local explainer.

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

    def _extract_window(
        self,
        dataset: DatasetDict,
        split: str = "test",
        window_size: Optional[int] = None,
        end_index: Optional[int] = None,
    ) -> pd.DataFrame:
        """Extract a window of data for local explanation.

        Useful for explaining a specific forecast by showing the context
        (e.g., last 30 days before the forecast point).

        Parameters
        ----------
        dataset : DatasetDict
            Dataset containing time series data
        split : str
            Which split to use (default: "test")
        window_size : int, optional
            Number of time points to include in window
            If None, returns all data up to end_index
        end_index : int, optional
            Last index to include (exclusive)
            If None, uses all available data

        Returns
        -------
        pd.DataFrame
            DataFrame with windowed data
        """
        if split not in dataset:
            raise ValueError(f"Split '{split}' not found in dataset")

        split_df = dataset[split].to_pandas()

        # Apply end index
        if end_index is not None:
            split_df = split_df.iloc[:end_index]

        # Apply window size
        if window_size is not None and len(split_df) > window_size:
            split_df = split_df.iloc[-window_size:]

        # Ensure timestamp column is datetime
        timestamp_col = self._get_timestamp_column()
        if timestamp_col and timestamp_col in split_df.columns:
            split_df[timestamp_col] = pd.to_datetime(split_df[timestamp_col])

        return split_df

    def _select_instance_by_timestamp(
        self, dataset: DatasetDict, timestamp: pd.Timestamp, split: str = "test"
    ) -> pd.Series:
        """Select a specific instance by timestamp.

        Parameters
        ----------
        dataset : DatasetDict
            Dataset containing time series data
        timestamp : pd.Timestamp
            Timestamp of instance to select
        split : str
            Which split to use (default: "test")

        Returns
        -------
        pd.Series
            Single row as Series

        Raises
        ------
        ValueError
            If timestamp not found in dataset
        """
        timestamp_col = self._get_timestamp_column()

        if timestamp_col is None:
            raise ValueError(
                "Cannot select by timestamp: timestamp column not available"
            )

        split_df = dataset[split].to_pandas()
        split_df[timestamp_col] = pd.to_datetime(split_df[timestamp_col])

        mask = split_df[timestamp_col] == timestamp

        if not mask.any():
            raise ValueError(f"Timestamp {timestamp} not found in {split} split")

        return split_df[mask].iloc[0]

    def _prepare_dataset_with_timestamps(
        self, dataset: DatasetDict, split: str = "test"
    ) -> pd.DataFrame:
        """Prepare dataset as DataFrame with all required columns.

        Includes timestamp column, exogenous variables, and target (if available).

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

    @abstractmethod
    def fit(
        self, dataset: Tuple[DatasetDict, DatasetDict], **fit_params
    ) -> "ForecastingLocalExplainer":
        """Fit the explainer on training data.

        Parameters
        ----------
        dataset : Tuple[DatasetDict, DatasetDict]
            Tuple with (input_features, targets)
        **fit_params : dict
            Additional fitting parameters

        Returns
        -------
        ForecastingLocalExplainer
            Self
        """

    @abstractmethod
    def explain_instance(self, instance: DatasetDict) -> dict:
        """Generate explanation for a specific forecast instance.

        Parameters
        ----------
        instance : DatasetDict
            Single instance or small window to explain

        Returns
        -------
        dict
            Explanation for this specific instance
        """

    @abstractmethod
    def plot(self, explanation: dict) -> List[dict]:
        """Create visualizations for the local explanation.

        Parameters
        ----------
        explanation : dict
            Explanation dictionary from explain_instance()

        Returns
        -------
        List[dict]
            List of plotly JSON figures
        """
