"""
Time Series Window Converter for DashAI.

This converter transforms time series data into a tabular regression format
by creating lag features and target columns with fixed horizons.
"""

from typing import Union

import pandas as pd

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.core.schema_fields import (
    int_field,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)


class TimeSeriesWindowConverterSchema(BaseSchema):
    """Schema for TimeSeriesWindowConverter parameters."""

    window_size: schema_field(
        int_field(ge=1),
        7,
        "Number of past time steps to use as lag features (window size).",
    )  # type: ignore

    horizon: schema_field(
        int_field(ge=1),
        1,
        "Number of time steps into the future to predict (forecasting horizon).",
    )  # type: ignore

    target_column: schema_field(
        string_field(),
        "",
        "Name of the target column containing the time series values to forecast.",
    )  # type: ignore


class TimeSeriesWindowConverter(BaseConverter):
    """
    Converter that transforms time series data into a regression problem.

    This converter creates lag features (lag_1, lag_2, ..., lag_w) from a time series
    and a target column shifted h steps into the future (y_target_h), where:
    - w is the window_size parameter
    - h is the horizon parameter

    The resulting dataset can be used with standard regression models to perform
    forecasting as a supervised learning problem.

    Example:
    --------
    Original time series: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    With window_size=3 and horizon=1:

    lag_3  lag_2  lag_1  y_target_1
    1      2      3      4
    2      3      4      5
    3      4      5      6
    4      5      6      7
    5      6      7      8
    6      7      8      9
    7      8      9      10
    """

    SCHEMA = TimeSeriesWindowConverterSchema
    DESCRIPTION = (
        "Transforms time series data into a tabular regression format by creating "
        "lag features from past values and a target column shifted into the future. "
        "This enables forecasting using standard regression models."
    )
    SHORT_DESCRIPTION = (
        "Converts time series to regression with lag features and future targets."
    )
    DISPLAY_NAME = "Time Series Window Converter"

    def __init__(self, window_size: int = 7, horizon: int = 1, target_column: str = ""):
        """Initialize the converter with schema parameters."""
        super().__init__()
        self.window_size = window_size
        self.horizon = horizon
        self.target_column = target_column

        # Internal state
        self._fitted = False
        self._target_column_validated = ""

    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> "TimeSeriesWindowConverter":
        """
        Fit the converter by validating parameters and target column.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset containing the time series data
        y : DashAIDataset, optional
            Not used in this converter

        Returns
        -------
        TimeSeriesWindowConverter
            The fitted converter instance

        Raises
        ------
        ValueError
            If validation fails (missing target column, invalid parameters, etc.)
        """
        # Validate parameters
        if self.window_size < 1:
            raise ValueError("window_size must be a positive integer")

        if self.horizon < 1:
            raise ValueError("horizon must be a positive integer")

        if not self.target_column:
            raise ValueError("target_column must be a non-empty string")

        # Check if target column exists in dataset
        if self.target_column not in x.column_names:
            raise ValueError(
                f"Target column '{self.target_column}' not found in dataset. "
                f"Available columns: {x.column_names}"
            )

        # Validate that we have enough data points
        min_required_rows = self.window_size + self.horizon
        if len(x) < min_required_rows:
            raise ValueError(
                f"Dataset has {len(x)} rows but needs at least "
                f"{min_required_rows} rows (window_size={self.window_size} + "
                f"horizon={self.horizon})"
            )

        # Store validated target column name
        self._target_column_validated = self.target_column
        self._fitted = True

        return self

    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """
        Transform the dataset by creating lag features and target column.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset to transform
        y : DashAIDataset, optional
            Not used in this converter

        Returns
        -------
        DashAIDataset
            Transformed dataset with lag features and target column

        Raises
        ------
        ValueError
            If converter is not fitted or transformation fails
        """
        if not self._fitted:
            raise ValueError("Converter must be fitted before transform")

        # Convert to pandas for easier manipulation
        data_frame = x.to_pandas()

        # Verify target column still exists
        if self._target_column_validated not in data_frame.columns:
            raise ValueError(
                f"Target column '{self._target_column_validated}' not found "
                f"in transform dataset"
            )

        # Create a copy to avoid modifying the original
        result_df = pd.DataFrame()

        # Create lag features (lag_1, lag_2, ..., lag_w)
        target_series = data_frame[self._target_column_validated]

        for lag in range(1, self.window_size + 1):
            lag_column_name = f"lag_{lag}"
            result_df[lag_column_name] = target_series.shift(lag)

        # Create multiple target columns (y_target_1 to y_target_horizon)
        for h in range(1, self.horizon + 1):
            target_column_name = f"y_target_{h}"
            result_df[target_column_name] = target_series.shift(-h)

        # Include any other columns that are not the target column
        # This preserves potential date columns or other features
        other_columns = [
            col for col in data_frame.columns if col != self._target_column_validated
        ]
        for col in other_columns:
            result_df[col] = data_frame[col]

        # Remove rows with NaN values (caused by shifting)
        # These occur at the beginning (due to lag) and end (due to future target)
        result_df = result_df.dropna()

        # Validate that we still have data after removing NaN rows
        if len(result_df) == 0:
            raise ValueError(
                "No valid rows remain after creating lag features and target column. "
                "Try reducing window_size or horizon, or use a larger dataset."
            )

        # Convert back to DashAIDataset
        return to_dashai_dataset(result_df)

    def changes_row_count(self) -> bool:
        """
        Indicates that this converter changes the number of rows.

        Returns
        -------
        bool
            True, as rows with NaN values are removed
        """
        return True
