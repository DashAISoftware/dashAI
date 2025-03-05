"""DashAI CSV Type Inference Dataloader."""

import os
import shutil
from typing import Any, Dict, Union

from beartype import beartype
from datasets import DatasetDict, load_dataset
from starlette.datastructures import UploadFile

from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader, CSVDataloaderSchema


class CSVTypeInferenceDataLoader(CSVDataLoader):
    """Data loader for tabular data in CSV files with automatic type inference."""

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = CSVDataloaderSchema  # Usamos el mismo esquema que CSVDataLoader
    DESCRIPTION = "A dataloader that automatically infers column types from CSV files"

    @beartype
    def load_data(
        self,
        filepath_or_buffer: Union[UploadFile, str],
        temp_path: str,
        params: Dict[str, Any],
    ) -> DatasetDict:
        """Load the uploaded CSV files into a DatasetDict with automatic type inference.

        Parameters
        ----------
        filepath_or_buffer : Union[UploadFile, str], optional
            An URL where the dataset is located or a FastAPI/Uvicorn uploaded file
            object.
        temp_path : str
            The temporary path where the files will be extracted and then uploaded.
        params : Dict[str, Any]
            Dict with the dataloader parameters. The options are:
            - `separator` (str): The character that delimits the CSV data.

        Returns
        -------
        DatasetDict
            A HuggingFace's Dataset with the loaded data and inferred types.
        """
        # Use the _check_params method from CSVDataLoader
        self._check_params(params)
        separator = params["separator"]

        if isinstance(filepath_or_buffer, str):
            dataset = load_dataset(
                "csv",
                data_files=filepath_or_buffer,
                sep=separator,
                infer_column_types=True,  # Enable type inference
            )

        elif isinstance(filepath_or_buffer, UploadFile):
            files_path = self.extract_files(
                temp_path,
                filepath_or_buffer,
            )
            if files_path.split("/")[-1] == "files":
                try:
                    dataset = load_dataset(
                        "csv",
                        data_dir=files_path,
                        sep=separator,
                        infer_column_types=True,  # Enable type inference
                    )
                finally:
                    shutil.rmtree(temp_path, ignore_errors=True)
            else:
                try:
                    dataset = load_dataset(
                        "csv",
                        data_files=files_path,
                        sep=separator,
                        infer_column_types=True,  # Enable type inference
                    )
                finally:
                    os.remove(files_path)

        return dataset 