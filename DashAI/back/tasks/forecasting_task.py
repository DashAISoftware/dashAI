"""Forecasting Task for time series prediction in DashAI.

This task enables native time series forecasting with models like Prophet,
as well as tabular approaches using TimeSeriesWindowConverter.
"""

from typing import Any, Dict, List, Optional, Union

import pandas as pd
from datasets import DatasetDict, Value

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.tasks.base_task import BaseTask


class ForecastingTask(BaseTask):
    """Task for time series forecasting.

    This task handles two main forecasting approaches:
    1. Native forecasting (Prophet, ARIMA): Uses ds (datetime) + y + optional exogenous
    2. Tabular forecasting: Uses TimeSeriesWindowConverter + regression models

    Key differences from RegressionTask:
    - Requires temporal column (ds) and proper time ordering
    - Uses causal splits (no shuffle) to respect temporal causality
    - Supports forecasting-specific metrics (MAPE, sMAPE, MASE)
    - Native models can predict variable horizons
    """

    DESCRIPTION: str = """
    Time series forecasting predicts future values based on historical patterns.
    Supports both native forecasting models (Prophet) that work directly with
    timestamps and target values, and tabular approaches that convert time series
    into supervised learning problems using lag features and future windows.
    """

    metadata = {
        "inputs_types": [Value],  # ds (datetime) + optional exogenous variables
        "outputs_types": [Value],  # y (target time series)
        "inputs_cardinality": "n",  # ds + optional exogenous features
        "outputs_cardinality": 1,  # Single target series
    }

    def __init__(self):
        """Initialize ForecastingTask."""
        super().__init__()
        self._temporal_metadata: Optional[Dict[str, Any]] = None

    def validate_dataset_for_task(
        self,
        dataset: DashAIDataset,
        dataset_name: str,
        input_columns: List[str],
        output_columns: List[str],
    ) -> None:
        """Validate a dataset for forecasting task."""

        print("\n🔍 VALIDATE_DATASET_FOR_TASK INICIO")
        print(f"📄 Dataset: {dataset_name}")
        print(f"📥 Input columns: {input_columns}")
        print(f"📤 Output columns: {output_columns}")

        metadata = self.metadata
        allowed_input_types = tuple(metadata["inputs_types"])
        allowed_output_types = tuple(metadata["outputs_types"])

        # 🔍 DEBUG: Print full metadata
        print("\n📐 Metadata:")
        print(f" - allowed_input_types: {allowed_input_types}")
        print(f" - allowed_output_types: {allowed_output_types}")
        print(f" - input_cardinality: {metadata.get('inputs_cardinality')}")
        print(f" - output_cardinality: {metadata.get('outputs_cardinality')}")

        # Validate cardinality
        if len(input_columns) < 1:
            raise ValueError(
                "ForecastingTask requires at least 1 input column.\n"
                "Include a timestamp and optional exogenous variables."
            )

        if len(output_columns) != 1:
            raise ValueError(
                "ForecastingTask requires exactly 1 output column "
                f"(target to forecast). Got: {len(output_columns)} outputs."
            )

        dataset_df = dataset.to_pandas()
        if not isinstance(dataset_df, pd.DataFrame):
            dataset_df = pd.concat(dataset_df, ignore_index=True)

        # 🔬 Revisar tipos de columnas en dataset.features
        print("\n🧪 DEBUG: Column types from dataset.features")
        for col_name, col_type in dataset.features.items():
            print(f"  - {col_name}: {col_type} ({type(col_type)})")

        # Validate all input columns exist and have correct types
        timestamp_found = False
        detected_timestamp = None

        for input_col in input_columns:
            if input_col not in dataset.features:
                raise ValueError(
                    f"Input column '{input_col}' not found in dataset. "
                    f"Available columns: {list(dataset.features.keys())}"
                )

            input_col_type = dataset.features[input_col]

            # Print individual type check
            print(
                f"🔍 Checking input '{input_col}' type: {input_col_type} "
                f"({type(input_col_type)})"
            )

            if not isinstance(input_col_type, allowed_input_types):
                print("❌ Input column type mismatch")
                raise TypeError(
                    f"Input column '{input_col}' has type "
                    f"{type(input_col_type).__name__}, but expected one of: "
                    f"{allowed_input_types}."
                )

            # Try to detect if it's the timestamp
            if not timestamp_found:
                try:
                    pd.to_datetime(dataset_df[input_col])
                    timestamp_found = True
                    detected_timestamp = input_col
                    print(f"✅ Detected timestamp column: '{input_col}'")
                except Exception:
                    pass

        if not timestamp_found:
            raise ValueError(
                "No timestamp column detected in input columns. "
                "ForecastingTask requires a datetime column for temporal ordering. "
                f"Checked columns: {input_columns}"
            )

        # OUTPUT VALIDATION
        output_col = output_columns[0]
        if output_col not in dataset.features:
            raise ValueError(
                f"Output column '{output_col}' not found in dataset. "
                f"Available: {list(dataset.features.keys())}"
            )

        output_col_type = dataset.features[output_col]
        print(
            f"\n🔍 Checking output '{output_col}' type: {output_col_type} "
            f"({type(output_col_type)})"
        )

        if not isinstance(output_col_type, allowed_output_types):
            print("❌ Output column type mismatch")
            raise TypeError(
                f"Output column '{output_col}' has type "
                f"{type(output_col_type).__name__}, but expected one of: "
                f"{allowed_output_types}."
            )

        # Validate target column
        try:
            pd.to_numeric(dataset_df[output_col])
            print(f"✅ Target column '{output_col}' is numeric")
        except Exception as e:
            raise TypeError(
                f"Output column '{output_col}' cannot be converted to numeric: {e}"
            ) from e

        # Check minimum data points
        if len(dataset) < 5:
            raise ValueError(
                f"Dataset '{dataset_name}' has only {len(dataset)} rows. "
                "Minimum 5 rows required for forecasting."
            )

        # ✅ VALIDATION PASSED
        print("✅ ForecastingTask validation PASSED:")
        print(f"   - Inputs: {input_columns} (timestamp: {detected_timestamp})")
        print(f"   - Output: {output_col}")
        print(f"   - Total rows: {len(dataset)}\n")

    @property
    def schema(self) -> Dict[str, Any]:
        """Get the schema for ForecastingTask."""
        return {
            "type": "object",
            "properties": {
                "timestamp_column": {
                    "type": "string",
                    "description": (
                        "Name of the datetime column (will be renamed to 'ds')"
                    ),
                },
                "target_column": {
                    "type": "string",
                    "description": (
                        "Name of the target time series column (will be renamed to 'y')"
                    ),
                },
                "exogenous_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional exogenous variables (holidays, weather, etc.)"
                    ),
                    "default": [],
                },
                "frequency": {
                    "type": "string",
                    "description": (
                        "Time series frequency (D, H, M, etc.). "
                        "Auto-detected if not specified"
                    ),
                    "default": "auto",
                },
            },
            "required": ["timestamp_column", "target_column"],
        }

    def validate_temporal_data(
        self,
        dataset: DashAIDataset,
        timestamp_col: str,
        target_col: str,
        exog_cols: Optional[List[str]] = None,
    ) -> None:
        """Validate that the dataset is suitable for forecasting.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to validate
        timestamp_col : str
            Name of timestamp column
        target_col : str
            Name of target column
        exog_cols : Optional[List[str]]
            Names of exogenous columns

        Raises
        ------
        ValueError
            If dataset is not suitable for forecasting
        """
        if exog_cols is None:
            exog_cols = []

        # Check required columns exist
        available_cols = set(dataset.column_names)

        if timestamp_col not in available_cols:
            raise ValueError(
                f"Timestamp column '{timestamp_col}' not found in dataset. "
                f"Available columns: {list(available_cols)}"
            )

        if target_col not in available_cols:
            raise ValueError(
                f"Target column '{target_col}' not found in dataset. "
                f"Available columns: {list(available_cols)}"
            )

        missing_exog = set(exog_cols) - available_cols
        if missing_exog:
            raise ValueError(
                f"Exogenous columns not found: {list(missing_exog)}. "
                f"Available columns: {list(available_cols)}"
            )

        # Convert to pandas for validation
        dataset_df = dataset.to_pandas()  # type: ignore
        if not isinstance(dataset_df, pd.DataFrame):
            dataset_df = pd.concat(dataset_df, ignore_index=True)

        # Validate timestamp column can be converted to datetime
        try:
            timestamp_series = pd.to_datetime(dataset_df[timestamp_col])
        except Exception as e:
            raise ValueError(
                f"Cannot convert timestamp column '{timestamp_col}' to datetime: {e}"
            ) from e

        # Check for duplicate timestamps
        if timestamp_series.duplicated().any():
            duplicates = timestamp_series[timestamp_series.duplicated()].unique()
            raise ValueError(
                f"Found duplicate timestamps in '{timestamp_col}': "
                f"{duplicates[:5].tolist()}{'...' if len(duplicates) > 5 else ''}"
            )

        # Validate target is numeric
        try:
            target_series = pd.to_numeric(dataset_df[target_col])
        except Exception as e:
            raise ValueError(
                f"Target column '{target_col}' must be numeric: {e}"
            ) from e

        # Check for too many missing values in target
        missing_pct = target_series.isna().mean()
        if missing_pct > 0.5:
            raise ValueError(
                f"Target column '{target_col}' has {missing_pct:.1%} missing values. "
                "Maximum allowed is 50%."
            )

        # Minimum data points check
        if len(dataset_df) < 5:
            raise ValueError(
                f"Dataset has only {len(dataset_df)} rows. "
                "Minimum 5 data points required for forecasting."
            )

        print(
            f"✅ Validation passed: {len(dataset_df)} data points, "
            f"timestamp range: {timestamp_series.min()} to {timestamp_series.max()}"
        )

    def detect_frequency(self, timestamp_series: pd.Series) -> str:
        """Auto-detect time series frequency.

        Parameters
        ----------
        timestamp_series : pd.Series
            Datetime series

        Returns
        -------
        str
            Detected frequency code (D, H, M, etc.)
        """
        try:
            # Sort timestamps and calculate differences
            sorted_ts = timestamp_series.sort_values()
            diffs = sorted_ts.diff().dropna()

            # Get most common difference
            mode_diff = (
                diffs.mode().iloc[0] if len(diffs.mode()) > 0 else diffs.median()
            )

            # Map to pandas frequency codes
            if mode_diff >= pd.Timedelta(days=365):  # type: ignore
                return "A"  # Annual
            elif mode_diff >= pd.Timedelta(days=30):  # type: ignore
                return "M"  # Monthly
            elif mode_diff >= pd.Timedelta(days=7):  # type: ignore
                return "W"  # Weekly
            elif mode_diff >= pd.Timedelta(days=1):  # type: ignore
                return "D"  # Daily
            elif mode_diff >= pd.Timedelta(hours=1):  # type: ignore
                return "H"  # Hourly
            else:
                return "T"  # Minute

        except Exception:
            # Fallback to daily
            return "D"

    def detect_timestamp_column(
        self, dataset: DashAIDataset, candidate_columns: List[str]
    ) -> Optional[str]:
        """Auto-detect which column is the timestamp from a list of candidates.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to analyze
        candidate_columns : List[str]
            List of column names to check

        Returns
        -------
        Optional[str]
            Name of detected timestamp column, or None if not found
        """
        # Convert to pandas for analysis
        dataset_df = dataset.to_pandas()  # type: ignore
        if not isinstance(dataset_df, pd.DataFrame):
            dataset_df = pd.concat(dataset_df, ignore_index=True)

        # Strategy 1: Check by column name
        for col in candidate_columns:
            col_lower = col.lower()
            if any(
                keyword in col_lower
                for keyword in [
                    "date",
                    "time",
                    "timestamp",
                    "ds",
                    "datetime",
                    "fecha",
                ]
            ):
                # Verify it can be converted to datetime
                try:
                    pd.to_datetime(dataset_df[col])
                    return col
                except Exception:
                    continue

        # Strategy 2: Try to convert each column to datetime
        for col in candidate_columns:
            try:
                pd.to_datetime(dataset_df[col])
                return col
            except Exception:
                continue

        return None

    def prepare_for_task(
        self,
        dataset: Optional[Union[DatasetDict, DashAIDataset]] = None,
        outputs_columns: Optional[List[str]] = None,
        inputs_columns: Optional[List[str]] = None,
        **kwargs,
    ) -> DashAIDataset:
        """Prepare dataset for forecasting task.

        Cambios mínimos:
        - Acepta `datasetdict` (alias que usa experiments.py).
        - Si no vienen `inputs_columns` ni `timestamp_column`, intenta
          detectar el timestamp usando todos los nombres de columnas.
        """
        # --- Soporte para alias `datasetdict` usado por experiments.py ---
        if dataset is None and "datasetdict" in kwargs:
            dataset = kwargs.pop("datasetdict")
        if inputs_columns is None and "input_columns" in kwargs:
            inputs_columns = kwargs.pop("input_columns")
        if outputs_columns is None and "output_columns" in kwargs:
            outputs_columns = kwargs.pop("output_columns")

        # Convertir a DashAIDataset si viene como DatasetDict
        if isinstance(dataset, DatasetDict):
            split_name = "train" if "train" in dataset else list(dataset.keys())[0]
            dashai_dataset = to_dashai_dataset(dataset[split_name])
        elif dataset is not None:
            dashai_dataset = dataset
        else:
            raise ValueError("dataset parameter is required for prepare_for_task")

        # Validaciones básicas de parámetros
        if not outputs_columns or len(outputs_columns) != 1:
            raise ValueError(
                "ForecastingTask requires exactly 1 output column (target variable). "
                f"Got {len(outputs_columns) if outputs_columns else 0} columns."
            )
        target_col = outputs_columns[0]

        # Obtener o detectar columna timestamp
        timestamp_col = kwargs.get("timestamp_column")
        if not timestamp_col:
            # Si no nos dan inputs_columns, intentamos con TODAS las columnas
            candidate_inputs = (
                inputs_columns if inputs_columns else list(dashai_dataset.column_names)
            )
            timestamp_col = self.detect_timestamp_column(
                dashai_dataset, candidate_inputs
            )
            if not timestamp_col:
                raise ValueError(
                    "Could not auto-detect timestamp column. "
                    "Provide `timestamp_column` o incluya una columna con fecha/tiempo "
                    "('date', 'timestamp', 'ds', 'datetime', etc.)."
                )
            print(f"🔍 Auto-detected timestamp column: '{timestamp_col}'")

        # Exógenas: si no vienen inputs, por defecto ninguna
        if inputs_columns:
            exog_cols = [c for c in inputs_columns if c != timestamp_col]
        else:
            exog_cols = kwargs.get("exogenous_columns", [])

        frequency = kwargs.get("frequency", "auto")

        # Validar datos
        self.validate_temporal_data(
            dashai_dataset, timestamp_col, target_col, exog_cols
        )

        # Procesamiento pandas
        dataset_df = dashai_dataset.to_pandas()  # type: ignore
        if not isinstance(dataset_df, pd.DataFrame):
            dataset_df = pd.concat(dataset_df, ignore_index=True)

        # NO renombrar columnas - mantener nombres originales
        # El modelo (ej: Prophet) hará el renombramiento si lo necesita

        # Orden temporal
        # If the timestamp column is numeric (int/float), treat values as
        # sequential time-step indices rather than nanosecond epoch offsets.
        if pd.api.types.is_integer_dtype(
            dataset_df[timestamp_col]
        ) or pd.api.types.is_float_dtype(dataset_df[timestamp_col]):
            base_date = pd.Timestamp("2000-01-01")
            step_vals = dataset_df[timestamp_col]
            min_val = step_vals.min()
            dataset_df[timestamp_col] = base_date + pd.to_timedelta(
                (step_vals - min_val).astype(int), unit="D"
            )
            print(
                f"ℹ️  Column '{timestamp_col}' contains numeric values — "
                f"converted to day offsets starting from {base_date.date()}"
            )
        else:
            dataset_df[timestamp_col] = pd.to_datetime(dataset_df[timestamp_col])
        dataset_df = dataset_df.sort_values(timestamp_col).reset_index(drop=True)

        # Frecuencia
        if frequency == "auto":
            frequency = self.detect_frequency(dataset_df[timestamp_col])

        # Guardar metadatos con nombres ORIGINALES
        self._temporal_metadata = {
            "timestamp_col": timestamp_col,
            "target_col": target_col,
            "exog_cols": exog_cols,
            "frequency": frequency,
            "start_date": dataset_df[timestamp_col].min(),
            "end_date": dataset_df[timestamp_col].max(),
            "n_periods": len(dataset_df),
        }

        print("✅ Prepared forecasting dataset:")
        print(f"   - Timestamp: {timestamp_col}")
        print(f"   - Target: {target_col}")
        print(f"   - Frequency: {frequency}")
        print(f"   - Periods: {len(dataset_df)}")
        if exog_cols:
            print(f"   - Exogenous vars: {', '.join(exog_cols)}")

        # Volver a DashAIDataset
        from datasets import Dataset

        hf_dataset = Dataset.from_pandas(dataset_df)
        return to_dashai_dataset(hf_dataset)

    def process_predictions(
        self, dataset: DashAIDataset, predictions: Any, target_column: str
    ) -> Any:
        """Process forecasting predictions.

        For forecasting, predictions can be:
        - Simple array of values (point forecasts)
        - DataFrame with ds, yhat, yhat_lower, yhat_upper (Prophet style)
        - Dictionary with forecasts and confidence intervals

        Parameters
        ----------
        dataset : DashAIDataset
            Original dataset
        predictions : Any
            Model predictions
        target_column : str
            Target column name

        Returns
        -------
        Any
            Processed predictions
        """
        # If predictions is a DataFrame (Prophet style), extract yhat
        if hasattr(predictions, "yhat"):
            return predictions["yhat"].to_numpy()

        # If it's already an array, return as-is
        if hasattr(predictions, "shape"):
            return predictions

        # Handle list/tuple
        if isinstance(predictions, (list, tuple)):
            import numpy as np

            return np.array(predictions)

        return predictions

    def num_labels(self, dataset: DashAIDataset, output_column: str) -> None:
        """Return None — forecasting predicts continuous values, not discrete labels."""
        return None

    def get_temporal_metadata(self) -> Optional[Dict[str, Any]]:
        """Get temporal metadata from the last prepare_for_task call.

        Returns
        -------
        Optional[Dict[str, Any]]
            Temporal metadata including frequency, date range, etc.
        """
        return self._temporal_metadata
