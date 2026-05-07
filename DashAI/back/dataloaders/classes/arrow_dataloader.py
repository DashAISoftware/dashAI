"""DashAI Arrow IPC Dataloader."""

import glob
import shutil
from typing import TYPE_CHECKING, Any, Dict

from DashAI.back.core.schema_fields import none_type, schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ArrowDataloaderSchema(BaseSchema):
    """Schema for ArrowDataLoader hyperparameters."""

    columns: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en=(
                "Comma-separated list of column names to load. "
                "Leave empty to load all columns."
            ),
            es=(
                "Lista de nombres de columnas separados por comas para cargar. "
                "Deje vacío para cargar todas las columnas."
            ),
        ),
        alias=MultilingualString(en="Columns", es="Columnas"),
    )  # type: ignore


class ArrowDataLoader(BaseDataLoader):
    """Data loader that ingests tabular data from Apache Arrow IPC files.

    Reads one or more Arrow IPC files (.arrow) using pyarrow, with optional
    column selection, and converts the result into DashAI datasets. Handles
    multi-file uploads via ZIP archives containing train/test/val split folders.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".arrow", ".zip"})
    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = ArrowDataloaderSchema

    DESCRIPTION: str = MultilingualString(
        en=(
            "Data loader for tabular data in Apache Arrow IPC files. "
            "Arrow IPC is a high-performance columnar in-memory format "
            "for efficient data interchange."
        ),
        es=(
            "Cargador de datos para datos tabulares en archivos Apache Arrow IPC. "
            "Arrow IPC es un formato columnar en memoria de alto rendimiento "
            "para intercambio eficiente de datos."
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Arrow Data Loader",
        es="Cargador de Datos Arrow",
    )

    def _parse_columns(self, params: Dict[str, Any]):
        """Parse the columns parameter into a list or None.

        Parameters
        ----------
        params : Dict[str, Any]
            Dataloader parameters.

        Returns
        -------
        list[str] | None
            List of column names, or None to load all columns.
        """
        raw = params.get("columns")
        if not raw:
            return None
        return [c.strip() for c in raw.split(",") if c.strip()]

    def _read_arrow_file(self, filepath: str, columns=None):
        """Read an Arrow IPC file and return a pandas DataFrame.

        Parameters
        ----------
        filepath : str
            Path to the Arrow IPC file.
        columns : list[str] | None
            Columns to load, or None for all.

        Returns
        -------
        pd.DataFrame
            Loaded DataFrame.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the file cannot be parsed as valid Arrow IPC.
        """
        from datasets.builder import DatasetGenerationError

        try:
            import pyarrow.ipc as ipc

            with ipc.open_file(filepath) as reader:
                table = reader.read_all()
            if columns:
                table = table.select(columns)
            return table.to_pandas()
        except Exception as e:
            raise DatasetGenerationError from e

    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = None,
    ) -> "DashAIDataset":
        """Load uploaded Arrow IPC files into a DatasetDict.

        Parameters
        ----------
        filepath_or_buffer : str
            Path or URL to an Arrow IPC file or a ZIP archive with split folders.
        temp_path : str
            Temporary directory for file extraction.
        params : Dict[str, Any]
            Dataloader parameters (see ArrowDataloaderSchema).
        n_sample : int | None
            Maximum rows to load, or None for all.

        Returns
        -------
        DashAIDataset
            Dataset with loaded data.
        """
        import pandas as pd
        from datasets import Dataset, DatasetDict

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        columns = self._parse_columns(params)
        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)

        if prepared_path[1] == "file":
            arrow_df = self._read_arrow_file(prepared_path[0], columns=columns)
            if n_sample is not None:
                arrow_df = arrow_df.head(n_sample)
            dataset_dict = DatasetDict(
                {"train": Dataset.from_pandas(arrow_df, preserve_index=False)}
            )
        else:
            train_files = glob.glob(prepared_path[0] + "/train/*")
            test_files = glob.glob(prepared_path[0] + "/test/*")
            val_files = glob.glob(prepared_path[0] + "/val/*") + glob.glob(
                prepared_path[0] + "/validation/*"
            )
            try:
                train_df = pd.concat(
                    [
                        self._read_arrow_file(f, columns=columns)
                        for f in sorted(train_files)
                    ]
                )
                test_df = pd.concat(
                    [
                        self._read_arrow_file(f, columns=columns)
                        for f in sorted(test_files)
                    ]
                )
                val_df = pd.concat(
                    [
                        self._read_arrow_file(f, columns=columns)
                        for f in sorted(val_files)
                    ]
                )
                if n_sample is not None:
                    train_df = train_df.head(n_sample)
                    test_df = test_df.head(n_sample)
                    val_df = val_df.head(n_sample)
                dataset_dict = DatasetDict(
                    {
                        "train": Dataset.from_pandas(train_df, preserve_index=False),
                        "test": Dataset.from_pandas(test_df, preserve_index=False),
                        "validation": Dataset.from_pandas(val_df, preserve_index=False),
                    }
                )
            finally:
                shutil.rmtree(prepared_path[0])
        return to_dashai_dataset(dataset_dict)

    def load_preview(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
        n_rows: int = 100,
    ):
        """Load a preview of the Arrow IPC dataset.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to the Arrow IPC file.
        params : Dict[str, Any]
            Dataloader parameters (see ArrowDataloaderSchema).
        n_rows : int, optional
            Maximum rows to return. Default is 100.

        Returns
        -------
        pd.DataFrame
            Preview DataFrame.
        """
        columns = self._parse_columns(params)
        arrow_df = self._read_arrow_file(filepath_or_buffer, columns=columns)
        return arrow_df.head(n_rows)
