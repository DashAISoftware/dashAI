"""DashAI CSV Dataloader."""

import shutil
from typing import Any, Dict

from beartype import beartype
from datasets import load_dataset

from DashAI.back.core.schema_fields import (
    bool_field,
    enum_field,
    int_field,
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
        enum_field([",", ";", "blank space", "tab"]),
        ",",
        "A separator character delimits the data in a CSV file.",
    )  # type: ignore

    header: schema_field(
        string_field(),
        "infer",
        (
            "Row number(s) containing column labels and marking the start of the data "
            "(zero-indexed). Default behavior is to infer the column names. If column "
            "names are passed explicitly, this should be set to '0'. "
            "Header can also be a list of integers that specify row locations "
            "for MultiIndex on the columns."
        ),
    )  # type: ignore

    names: schema_field(
        none_type(string_field()),
        None,
        (
            "Comma-separated list of column names to use. If the file contains a "
            "header row, "
            "then you should explicitly pass header=0 to override the column names. "
            "Example: 'col1,col2,col3'. Leave empty to use file headers."
        ),
    )  # type: ignore

    encoding: schema_field(
        enum_field(["utf-8", "latin1", "cp1252", "iso-8859-1"]),
        "utf-8",
        "Encoding to use for UTF when reading/writing. Most common encodings provided.",
    )  # type: ignore

    na_values: schema_field(
        none_type(string_field()),
        None,
        (
            "Comma-separated additional strings to recognize as NA/NaN. "
            "Example: 'NULL,missing,n/a'"
        ),
    )  # type: ignore

    keep_default_na: schema_field(
        bool_field(),
        True,
        (
            "Whether to include the default NaN values when parsing the data "
            "(True recommended)."
        ),
    )  # type: ignore

    true_values: schema_field(
        none_type(string_field()),
        None,
        "Comma-separated values to consider as True. Example: 'yes,true,1,on'",
    )  # type: ignore

    false_values: schema_field(
        none_type(string_field()),
        None,
        "Comma-separated values to consider as False. Example: 'no,false,0,off'",
    )  # type: ignore

    skip_blank_lines: schema_field(
        bool_field(),
        True,
        "If True, skip over blank lines rather than interpreting as NaN values.",
    )  # type: ignore

    skiprows: schema_field(
        none_type(int_field()),
        None,
        "Number of lines to skip at the beginning of the file. "
        "Leave empty to skip none.",
    )  # type: ignore

    nrows: schema_field(
        none_type(int_field()),
        None,
        "Number of rows to read from the file. Leave empty to read all rows.",
    )  # type: ignore


class CSVDataLoader(BaseDataLoader):
    """Data loader for tabular data in CSV files."""

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = CSVDataloaderSchema

    DESCRIPTION: str = """
    Data loader for tabular data in CSV files.
    All uploaded CSV files must have the same column structure and use
    consistent separators.
    """

    def _check_params(
        self,
        params: Dict[str, Any],
    ) -> None:
        if "separator" not in params:
            raise ValueError(
                "Error trying to load the CSV dataset: "
                "separator parameter was not provided."
            )

        clean_params = {}

        separator = params["separator"]
        if separator == "blank space":
            separator = " "
        elif separator == "tab":
            separator = "\t"
        if not isinstance(separator, str):
            raise TypeError(
                f"Param separator should be a string, got {type(params['separator'])}"
            )
        clean_params["delimiter"] = separator

        if params.get("header") is not None:
            clean_params["header"] = params["header"]

        list_params = ["names", "na_values", "true_values", "false_values"]
        for param in list_params:
            if param in params and params[param]:
                clean_params[param] = [val.strip() for val in params[param].split(",")]

        bool_params = ["keep_default_na", "skip_blank_lines"]
        for param in bool_params:
            if param in params and params[param] is not None:
                clean_params[param] = params[param]

        int_params = ["skiprows", "nrows"]
        for param in int_params:
            if param in params and params[param] is not None:
                if not isinstance(params[param], int):
                    raise TypeError(
                        f"Param {param} should be an integer, got {type(params[param])}"
                    )
                clean_params[param] = params[param]

        if "encoding" in params and params["encoding"]:
            valid_encodings = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
            if params["encoding"] not in valid_encodings:
                raise ValueError(f"Invalid encoding: {params['encoding']}")
            clean_params["encoding"] = params["encoding"]

        return clean_params

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
        print("parameters are", params)
        clean_params = self._check_params(params)
        print("cleaned parameters are", clean_params)
        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)
        if prepared_path[1] == "file":
            dataset = load_dataset(
                "csv",
                data_files=prepared_path[0],
                **clean_params,
            )
        else:
            dataset = load_dataset(
                "csv",
                data_dir=prepared_path[0],
                **clean_params,
            )
            shutil.rmtree(prepared_path[0])

        return to_dashai_dataset(dataset)
