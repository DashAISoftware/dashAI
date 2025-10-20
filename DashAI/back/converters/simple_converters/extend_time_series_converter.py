"""
Extend Time Series Converter for DashAI.

This converter extends a time series dataset by adding n future timestamps
with the same period as the original dataset. This is useful for preparing
datasets for forecasting predictions.
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


class ExtendTimeSeriesConverterSchema(BaseSchema):
    """Schema for ExtendTimeSeriesConverter parameters."""

    n_steps: schema_field(
        int_field(ge=1, le=100000),
        1,
        "Number of future time steps to add to the dataset (max: 100,000).",
    )  # type: ignore

    time_column: schema_field(
        string_field(),
        "",
        (
            "Name of the timestamp column to extend. "
            "If empty, the converter will auto-detect datetime columns."
        ),
    )  # type: ignore


class ExtendTimeSeriesConverter(BaseConverter):
    """
    Converter that extends a time series dataset with future timestamps.

    This converter adds n new rows to the dataset with timestamps that continue
    the sequence from the last timestamp in the dataset. The frequency/period
    is automatically inferred from the existing timestamps.

    All columns except the timestamp column will be filled with NaN values
    in the new rows, as these are future values to be predicted.

    Example:
    --------
    Original dataset:
        date       | y     | exog1
        2024-01-01 | 10.5  | 100
        2024-01-02 | 11.2  | 105
        2024-01-03 | 12.1  | 110

    After extending with n_steps=2:
        date       | y     | exog1
        2024-01-01 | 10.5  | 100
        2024-01-02 | 11.2  | 105
        2024-01-03 | 12.1  | 110
        2024-01-04 | NaN   | NaN
        2024-01-05 | NaN   | NaN
    """

    SCHEMA = ExtendTimeSeriesConverterSchema
    DESCRIPTION = (
        "Extends a time series dataset by adding n future timestamps with the same "
        "period as the original data. Other columns are filled with NaN values. "
        "This is useful for preparing datasets for forecasting predictions."
    )
    SHORT_DESCRIPTION = "Extends time series with n future timestamps for forecasting."
    DISPLAY_NAME = "Extend Time Series Converter"

    # Maximum allowed n_steps to prevent memory issues
    MAX_N_STEPS = 100000

    def __init__(self, n_steps: int = 1, time_column: str = ""):
        """Initialize the converter with schema parameters."""
        super().__init__()
        self.n_steps = n_steps
        self.time_column = time_column

        # Internal state
        self._fitted = False
        self._time_column_validated = ""
        self._inferred_freq = None

    def _detect_datetime_columns(self, df: pd.DataFrame) -> list[str]:
        """
        Detect columns with datetime or timestamp data types.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame to analyze

        Returns
        -------
        list[str]
            List of column names with datetime/timestamp types
        """
        datetime_columns = []

        for col in df.columns:
            # Check if column dtype is datetime
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                datetime_columns.append(col)
            # Try to parse as datetime if it's object/string type
            elif df[col].dtype == "object":
                try:
                    # Try to convert a sample to datetime
                    pd.to_datetime(df[col].dropna().head(10), errors="raise")
                    datetime_columns.append(col)
                except (ValueError, TypeError):
                    # Not a datetime column
                    pass

        return datetime_columns

    def _infer_frequency(self, time_series: pd.Series) -> pd.DateOffset:
        """
        Infer the frequency/period of a datetime series.

        Parameters
        ----------
        time_series : pd.Series
            Series with datetime values

        Returns
        -------
        pd.DateOffset
            The inferred frequency

        Raises
        ------
        ValueError
            If frequency cannot be inferred
        """
        # Ensure the series is sorted
        time_series = time_series.sort_values().reset_index(drop=True)

        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(time_series):
            time_series = pd.to_datetime(time_series)

        # Remove NaT values
        time_series = time_series.dropna()

        # Need at least 2 points to infer frequency
        if len(time_series) < 2:
            raise ValueError(
                "Need at least 2 timestamps to infer frequency. "
                f"Found {len(time_series)} timestamps."
            )

        # Check for duplicate timestamps
        duplicates = time_series.duplicated()
        if duplicates.any():
            n_duplicates = duplicates.sum()
            # Warning: we'll still try to infer, but user should know
            import warnings

            warnings.warn(
                f"Found {n_duplicates} duplicate timestamp(s) in the time series. "
                "This may affect frequency inference.",
                UserWarning,
                stacklevel=2,
            )
            # Remove duplicates for frequency inference
            time_series = time_series.drop_duplicates()

        # Try using pandas infer_freq on unique sorted values
        freq = pd.infer_freq(time_series)
        if freq is not None:
            return pd.tseries.frequencies.to_offset(freq)

        # If infer_freq fails, calculate the most common difference
        diffs = time_series.diff().dropna()

        if len(diffs) == 0:
            raise ValueError("Cannot infer frequency: no time differences found")

        # Filter out zero differences (duplicates that weren't caught)
        diffs = diffs[diffs != pd.Timedelta(0)]

        if len(diffs) == 0:
            raise ValueError(
                "Cannot infer frequency: all timestamps are identical "
                "after removing duplicates"
            )

        # Get the most common difference
        most_common_diff = diffs.mode()

        if len(most_common_diff) == 0:
            raise ValueError("Cannot infer frequency: no consistent time difference")

        # Check if the frequency is reasonably consistent
        # If there's high variance, warn the user
        diff_std = diffs.std()
        diff_mean = diffs.mean()

        if diff_std / diff_mean > 0.5:  # More than 50% coefficient of variation
            import warnings

            warnings.warn(
                f"Timestamps have irregular intervals "
                f"(std/mean = {diff_std / diff_mean:.2f}). "
                f"Using most common difference: {most_common_diff.iloc[0]}. "
                "Results may not be accurate for irregular time series.",
                UserWarning,
                stacklevel=2,
            )

        # Return the most common difference as a Timedelta
        return most_common_diff.iloc[0]

    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> "ExtendTimeSeriesConverter":
        """
        Fit the converter by validating parameters and detecting time column.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset containing the time series data
        y : DashAIDataset, optional
            Not used in this converter

        Returns
        -------
        ExtendTimeSeriesConverter
            The fitted converter instance

        Raises
        ------
        ValueError
            If validation fails (missing time column, invalid parameters, etc.)
        """
        # Validate parameters
        if self.n_steps < 1:
            raise ValueError("n_steps must be a positive integer")

        if self.n_steps > self.MAX_N_STEPS:
            raise ValueError(
                f"n_steps cannot exceed {self.MAX_N_STEPS} to prevent memory issues. "
                f"Requested: {self.n_steps}"
            )

        # Convert to pandas for analysis
        data_frame: pd.DataFrame = x.to_pandas()  # type: ignore

        # Validate dataset is not empty
        if len(data_frame) == 0:
            raise ValueError(
                "Cannot extend an empty dataset. "
                "Please provide a dataset with at least 2 rows."
            )

        # Detect datetime columns
        datetime_columns = self._detect_datetime_columns(data_frame)

        if len(datetime_columns) == 0:
            raise ValueError(
                "No datetime columns found in the dataset. "
                "Please ensure your dataset has at least one timestamp column."
            )

        # Determine which time column to use
        if self.time_column:
            # User specified a time column
            if self.time_column not in data_frame.columns:
                raise ValueError(
                    f"Specified time column '{self.time_column}' not found in dataset. "
                    f"Available columns: {list(data_frame.columns)}"
                )

            if self.time_column not in datetime_columns:
                # Try to convert it to datetime
                try:
                    data_frame[self.time_column] = pd.to_datetime(
                        data_frame[self.time_column]
                    )
                    self._time_column_validated = self.time_column
                except (ValueError, TypeError) as e:
                    raise ValueError(
                        f"Column '{self.time_column}' cannot be converted "
                        f"to datetime: {e}"
                    ) from e
            else:
                self._time_column_validated = self.time_column
        else:
            # Auto-detect time column
            if len(datetime_columns) > 1:
                raise ValueError(
                    f"Multiple datetime columns found: {datetime_columns}. "
                    "Please specify which one to use with the 'time_column' parameter."
                )
            self._time_column_validated = datetime_columns[0]

        # Infer the frequency
        time_series = data_frame[self._time_column_validated]

        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(time_series):
            time_series = pd.to_datetime(time_series)

        try:
            self._inferred_freq = self._infer_frequency(time_series)
        except ValueError as e:
            raise ValueError(
                f"Failed to infer frequency for time column "
                f"'{self._time_column_validated}': {e}"
            ) from e

        self._fitted = True
        return self

    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """
        Transform the dataset by adding n future timestamps.

        Parameters
        ----------
        x : DashAIDataset
            Input dataset to transform
        y : DashAIDataset, optional
            Not used in this converter

        Returns
        -------
        DashAIDataset
            Extended dataset with n additional rows containing future timestamps

        Raises
        ------
        ValueError
            If converter is not fitted or transformation fails
        """
        if not self._fitted:
            raise ValueError("Converter must be fitted before transform")

        # Convert to pandas
        data_frame: pd.DataFrame = x.to_pandas()  # type: ignore

        # Verify time column still exists
        if self._time_column_validated not in data_frame.columns:
            raise ValueError(
                f"Time column '{self._time_column_validated}' not found "
                f"in transform dataset"
            )

        # Convert time column to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(
            data_frame[self._time_column_validated]
        ):
            data_frame[self._time_column_validated] = pd.to_datetime(
                data_frame[self._time_column_validated]
            )

        # Get the last timestamp
        last_timestamp = data_frame[self._time_column_validated].max()

        # Validate last_timestamp is not NaT
        if pd.isna(last_timestamp):
            raise ValueError(
                f"Cannot extend time series: all timestamps in column "
                f"'{self._time_column_validated}' are NaT (Not a Time)"
            )

        # Generate future timestamps
        future_timestamps = []
        current_timestamp = last_timestamp

        try:
            for _i in range(self.n_steps):
                current_timestamp = current_timestamp + self._inferred_freq
                future_timestamps.append(current_timestamp)
        except (OverflowError, ValueError) as e:
            raise ValueError(
                f"Error generating future timestamp at step "
                f"{_i + 1}/{self.n_steps}: {e}. "
                "This might be due to timestamp overflow or invalid frequency."
            ) from e

        # Create new rows with future timestamps
        future_rows = []
        for future_ts in future_timestamps:
            # Create a row with NaN for all columns except timestamp
            new_row = dict.fromkeys(data_frame.columns)
            new_row[self._time_column_validated] = future_ts
            future_rows.append(new_row)

        # Create DataFrame from future rows
        future_df = pd.DataFrame(future_rows)

        # Ensure the timestamp column has the same dtype
        future_df[self._time_column_validated] = pd.to_datetime(
            future_df[self._time_column_validated]
        )

        # Align column order with original dataframe
        future_df = future_df[data_frame.columns]

        # Preserve original data types as much as possible
        # for non-timestamp columns
        for col in data_frame.columns:
            if col != self._time_column_validated:
                # Try to maintain the original dtype
                # (will be nullable version due to NaN)
                try:
                    original_dtype = data_frame[col].dtype
                    # For numeric types, pandas will handle
                    # the NaN conversion automatically
                    if pd.api.types.is_numeric_dtype(original_dtype):
                        # Let pandas handle it naturally
                        # (int -> float for NaN compatibility)
                        pass
                    elif pd.api.types.is_datetime64_any_dtype(original_dtype):
                        future_df[col] = pd.to_datetime(future_df[col])
                except Exception:
                    # If conversion fails, keep as is
                    # (likely already None/NaN)
                    pass

        # Concatenate original data with future data
        try:
            extended_df = pd.concat([data_frame, future_df], ignore_index=True)
        except Exception as e:
            raise ValueError(
                f"Error concatenating original and extended data: {e}. "
                "This might be due to incompatible data types."
            ) from e

        # Validate the extended dataframe
        if len(extended_df) != len(data_frame) + self.n_steps:
            raise ValueError(
                f"Extended dataset has unexpected number of rows. "
                f"Expected: {len(data_frame) + self.n_steps}, "
                f"Got: {len(extended_df)}"
            )

        # Convert back to DashAIDataset
        return to_dashai_dataset(extended_df)

    def changes_row_count(self) -> bool:
        """
        Indicates that this converter changes the number of rows.

        Returns
        -------
        bool
            True, as new rows with future timestamps are added
        """
        return True
