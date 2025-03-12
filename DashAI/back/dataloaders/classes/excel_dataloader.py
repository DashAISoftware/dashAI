"""DashAI Excel Dataloader."""

import glob
import shutil
from typing import Any, Dict

import pandas as pd
from beartype import beartype
from datasets import Dataset, DatasetDict
from datasets.builder import DatasetGenerationError

from DashAI.back.core.schema_fields import (
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader


class ExcelDataloaderSchema(BaseSchema):
    name: schema_field(
        none_type(string_field()),
        "",
        (
            "Custom name to register your dataset. If no name is specified, "
            "the name of the uploaded file will be used."
        ),
    )  # type: ignore
    sheet: schema_field(
        union_type(int_field(ge=0), string_field()),
        placeholder=0,
        description="""
        The name of the sheet to read or its zero-based index.
        If a string is provided, the reader will search for a sheet named exactly as
        the string.
        If an integer is provided, the reader will select the sheet at the corresponding
        index.
        By default, the first sheet will be read.
        """,
    )  # type: ignore
    header: schema_field(
        none_type(int_field(ge=0)),
        placeholder=0,
        description="""
        The row number where the column names are located, indexed from 0.
        If null, the file will be considered to have no column names.
        """,
    )  # type: ignore
    usecols: schema_field(
        none_type(string_field()),
        placeholder=None,
        description="""
        If None, the reader will load all columns.
        If str, then indicates comma separated list of Excel column letters and column
        ranges (e.g. “A:E” or “A,C,E:F”). Ranges are inclusive of both sides.
        """,
    )  # type: ignore


class ExcelDataLoader(BaseDataLoader):
    """Data loader for tabular data in Excel files."""

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = ExcelDataloaderSchema

    @beartype
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
    ) -> DashAIDataset:
        """Load the uploaded Excel files into a DatasetDict.

        Parameters
        ----------
        filepath_or_buffer : str
            An URL where the dataset is located or a FastAPI/Uvicorn uploaded file
            object.
        temp_path : str
            The temporary path where the files will be extracted and then uploaded.
        params : Dict[str, Any]
            Dict with the dataloader parameters.

        Returns
        -------
        DatasetDict
            A HuggingFace's Dataset with the loaded data.
        """
        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)
        if prepared_path[1] == "file":
            try:
                dataset = pd.read_excel(
                    io=prepared_path[0],
                    sheet_name=params["sheet"],
                    header=params["header"],
                    usecols=params["usecols"],
                )
            except ValueError as e:
                raise DatasetGenerationError from e
            dataset_dict = DatasetDict({"train": Dataset.from_pandas(dataset)})
        if prepared_path[1] == "dir":
            train_files = glob.glob(prepared_path[0] + "/train/*")
            test_files = glob.glob(prepared_path[0] + "/test/*")
            val_files = glob.glob(prepared_path[0] + "/val/*") + glob.glob(
                prepared_path[0] + "/validation/*"
            )
            try:
                train_df_list = [
                    pd.read_excel(
                        io=file_path,
                        sheet_name=params["sheet"],
                        header=params["header"],
                        usecols=params["usecols"],
                    )
                    for file_path in sorted(train_files)
                ]

                train_df = pd.concat(train_df_list)
                test_df_list = [
                    pd.read_excel(
                        io=file_path,
                        sheet_name=params["sheet"],
                        header=params["header"],
                        usecols=params["usecols"],
                    )
                    for file_path in sorted(test_files)
                ]
                test_df_list = pd.concat(test_df_list)

                val_df_list = [
                    pd.read_excel(
                        io=file_path,
                        sheet_name=params["sheet"],
                        header=params["header"],
                        usecols=params["usecols"],
                    )
                    for file_path in sorted(val_files)
                ]
                val_df = pd.concat(val_df_list)

                dataset_dict = DatasetDict(
                    {
                        "train": Dataset.from_pandas(train_df, preserve_index=False),
                        "test": Dataset.from_pandas(test_df_list, preserve_index=False),
                        "validation": Dataset.from_pandas(val_df, preserve_index=False),
                    }
                )
            except ValueError as e:
                raise DatasetGenerationError from e
            finally:
                shutil.rmtree(prepared_path[0])
        return to_dashai_dataset(dataset_dict)
