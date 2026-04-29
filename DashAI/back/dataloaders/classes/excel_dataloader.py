"""DashAI Excel Dataloader."""

from typing import TYPE_CHECKING, Any, Dict

from DashAI.back.core.schema_fields import (
    bool_field,
    int_field,
    none_type,
    schema_field,
    string_field,
    union_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ExcelDataloaderSchema(BaseSchema):
    """Schema for ExcelDataLoader hyperparameters.

    Configures the sheet selector, header row, columns to import,
    row-skipping and row-count limit, and the dataset split ratios.
    The sheet can be specified as a name string or a zero-based index;
    leaving the sheet field empty selects the first sheet.
    """

    name: schema_field(
        string_field(),
        "",
        description=MultilingualString(
            en=(
                "Custom name to register your dataset. If no name is specified, "
                "the name of the uploaded file will be used."
            ),
            es=(
                "Nombre personalizado para registrar su dataset. Si no se especifica "
                "un nombre, se usará el nombre del archivo subido."
            ),
        ),
        alias=MultilingualString(en="Name", es="Nombre"),
    )  # type: ignore
    sheet: schema_field(
        union_type(int_field(ge=0), string_field()),
        placeholder=0,
        description=MultilingualString(
            en=(
                "The name of the sheet to read or its zero-based index. "
                "If a string is provided, the reader will search for a sheet named "
                "exactly as the string. If an integer is provided, the reader will "
                "select the sheet at the corresponding index. By default, the first "
                "sheet will be read."
            ),
            es=(
                "El nombre de la hoja a leer o su índice basado en cero. "
                "Si se proporciona una cadena, el lector buscará una hoja con ese "
                "nombre exacto. Si se proporciona un entero, el lector seleccionará "
                "la hoja en el índice correspondiente. Por defecto, se leerá la "
                "primera hoja."
            ),
        ),
        alias=MultilingualString(en="Sheet", es="Hoja"),
    )  # type: ignore
    header: schema_field(
        none_type(int_field(ge=0)),
        placeholder=0,
        description=MultilingualString(
            en=(
                "The row number where the column names are located, indexed from 0. "
                "If null, the file will be considered to have no column names."
            ),
            es=(
                "El número de fila donde se encuentran los nombres de columna, "
                "indexado desde 0. Si es null, se considerará que el archivo no "
                "tiene nombres de columna."
            ),
        ),
        alias=MultilingualString(en="Header", es="Encabezado"),
    )  # type: ignore
    usecols: schema_field(
        none_type(string_field()),
        placeholder=None,
        description=MultilingualString(
            en=(
                "If None, the reader will load all columns. If str, then indicates "
                "comma separated list of Excel column letters and column ranges "
                '(e.g. "A:E" or "A,C,E:F"). Ranges are inclusive of both sides.'
            ),
            es=(
                "Si es None, el lector cargará todas las columnas. Si es str, indica "
                "una lista separada por comas de letras de columna de Excel y rangos "
                'de columna (ej. "A:E" o "A,C,E:F"). Los rangos son inclusivos en '
                "ambos lados."
            ),
        ),
        alias=MultilingualString(en="Use columns", es="Usar columnas"),
    )  # type: ignore

    skiprows: schema_field(
        none_type(int_field(ge=0)),
        None,
        description=MultilingualString(
            en=(
                "Number of rows to skip at the start of the file. "
                "Leave empty to not skip any rows."
            ),
            es=(
                "Número de filas a omitir al inicio del archivo. "
                "Deje vacío para no omitir ninguna fila."
            ),
        ),
        alias=MultilingualString(en="Skip rows", es="Omitir filas"),
    )  # type: ignore

    nrows: schema_field(
        none_type(int_field(ge=1)),
        None,
        description=MultilingualString(
            en="Number of rows to read. Leave empty to read all rows.",
            es="Número de filas a leer. Deje vacío para leer todas las filas.",
        ),
        alias=MultilingualString(en="N rows", es="N filas"),
    )  # type: ignore

    names: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en=(
                "Comma-separated list of column names to use. "
                "Example: 'col1,col2,col3'. Leave empty to use header row."
            ),
            es=(
                "Lista de nombres de columna separados por comas. "
                "Ejemplo: 'col1,col2,col3'. Deje vacío para usar la fila de "
                "encabezado."
            ),
        ),
        alias=MultilingualString(en="Names", es="Nombres"),
    )  # type: ignore

    na_values: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en=(
                "Comma-separated additional strings to recognize as NA/NaN. "
                "Example: 'NA,N/A,null'."
            ),
            es=(
                "Cadenas adicionales separadas por comas para reconocer como NA/NaN. "
                "Ejemplo: 'NA,N/A,null'."
            ),
        ),
        alias=MultilingualString(en="NA values", es="Valores NA"),
    )  # type: ignore

    keep_default_na: schema_field(
        bool_field(),
        True,
        description=MultilingualString(
            en="Whether to include the default NaN values when parsing the data.",
            es=(
                "Si se deben incluir los valores NaN predeterminados al analizar los "
                "datos."
            ),
        ),
        alias=MultilingualString(en="Keep default NA", es="Mantener NA predeterminado"),
    )  # type: ignore

    true_values: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Comma-separated values to consider as True. Example: 'yes,true,1'.",
            es=(
                "Valores separados por comas a considerar como True. "
                "Ejemplo: 'yes,true,1'."
            ),
        ),
        alias=MultilingualString(en="True values", es="Valores verdaderos"),
    )  # type: ignore

    false_values: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Comma-separated values to consider as False. Example: 'no,false,0'.",
            es=(
                "Valores separados por comas a considerar como False. "
                "Ejemplo: 'no,false,0'."
            ),
        ),
        alias=MultilingualString(en="False values", es="Valores falsos"),
    )  # type: ignore


