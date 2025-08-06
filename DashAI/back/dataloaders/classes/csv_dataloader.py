"""DashAI CSV Dataloader."""

import shutil
from typing import Any, Dict

import pandas as pd
from beartype import beartype
from datasets import load_dataset

from DashAI.back.core.schema_fields import (
    enum_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader


class CSVDataloaderSchema(BaseSchema):
    name: schema_field(
        none_type(string_field()),
        "",
        (
            "Custom name to register your dataset. If no name is specified, "
            "the name of the uploaded file will be used."
        ),
    )  # type: ignore
    separator: schema_field(
        enum_field([",", ";", "\u0020", "\t"]),
        ",",
        "A separator character delimits the data in a CSV file.",
    )  # type: ignore


class CSVDataLoader(BaseDataLoader):
    """Data loader for tabular data in CSV files."""

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = CSVDataloaderSchema

    def _check_params(
        self,
        params: Dict[str, Any],
    ) -> None:
        if "separator" not in params:
            raise ValueError(
                "Error trying to load the CSV dataset: "
                "separator parameter was not provided."
            )
        separator = params["separator"]

        if not isinstance(separator, str):
            raise TypeError(
                f"Param separator should be a string, got {type(params['separator'])}"
            )

    @beartype
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
    ) -> DashAIDataset:
        """Load the uploaded CSV files into a DatasetDict.

        Parameters
        ----------
        filepath_or_buffer : str, optional
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
            A HuggingFace's Dataset with the loaded data.
        """
        self._check_params(params)
        separator = params["separator"]
        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)
        if prepared_path[1] == "file":
            dataset = load_dataset(
                "csv",
                data_files=prepared_path[0],
                delimiter=separator,
            )
        else:
            dataset = load_dataset(
                "csv",
                data_dir=prepared_path[0],
                delimiter=separator,
            )
            shutil.rmtree(prepared_path[0])

        return to_dashai_dataset(dataset)

    def load_preview(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
        n_rows: int = 5,
    ) -> pd.DataFrame:
        """Load a preview of the dataset.

        Parameters
        ----------
        filepath_or_buffer : str
            An URL where the dataset is located or a FastAPI/Uvicorn uploaded file
            object.
        params : Dict[str, Any]
            Dict with the dataloader parameters. The options are:
            - `separator` (str): The character that delimits the CSV data.
        n_rows : int, optional
            The number of rows to preview. Default is 5.
        """
        self._check_params(params)
        separator = params["separator"]
        prepared_path = self.prepare_files(filepath_or_buffer, None)

        if prepared_path[1] == "file":
            df = pd.read_csv(
                prepared_path[0],
                sep=separator,
                nrows=n_rows,
            )
        else:
            df = pd.read_csv(
                prepared_path[0],
                sep=separator,
                nrows=n_rows,
            )
            shutil.rmtree(prepared_path[0])
        return df
