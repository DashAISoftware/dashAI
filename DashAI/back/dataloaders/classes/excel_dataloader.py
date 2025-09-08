"""DashAI Excel Dataloader."""

import glob
import shutil
from typing import Any, Dict

import pandas as pd
from beartype import beartype
from datasets import Dataset, DatasetDict
from datasets.builder import DatasetGenerationError

from DashAI.back.core.schema_fields import (
    bool_field,
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
        placeholder=None,
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

    skiprows: schema_field(
        none_type(int_field(ge=0)),
        None,
        (
            "Number of rows to skip at the start of the file. "
            "Leave empty to not skip any rows."
        ),
    )  # type: ignore

    nrows: schema_field(
        none_type(int_field(ge=1)),
        None,
        "Number of rows to read. Leave empty to read all rows.",
    )  # type: ignore

    names: schema_field(
        none_type(string_field()),
        None,
        (
            "Comma-separated list of column names to use. Example: 'col1,col2,col3'. "
            "Leave empty to use header row."
        ),
    )  # type: ignore

    na_values: schema_field(
        none_type(string_field()),
        None,
        (
            "Comma-separated additional strings to recognize as NA/NaN. "
            "Example: 'NA,N/A,null'."
        ),
    )  # type: ignore

    keep_default_na: schema_field(
        bool_field(),
        True,
        "Whether to include the default NaN values when parsing the data.",
    )  # type: ignore

    true_values: schema_field(
        none_type(string_field()),
        None,
        "Comma-separated values to consider as True. Example: 'yes,true,1'.",
    )  # type: ignore

    false_values: schema_field(
        none_type(string_field()),
        None,
        "Comma-separated values to consider as False. Example: 'no,false,0'.",
    )  # type: ignore


class ExcelDataLoader(BaseDataLoader):
    """Data loader for tabular data in Excel files."""

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = ExcelDataloaderSchema

    DESCRIPTION: str = """
    Data loader for tabular data in Excel files.
    Supports xls, xlsx, xlsm, xlsb, odf, ods and odt file extensions.
    """

    def _prepare_pandas_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters for pandas.read_excel."""
        pandas_params = {}

        if "sheet" in params and params["sheet"] is not None:
            pandas_params["sheet_name"] = params["sheet"]

        pandas_params["header"] = params.get("header", 0)

        if "usecols" in params and params["usecols"] is not None:
            pandas_params["usecols"] = params["usecols"]

        if "skiprows" in params and params["skiprows"] is not None:
            pandas_params["skiprows"] = params["skiprows"]

        if "nrows" in params and params["nrows"] is not None:
            pandas_params["nrows"] = params["nrows"]

        if "names" in params and params["names"] is not None:
            pandas_params["names"] = [
                name.strip() for name in params["names"].split(",")
            ]

        if "na_values" in params and params["na_values"] is not None:
            pandas_params["na_values"] = [
                val.strip() for val in params["na_values"].split(",")
            ]

        if "keep_default_na" in params and params["keep_default_na"] is not None:
            pandas_params["keep_default_na"] = params["keep_default_na"]

        if "true_values" in params and params["true_values"] is not None:
            pandas_params["true_values"] = [
                val.strip() for val in params["true_values"].split(",")
            ]

        if "false_values" in params and params["false_values"] is not None:
            pandas_params["false_values"] = [
                val.strip() for val in params["false_values"].split(",")
            ]

        return pandas_params

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
        print("path prepared", prepared_path)

        pandas_params = self._prepare_pandas_params(params)

        if prepared_path[1] == "file":
            try:
                dataset = pd.read_excel(
                    io=prepared_path[0],
                    **pandas_params,
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
                        **pandas_params,
                    )
                    for file_path in sorted(train_files)
                ]

                train_df = pd.concat(train_df_list)
                test_df_list = [
                    pd.read_excel(
                        io=file_path,
                        **pandas_params,
                    )
                    for file_path in sorted(test_files)
                ]
                test_df_list = pd.concat(test_df_list)

                val_df_list = [
                    pd.read_excel(
                        io=file_path,
                        **pandas_params,
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