class ExcelDataLoader(BaseDataLoader):
    """Data loader that ingests tabular data from Excel workbooks into DashAI datasets.

    Reads ``.xlsx`` / ``.xls`` files, optionally selecting a specific sheet,
    samples rows, and splits the result into train/validation/test
    ``DashAIDataset`` splits. Delegates to ``pandas.read_excel`` after
    normalising the schema parameters (sheet name/index, header row, column
    selection, row limits).

    Handles multi-file uploads by concatenating all workbooks before splitting.
    """

    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = ExcelDataloaderSchema

    DESCRIPTION: str = MultilingualString(
        en=(
            "Data loader for tabular data in Excel files. "
            "Supports xls, xlsx, xlsm, xlsb, odf, ods and odt file extensions."
        ),
        es=(
            "Cargador de datos para datos tabulares en archivos Excel. "
            "Soporta extensiones de archivo xls, xlsx, xlsm, xlsb, odf, ods y odt."
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Excel Data Loader",
        es="Cargador de Datos Excel",
    )
    ICON: str = "BorderAll"
    TAGS: list[str] = ["tabular", "spreadsheet", ".xlsx", ".xls"]

    def _prepare_pandas_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert schema parameters into a dict suitable for ``pandas.read_excel``.

        Maps DashAI schema keys to their pandas equivalents and normalises
        comma-separated string fields (``names``, ``na_values``,
        ``true_values``, ``false_values``) into Python lists.

        Parameters
        ----------
        params : Dict[str, Any]
            Raw parameter dictionary from the schema (``sheet``, ``header``,
            ``usecols``, ``skiprows``, ``nrows``, ``names``, ``na_values``,
            ``keep_default_na``, ``true_values``, ``false_values``).

        Returns
        -------
        Dict[str, Any]
            Keyword-argument dict ready to be unpacked into ``pd.read_excel``.
        """
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

    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = None,
    ) -> "DashAIDataset":
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
        n_sample : int | None
            Indicates how many rows load from the dataset, all rows if null.

        Returns
        -------
        DatasetDict
            A HuggingFace's Dataset with the loaded data.
        """
        import glob
        import shutil

        import pandas as pd
        from datasets import Dataset, DatasetDict
        from datasets.builder import DatasetGenerationError

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)
        print("path prepared", prepared_path)

        pandas_params = self._prepare_pandas_params(params)

        if prepared_path[1] == "file":
            try:
                dataset = pd.read_excel(
                    io=prepared_path[0], **pandas_params, nrows=n_sample
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
                    pd.read_excel(io=file_path, **pandas_params, nrows=n_sample)
                    for file_path in sorted(train_files)
                ]

                train_df = pd.concat(train_df_list)
                test_df_list = [
                    pd.read_excel(io=file_path, **pandas_params, nrows=n_sample)
                    for file_path in sorted(test_files)
                ]
                test_df_list = pd.concat(test_df_list)

                val_df_list = [
                    pd.read_excel(io=file_path, **pandas_params, nrows=n_sample)
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

    def load_preview(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
        n_rows: int = 10,
    ):
        """
        Load a preview of the Excel dataset.

        Note: Excel doesn't support native streaming in the same way as CSV/JSON,
        so we use nrows parameter to limit memory usage.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to the Excel file.
        params : Dict[str, Any]
            Parameters for loading Excel (sheet, header, etc.).
        n_rows : int, optional
            Number of rows to preview. Default is 10.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the preview rows.
        """
        pandas_params = self._prepare_pandas_params(params)
        pandas_params["nrows"] = n_rows

        import pandas as pd

        df_preview = pd.read_excel(
            io=filepath_or_buffer,
            **pandas_params,
        )

        return df_preview
