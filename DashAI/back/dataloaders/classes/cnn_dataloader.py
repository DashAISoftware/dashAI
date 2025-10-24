"""DashAI CNN Dataloader for ECG time series data."""

import os
import shutil
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from beartype import beartype
from datasets import Dataset

from DashAI.back.core.schema_fields import (
    BaseSchema,
    bool_field,
    enum_field,
    list_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader


class CNNDataloaderSchema(BaseSchema):
    name: schema_field(
        string_field(),
        "",
        (
            "Custom name to register your dataset. If no name is specified, "
            "the name of the uploaded file will be used."
        ),
    )  # type: ignore

    metadata_cols: schema_field(
        list_field(string_field(), min_items=0),
        placeholder=["age", "sex"],
        description=(
            "List of column names to use as metadata features. "
            "Common options: age, sex"
        ),
    )  # type: ignore

    target_cols: schema_field(
        list_field(string_field(), min_items=1),
        placeholder=[
            "sinusal",
            "bradycardia",
            "tachycardia",
            "bradycardia_only",
            "tachycardia_only",
        ],
        description=(
            "List of column names to use as target labels (binary columns). "
            "default: sinusal,bradycardia,tachycardia,bradycardia_only,tachycardia_only"
        ),
    )  # type: ignore

    equilibrate_method: schema_field(
        none_type(enum_field(["oversample", "downsample"])),
        None,
        (
            "Method to balance classes in the dataset. "
            "Options: 'oversample', 'downsample', or None for no balancing."
        ),
    )  # type: ignore

    engine: schema_field(
        enum_field(["pyarrow", "fastparquet"]),
        "pyarrow",
        "Parquet engine to use for reading files.",
    )  # type: ignore


class CNNDataLoader(BaseDataLoader):
    """Data loader for ECG time series data stored as parquet files."""

    COMPATIBLE_COMPONENTS = ["TimeSeriesClassificationTask"]
    SCHEMA = CNNDataloaderSchema

    DESCRIPTION: str = """
    Data loader for ECG time series data with metadata.
    Expects a ZIP file containing:
    - A CSV file with columns: ecg_id, age, sex, and target columns (binary values)
    - An 'exams' directory with parquet files named {ecg_id}.parquet.gzip containing 
      the time series data (12 channels x 5000 time steps)
    
    The CSV should have:
    - ecg_id: unique identifier
    - age, sex: numeric metadata
    - Binary target columns (0/1 or True/False)
    - Other columns (like report, scp_codes) will be ignored
    """

    @beartype
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
    ) -> DashAIDataset:
        """Load ECG time series data into a DashAIDataset.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to a zip file containing:
            - CSV file(s) with metadata and labels
            - 'exams' directory with parquet files containing time series data
        temp_path : str
            Temporary path where files will be extracted
        params : Dict[str, Any]
            Parameters including:
            - metadata_cols: list of metadata column names (default: ['age', 'sex'])
            - target_cols: list of target column names (binary columns)
            - equilibrate_method: optional balancing method
            - engine: parquet engine to use

        Returns
        -------
        DashAIDataset
            A DashAI Dataset with the loaded ECG data
        """
        # Extract files if needed
        prepared_path, path_type = self.prepare_files(filepath_or_buffer, temp_path)

        if path_type != "dir":
            raise ValueError(
                "CNN DataLoader requires a zip file containing CSV and parquet files."
            )

        # Find CSV files and parquet directory
        csv_files = []
        parquet_dir = None

        for root, dirs, files in os.walk(prepared_path):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))

            # Look for 'exams' directory containing parquet files
            if "exams" in dirs:
                exams_path = os.path.join(root, "exams")
                if any(
                    f.endswith(".parquet.gzip") or f.endswith(".parquet")
                    for f in os.listdir(exams_path)
                ):
                    parquet_dir = exams_path
                    break

        if not csv_files:
            raise ValueError("No CSV files found in the uploaded zip.")

        if not parquet_dir:
            raise ValueError(
                "No 'exams' directory with parquet files found in the uploaded zip."
            )

        # Load and combine CSV files
        df_list = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            # Add dataset prefix if multiple CSVs
            if len(csv_files) > 1:
                dataset_name = os.path.splitext(os.path.basename(csv_file))[0]
                df["ecg_id"] = dataset_name + "_" + df["ecg_id"].astype(str)
            df_list.append(df)

        df = pd.concat(df_list, ignore_index=True)

        # Extract parameters
        metadata_cols = params.get("metadata_cols", ["age", "sex"])
        target_cols = params.get("target_cols", [])
        equilibrate_method = params.get("equilibrate_method", None)
        engine = params.get("engine", "pyarrow")

        if not target_cols:
            raise ValueError(
                "target_cols must be specified and non-empty. "
                "Example: ['sinusal', 'bradycardia', 'tachycardia']"
            )

        # Validate and clean columns
        df, metadata_cols, target_cols = self._validate_and_clean_columns(
            df, metadata_cols, target_cols
        )

        # Apply equilibration if requested
        if equilibrate_method:
            df = self._equilibrate_dataset(df, target_cols, equilibrate_method)

        # Load time series data and create dataset
        data_dict = self._load_time_series_data(
            df, parquet_dir, metadata_cols, target_cols, engine
        )

        # Clean up temporary files
        shutil.rmtree(prepared_path)

        # Create HuggingFace Dataset
        dataset = Dataset.from_dict(data_dict)

        return to_dashai_dataset(dataset)

    def _validate_and_clean_columns(
        self, df: pd.DataFrame, metadata_cols: List[str], target_cols: List[str]
    ) -> tuple:
        """Validate columns exist and are numeric, clean data."""

        # Check if ecg_id exists
        if "ecg_id" not in df.columns:
            raise ValueError("CSV must contain 'ecg_id' column")

        # Filter out non-numeric columns from metadata
        valid_metadata_cols = []
        for col in metadata_cols:
            if col not in df.columns:
                print(f"Warning: Metadata column '{col}' not found in CSV, skipping...")
                continue

            # Try to convert to numeric
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                # Fill NaN with median or 0
                if df[col].isnull().any():
                    median_val = df[col].median()
                    if pd.isna(median_val):
                        median_val = 0
                    df[col].fillna(median_val, inplace=True)
                    print(f"Info: Filled missing values in '{col}' with {median_val}")
                valid_metadata_cols.append(col)
            except Exception as e:
                print(
                    f"Warning: Could not convert '{col}' to numeric: {e}, skipping..."
                )
                continue

        if not valid_metadata_cols:
            print("Warning: No valid metadata columns found, using empty metadata")

        # Validate target columns
        valid_target_cols = []
        for col in target_cols:
            if col not in df.columns:
                print(f"Warning: Target column '{col}' not found in CSV, skipping...")
                continue

            # Convert boolean-like values to 0/1
            try:
                # Handle string representations
                if df[col].dtype == object:
                    df[col] = (
                        df[col]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        .map(
                            {
                                "1": 1.0,
                                "0": 0.0,
                                "true": 1.0,
                                "false": 0.0,
                                "yes": 1.0,
                                "no": 1.0,
                            }
                        )
                    )

                # Convert to numeric
                df[col] = pd.to_numeric(df[col], errors="coerce")

                # Fill NaN with 0 (assuming missing targets are negative)
                if df[col].isnull().any():
                    df[col].fillna(0.0, inplace=True)
                    print(f"Info: Filled missing values in target '{col}' with 0")

                # Ensure values are 0 or 1
                unique_vals = df[col].unique()
                if not all(v in [0.0, 1.0] for v in unique_vals):
                    print(
                        f"Warning: Target column '{col}' has non-binary values: {unique_vals}, "
                        "converting to binary (>0.5 = 1, <=0.5 = 0)"
                    )
                    df[col] = (df[col] > 0.5).astype(float)

                valid_target_cols.append(col)
            except Exception as e:
                print(
                    f"Warning: Could not process target column '{col}': {e}, skipping..."
                )
                continue

        if not valid_target_cols:
            raise ValueError(
                "No valid target columns found. Please specify binary target columns."
            )

        return df, valid_metadata_cols, valid_target_cols

    def _equilibrate_dataset(
        self, df: pd.DataFrame, target_cols: List[str], method: str
    ) -> pd.DataFrame:
        """Balance classes in the dataset."""
        # For multi-label, create a composite class indicator
        # Sum all targets + add a "normal" class (all zeros)
        target_matrix = df[target_cols].values

        # Create class identifier: convert each row to a tuple for unique identification
        class_ids = [tuple(row) for row in target_matrix]
        unique_classes, counts = np.unique(class_ids, return_counts=True, axis=0)

        # Find majority class
        majority_idx = np.argmax(counts)
        majority_class = unique_classes[majority_idx]

        # Separate indices
        majority_indices = [
            i for i, class_id in enumerate(class_ids) if class_id == majority_class
        ]
        minority_indices = [
            i for i, class_id in enumerate(class_ids) if class_id != majority_class
        ]

        if method == "oversample":
            target_size = len(majority_indices)
            if len(minority_indices) > 0:
                n_repeats = target_size // len(minority_indices)
                remainder = target_size % len(minority_indices)

                oversampled_minority = minority_indices * n_repeats
                if remainder > 0:
                    oversampled_minority.extend(
                        np.random.choice(
                            minority_indices, remainder, replace=False
                        ).tolist()
                    )

                balanced_indices = majority_indices + oversampled_minority
            else:
                balanced_indices = majority_indices

        elif method == "downsample":
            if len(minority_indices) > 0:
                target_size = len(minority_indices)
                if len(majority_indices) > target_size:
                    downsampled_majority = np.random.choice(
                        majority_indices, target_size, replace=False
                    ).tolist()
                    balanced_indices = downsampled_majority + minority_indices
                else:
                    balanced_indices = majority_indices + minority_indices
            else:
                balanced_indices = majority_indices
        else:
            raise ValueError(f"Unknown equilibrate_method: {method}")

        np.random.shuffle(balanced_indices)
        return df.iloc[balanced_indices].reset_index(drop=True)

    def _load_time_series_data(
        self,
        df: pd.DataFrame,
        parquet_dir: str,
        metadata_cols: List[str],
        target_cols: List[str],
        engine: str,
    ) -> Dict[str, List]:
        """Load time series data from parquet files."""
        data_dict = {
            "ecg_id": [],
            "time_series": [],
        }

        # Add metadata and target columns
        for col in metadata_cols:
            data_dict[col] = []
        for col in target_cols:
            data_dict[col] = []

        skipped_count = 0
        loaded_count = 0

        for idx, row in df.iterrows():
            ecg_id = str(row["ecg_id"]).strip()

            # Try multiple naming patterns for parquet files
            parquet_patterns = [
                f"{ecg_id}.parquet.gzip",
                f"{ecg_id}.parquet",
                f"{int(float(ecg_id))}.parquet.gzip",  # In case ecg_id is numeric
                f"{int(float(ecg_id))}.parquet",
            ]

            parquet_path = None
            for pattern in parquet_patterns:
                test_path = os.path.join(parquet_dir, pattern)
                if os.path.exists(test_path):
                    parquet_path = test_path
                    break

            if not parquet_path:
                if skipped_count < 10:  # Only print first 10 warnings
                    print(
                        f"Warning: Missing parquet file for ecg_id={ecg_id}, skipping..."
                    )
                skipped_count += 1
                continue

            try:
                # Load time series
                arr = pd.read_parquet(parquet_path, engine=engine)
                if hasattr(arr, "values"):
                    np_arr = arr.values
                else:
                    np_arr = arr.to_numpy()

                # Handle different array shapes
                if np_arr.ndim == 1:
                    if np_arr.size == 12 * 5000:
                        np_arr = np_arr.reshape(12, 5000)
                    else:
                        if skipped_count < 10:
                            print(
                                f"Warning: Unexpected array size {np_arr.size} for {ecg_id}, skipping..."
                            )
                        skipped_count += 1
                        continue
                elif np_arr.ndim == 2:
                    if np_arr.shape == (12, 5000):
                        pass
                    elif np_arr.shape == (5000, 12):
                        np_arr = np_arr.T
                    else:
                        if skipped_count < 10:
                            print(
                                f"Warning: Unexpected array shape {np_arr.shape} for {ecg_id}, skipping..."
                            )
                        skipped_count += 1
                        continue

                # Add to data dict
                data_dict["ecg_id"].append(ecg_id)
                data_dict["time_series"].append(np_arr.tolist())

                # Add metadata (ensure it's float)
                for col in metadata_cols:
                    try:
                        value = float(row[col])
                        data_dict[col].append(value)
                    except (ValueError, TypeError) as e:
                        print(
                            f"Warning: Could not convert metadata '{col}' to float for {ecg_id}: {e}"
                        )
                        data_dict[col].append(0.0)  # Default to 0

                # Add targets (ensure it's float)
                for col in target_cols:
                    try:
                        value = float(row[col])
                        data_dict[col].append(value)
                    except (ValueError, TypeError) as e:
                        print(
                            f"Warning: Could not convert target '{col}' to float for {ecg_id}: {e}"
                        )
                        data_dict[col].append(0.0)  # Default to 0

                loaded_count += 1

            except Exception as e:
                if skipped_count < 10:
                    print(f"Warning: Error loading {ecg_id}: {str(e)}, skipping...")
                skipped_count += 1
                continue

        if skipped_count > 10:
            print(f"... and {skipped_count - 10} more files were skipped")

        print(f"\nSuccessfully loaded {loaded_count} ECG records")
        print(f"Skipped {skipped_count} records due to errors or missing files")

        if loaded_count == 0:
            raise ValueError(
                "No ECG records could be loaded. Please check your data format."
            )

        return data_dict
