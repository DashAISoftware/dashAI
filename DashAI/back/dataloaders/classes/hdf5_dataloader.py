"""DashAI HDF5 Dataloader."""

import glob
import shutil
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from DashAI.back.core.schema_fields import (
    int_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader

if TYPE_CHECKING:
    from pandas import DataFrame

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class HDF5DataloaderSchema(BaseSchema):
    """Schema for HDF5DataLoader hyperparameters.

    Selects which object inside the HDF5 container is read as a table, which
    of its columns are kept, and which row range is loaded. Leaving the key
    empty makes the loader pick the first object in the file that can be
    read as a table.
    """

    key: schema_field(
        none_type(string_field()),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Path of the object to read inside the HDF5 file, for example "
                "'df' or '/group/dataset'. Leave empty to let the loader pick "
                "the first object that can be read as a table."
            ),
            es=(
                "Ruta del objeto a leer dentro del archivo HDF5, por ejemplo "
                "'df' o '/grupo/dataset'. Deje vacío para que el cargador "
                "seleccione el primer objeto que pueda leerse como tabla."
            ),
            pt=(
                "Caminho do objeto a ser lido dentro do arquivo HDF5, por exemplo "
                "'df' ou '/grupo/dataset'. Deixe vazio para que o carregador "
                "selecione o primeiro objeto que possa ser lido como tabela."
            ),
            de=(
                "Pfad des zu lesenden Objekts in der HDF5-Datei, zum Beispiel "
                "'df' oder '/gruppe/dataset'. Leer lassen, damit der Datenlader "
                "das erste als Tabelle lesbare Objekt auswählt."
            ),
            zh=(
                "HDF5文件内要读取的对象路径，例如'df'或'/group/dataset'。"
                "留空则由加载器选择第一个可作为表读取的对象。"
            ),
        ),
        alias=MultilingualString(
            en="Key", es="Clave", pt="Chave", de="Schlüssel", zh="键"
        ),
    )  # type: ignore

    columns: schema_field(
        none_type(string_field()),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Comma-separated list of column names to keep. "
                "Example: 'col1,col2'. Leave empty to load all columns."
            ),
            es=(
                "Lista de nombres de columna separados por comas a conservar. "
                "Ejemplo: 'col1,col2'. Deje vacío para cargar todas las columnas."
            ),
            pt=(
                "Lista de nomes de coluna separados por vírgulas a manter. "
                "Exemplo: 'col1,col2'. Deixe vazio para carregar todas as colunas."
            ),
            de=(
                "Kommagetrennte Liste der zu behaltenden Spaltennamen. "
                "Beispiel: 'col1,col2'. Leer lassen, um alle Spalten zu laden."
            ),
            zh="要保留的列名逗号分隔列表。示例：'col1,col2'。留空则加载所有列。",
        ),
        alias=MultilingualString(
            en="Columns", es="Columnas", pt="Colunas", de="Spalten", zh="列"
        ),
    )  # type: ignore

    start: schema_field(
        none_type(int_field(ge=0)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Index of the first row to read, indexed from 0. "
                "Leave empty to start from the first row."
            ),
            es=(
                "Índice de la primera fila a leer, indexado desde 0. "
                "Deje vacío para comenzar desde la primera fila."
            ),
            pt=(
                "Índice da primeira linha a ler, indexado a partir de 0. "
                "Deixe vazio para começar da primeira linha."
            ),
            de=(
                "Index der ersten zu lesenden Zeile, nullbasiert. "
                "Leer lassen, um bei der ersten Zeile zu beginnen."
            ),
            zh="要读取的第一行索引，从0开始。留空则从第一行开始。",
        ),
        alias=MultilingualString(
            en="Start row",
            es="Fila inicial",
            pt="Linha inicial",
            de="Startzeile",
            zh="起始行",
        ),
    )  # type: ignore

    stop: schema_field(
        none_type(int_field(ge=0)),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Index of the row to stop at, exclusive. "
                "Leave empty to read until the last row."
            ),
            es=(
                "Índice de la fila donde detenerse, exclusivo. "
                "Deje vacío para leer hasta la última fila."
            ),
            pt=(
                "Índice da linha onde parar, exclusivo. "
                "Deixe vazio para ler até a última linha."
            ),
            de=(
                "Index der Zeile, bei der gestoppt wird, exklusiv. "
                "Leer lassen, um bis zur letzten Zeile zu lesen."
            ),
            zh="停止读取的行索引，不含该行。留空则读取至最后一行。",
        ),
        alias=MultilingualString(
            en="Stop row",
            es="Fila final",
            pt="Linha final",
            de="Endzeile",
            zh="结束行",
        ),
    )  # type: ignore


class HDF5DataLoader(BaseDataLoader):
    """Data loader that ingests tabular data from HDF5 files into DashAI datasets.

    HDF5 is a container format, so two very different layouts are supported:

    - Files written by pandas (a PyTables ``HDFStore``), recognised by their
      ``pandas_type`` attribute and read through ``pandas.read_hdf``.
    - Files written directly with ``h5py``, read as a 2D dataset (one column
      per matrix column), a 1D dataset with a compound dtype (one column per
      field), or a group of equal-length 1D datasets (one column per member).

    Both layouts carry explicit dtypes, so the loader exposes native types
    instead of relying on statistical inference. Multifile uploads are handled
    through ZIP archives containing train/test/val folders.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".h5", ".hdf5", ".hdf", ".zip"})
    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = HDF5DataloaderSchema
    SUPPORTS_NATIVE_TYPES: bool = True
    # Keyed by numpy dtype kind character.
    NATIVE_TYPE_MAPPING: Dict[str, Dict[str, Any]] = {
        "i": {"type": "Integer", "dtype": "int64"},
        "u": {"type": "Integer", "dtype": "int64"},
        "f": {"type": "Float", "dtype": "float64"},
        # Booleans are represented as categorical, following PTYPE_TO_DASHAI.
        "b": {"type": "Categorical", "dtype": "string", "encoder": "one_hot"},
        "S": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
        "U": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
        "O": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
        # Dates and times are mapped to text until date support is implemented.
        "M": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
        "m": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
        "c": {"type": "Text", "dtype": "string", "encoding": "utf-8"},
    }

    DESCRIPTION: str = MultilingualString(
        en=(
            "Data loader for tabular data in HDF5 files. "
            "Reads both stores written by pandas and plain h5py files "
            "(2D matrices, compound datasets or groups of columns). "
            "Supports h5, hdf5 and hdf file extensions."
        ),
        es=(
            "Cargador de datos para datos tabulares en archivos HDF5. "
            "Lee tanto almacenes escritos por pandas como archivos h5py simples "
            "(matrices 2D, datasets compuestos o grupos de columnas). "
            "Soporta las extensiones de archivo h5, hdf5 y hdf."
        ),
        pt=(
            "Carregador de dados para dados tabulares em arquivos HDF5. "
            "Lê tanto armazenamentos escritos por pandas como arquivos h5py "
            "simples (matrizes 2D, datasets compostos ou grupos de colunas). "
            "Suporta as extensões de arquivo h5, hdf5 e hdf."
        ),
        de=(
            "Datenlader für tabellarische Daten in HDF5-Dateien. "
            "Liest sowohl von pandas geschriebene Speicher als auch einfache "
            "h5py-Dateien (2D-Matrizen, zusammengesetzte Datasets oder "
            "Spaltengruppen). Unterstützt die Dateierweiterungen h5, hdf5 und hdf."
        ),
        zh=(
            "HDF5文件表格数据加载器。"
            "既可读取pandas写入的存储，也可读取普通h5py文件"
            "（二维矩阵、复合数据集或列分组）。"
            "支持h5、hdf5和hdf文件扩展名。"
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="HDF5 Data Loader",
        es="Cargador de Datos HDF5",
        pt="Carregador de Dados HDF5",
        de="HDF5 Datenlader",
        zh="HDF5数据加载器",
    )

    # ------------------------------------------------------------------
    # Parameter helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_columns(params: Dict[str, Any]) -> List[str] | None:
        """Split the comma-separated ``columns`` parameter into a list.

        Parameters
        ----------
        params : Dict[str, Any]
            Dataloader parameters.

        Returns
        -------
        List[str] or None
            Column names to keep, or ``None`` when all columns are wanted.
        """
        raw = params.get("columns")
        if raw is None:
            return None
        columns = [name.strip() for name in str(raw).split(",") if name.strip()]
        return columns or None

    @staticmethod
    def _decode_if_bytes(value: Any) -> Any:
        """Return ``value`` UTF-8 decoded if it is bytes, otherwise unchanged."""
        return value.decode("utf-8") if isinstance(value, bytes) else value

    # ------------------------------------------------------------------
    # Layout detection
    # ------------------------------------------------------------------

    @staticmethod
    def _has_pandas_metadata(file: Any, key: str | None) -> bool:
        """Tell whether the file (or ``key`` within it) was written by pandas.

        pandas tags every object it writes to an ``HDFStore`` with a
        ``pandas_type`` attribute, which is what distinguishes a store from a
        plain h5py file.

        Parameters
        ----------
        file : h5py.File
            Open HDF5 file.
        key : str or None
            Object path requested by the user, or ``None`` for autodetection.

        Returns
        -------
        bool
            ``True`` if the object must be read with ``pandas.read_hdf``.
        """
        if key is not None:
            node = file.get(key)
            return node is not None and "pandas_type" in node.attrs
        return any("pandas_type" in file[name].attrs for name in file)

    def _is_table_group(self, group: Any) -> bool:
        """Tell whether a group holds one equal-length 1D dataset per column."""
        import h5py

        members = [group[name] for name in group]
        if not members:
            return False
        if not all(
            isinstance(member, h5py.Dataset)
            and member.ndim == 1
            and member.dtype.names is None
            for member in members
        ):
            return False
        return len({len(member) for member in members}) == 1

    def _search_node(self, group: Any) -> Any | None:
        """Find the first object in ``group`` that can be read as a table.

        Datasets that already hold a whole table (2D matrices and compound
        1D datasets) win over groups of columns, which in turn win over plain
        1D datasets (a single column). The search then recurses into subgroups.

        Parameters
        ----------
        group : h5py.Group
            Group to search, typically the file root.

        Returns
        -------
        h5py.Dataset, h5py.Group or None
            The chosen node, or ``None`` when the group holds nothing readable.
        """
        import h5py

        subgroups = []
        for name in group:
            item = group[name]
            if isinstance(item, h5py.Dataset):
                if item.ndim == 2 or (item.ndim == 1 and item.dtype.names is not None):
                    return item
            else:
                subgroups.append(item)

        for subgroup in subgroups:
            if self._is_table_group(subgroup):
                return subgroup

        for name in group:
            item = group[name]
            if isinstance(item, h5py.Dataset) and item.ndim == 1:
                return item

        for subgroup in subgroups:
            found = self._search_node(subgroup)
            if found is not None:
                return found

        return None

    def _resolve_node(self, file: Any, key: str | None) -> Any:
        """Return the node named by ``key``, or the autodetected one.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If ``key`` is missing from the file, or if no object in the file
            can be read as a table.
        """
        from datasets.builder import DatasetGenerationError

        if key is not None:
            node = file.get(key)
            if node is None:
                raise DatasetGenerationError(
                    f"Key '{key}' was not found in the HDF5 file."
                )
            return node

        if self._is_table_group(file):
            return file

        node = self._search_node(file)
        if node is None:
            raise DatasetGenerationError(
                "The HDF5 file does not contain any object that can be read as a table."
            )
        return node

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def _matrix_column_names(self, node: Any) -> List[str]:
        """Return column names for a 2D dataset, from its attributes if present."""
        import numpy as np

        for attribute in ("column_names", "columns"):
            if attribute in node.attrs:
                names = np.atleast_1d(node.attrs[attribute])
                return [str(self._decode_if_bytes(name)) for name in names]
        return [f"col_{index}" for index in range(node.shape[1])]

    def _node_to_dataframe(self, node: Any) -> "DataFrame":
        """Convert an HDF5 dataset or group into a pandas DataFrame.

        Parameters
        ----------
        node : h5py.Dataset or h5py.Group
            Node resolved from the file.

        Returns
        -------
        DataFrame
            One column per matrix column, compound field or group member.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the node has more than two dimensions, is an empty group, or is
            a group whose members are not equal-length 1D datasets.
        """
        import h5py
        import pandas as pd
        from datasets.builder import DatasetGenerationError

        if isinstance(node, h5py.Dataset):
            if node.dtype.names is not None:
                data = node[...]
                return pd.DataFrame(
                    {name: data[name] for name in node.dtype.names},
                )
            if node.ndim == 1:
                return pd.DataFrame({node.name.split("/")[-1]: node[...]})
            if node.ndim == 2:
                return pd.DataFrame(
                    node[...],
                    columns=self._matrix_column_names(node),
                )
            raise DatasetGenerationError(
                f"Dataset '{node.name}' has {node.ndim} dimensions; only one- "
                "and two-dimensional datasets can be read as a table."
            )

        members = {name: node[name] for name in node}
        if not members:
            raise DatasetGenerationError(
                f"Group '{node.name}' is empty, there is no data to read."
            )
        for name, member in members.items():
            if not isinstance(member, h5py.Dataset) or member.ndim != 1:
                raise DatasetGenerationError(
                    f"Group member '{name}' is not a one-dimensional dataset, "
                    "so the group cannot be read as a table."
                )
        if len({len(member) for member in members.values()}) != 1:
            raise DatasetGenerationError(
                f"Members of group '{node.name}' have different lengths, "
                "so the group cannot be read as a table."
            )
        return pd.DataFrame({name: member[...] for name, member in members.items()})

    def _decode_byte_columns(self, dataframe: "DataFrame") -> "DataFrame":
        """Decode fixed-length byte-string columns to UTF-8 text."""
        for column in dataframe.columns:
            if dataframe[column].dtype == object:
                dataframe[column] = dataframe[column].map(self._decode_if_bytes)
        return dataframe

    @staticmethod
    def _apply_row_slice(dataframe: "DataFrame", params: Dict[str, Any]) -> "DataFrame":
        """Keep only the rows in the ``[start, stop)`` range, if given."""
        start = params.get("start")
        stop = params.get("stop")
        if start is None and stop is None:
            return dataframe
        return dataframe.iloc[slice(start, stop)].reset_index(drop=True)

    def _select_columns(
        self, dataframe: "DataFrame", columns: List[str] | None
    ) -> "DataFrame":
        """Keep only ``columns``, failing loudly on names absent from the file."""
        from datasets.builder import DatasetGenerationError

        if not columns:
            return dataframe
        missing = [name for name in columns if name not in dataframe.columns]
        if missing:
            raise DatasetGenerationError(
                f"Columns {missing} were not found in the HDF5 file."
            )
        return dataframe[columns]

    def _read_with_pandas(self, filepath: str, params: Dict[str, Any]) -> "DataFrame":
        """Read a pandas ``HDFStore`` file through ``pandas.read_hdf``.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If pandas cannot read the store with the given parameters, for
            example when column or row selection is used on a store written in
            the ``fixed`` format.
        """
        import pandas as pd
        from datasets.builder import DatasetGenerationError

        read_params: Dict[str, Any] = {}
        if params.get("key") is not None:
            read_params["key"] = params["key"]
        columns = self._parse_columns(params)
        if columns is not None:
            read_params["columns"] = columns
        for bound in ("start", "stop"):
            if params.get(bound) is not None:
                read_params[bound] = params[bound]

        try:
            data = pd.read_hdf(filepath, **read_params)
        except Exception as e:
            raise DatasetGenerationError from e

        if not isinstance(data, pd.DataFrame):
            data = data.to_frame()
        return data.reset_index(drop=True)

    def _read_with_h5py(self, filepath: str, params: Dict[str, Any]) -> "DataFrame":
        """Read a plain h5py file as a table.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the file cannot be opened, the requested key is missing, or the
            selected node cannot be read as a table.
        """
        import h5py
        from datasets.builder import DatasetGenerationError

        try:
            with h5py.File(filepath, "r") as file:
                node = self._resolve_node(file, params.get("key"))
                dataframe = self._node_to_dataframe(node)
        except DatasetGenerationError:
            raise
        except Exception as e:
            raise DatasetGenerationError from e

        dataframe = self._decode_byte_columns(dataframe)
        dataframe = self._apply_row_slice(dataframe, params)
        return self._select_columns(dataframe, self._parse_columns(params))

    def _reader_for(self, filepath: str, params: Dict[str, Any]) -> str:
        """Return ``"pandas"`` or ``"h5py"`` for the given file.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the file is not a valid HDF5 container.
        """
        import h5py
        from datasets.builder import DatasetGenerationError

        try:
            with h5py.File(filepath, "r") as file:
                if self._has_pandas_metadata(file, params.get("key")):
                    return "pandas"
        except Exception as e:
            raise DatasetGenerationError from e
        return "h5py"

    def _read_hdf5_file(
        self, filepath: str, params: Dict[str, Any]
    ) -> Tuple["DataFrame", str]:
        """Read an HDF5 file with whichever reader matches its layout.

        Parameters
        ----------
        filepath : str
            Path to a single HDF5 file already on disk.
        params : Dict[str, Any]
            Dataloader parameters (``key``, ``columns``, ``start``, ``stop``).

        Returns
        -------
        tuple of (DataFrame, str)
            The loaded table and the name of the reader that produced it,
            either ``"pandas"`` or ``"h5py"``.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the file cannot be read as a table.
        """
        reader = self._reader_for(filepath, params)
        if reader == "pandas":
            return self._read_with_pandas(filepath, params), reader
        return self._read_with_h5py(filepath, params), reader

    # ------------------------------------------------------------------
    # Native types
    # ------------------------------------------------------------------

    def _node_dtypes(self, node: Any) -> Dict[str, Any]:
        """Read one dtype per column from an h5py node, without loading data.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the node cannot be read as a table.
        """
        import h5py
        from datasets.builder import DatasetGenerationError

        if isinstance(node, h5py.Dataset):
            if node.dtype.names is not None:
                return {name: node.dtype[name] for name in node.dtype.names}
            if node.ndim == 1:
                return {node.name.split("/")[-1]: node.dtype}
            if node.ndim == 2:
                return dict.fromkeys(self._matrix_column_names(node), node.dtype)
            raise DatasetGenerationError(
                f"Dataset '{node.name}' has {node.ndim} dimensions; only one- "
                "and two-dimensional datasets can be read as a table."
            )

        dtypes: Dict[str, Any] = {}
        for name in node:
            member = node[name]
            if not isinstance(member, h5py.Dataset) or member.ndim != 1:
                raise DatasetGenerationError(
                    f"Group member '{name}' is not a one-dimensional dataset, "
                    "so the group cannot be read as a table."
                )
            dtypes[name] = member.dtype
        if not dtypes:
            raise DatasetGenerationError(
                f"Group '{node.name}' is empty, there is no data to read."
            )
        return dtypes

    def _pandas_store_dtypes(
        self, filepath: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Read one dtype per column from a pandas store, reading a single row.

        Categorical columns keep the full category list, which pandas stores
        as table metadata rather than deriving it from the rows read.
        """
        probe_params = dict(params)
        probe_params.pop("columns", None)
        probe_params["start"] = 0
        probe_params["stop"] = 1
        try:
            dataframe = self._read_with_pandas(filepath, probe_params)
        except Exception:
            # Stores in the "fixed" format reject row selection.
            full_params = dict(params)
            full_params.pop("columns", None)
            full_params.pop("start", None)
            full_params.pop("stop", None)
            dataframe = self._read_with_pandas(filepath, full_params)
        return dict(dataframe.dtypes)

    def _native_type_for(self, dtype: Any, reader: str) -> Dict[str, Any]:
        """Build the DashAI type dict for a single column dtype.

        Parameters
        ----------
        dtype : numpy.dtype or pandas.api.extensions.ExtensionDtype
            Column dtype as declared by the file.
        reader : str
            Reader that produced the dtype, ``"pandas"`` or ``"h5py"``.

        Returns
        -------
        Dict[str, Any]
            Same dict shape produced by ``DashAIPtype.infer_types``.
        """
        import pandas as pd

        categories = None
        if isinstance(dtype, pd.CategoricalDtype):
            info = {"type": "Categorical", "dtype": "string", "encoder": "one_hot"}
            categories = [str(category) for category in dtype.categories]
        else:
            info = dict(
                self.NATIVE_TYPE_MAPPING.get(
                    dtype.kind,
                    {"type": "Text", "dtype": "string", "encoding": "utf-8"},
                )
            )
            if dtype.kind == "b":
                categories = ["False", "True"]

        if categories is not None:
            info["categories"] = categories

        info["inference_reason"] = {
            "source": "hdf5_metadata",
            "reader": reader,
            "native_type": str(dtype),
            "final_type": info.get("type"),
            "is_categorical": info.get("type") == "Categorical",
        }
        return info

    def extract_native_types(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        """Build the DashAI column-type map from the HDF5 dtypes themselves.

        Both layouts declare their dtypes, so no statistical inference is
        needed. For the h5py layout the dtypes are read from the file
        metadata without loading any data; for the pandas layout a single row
        is read, which is enough to recover dtypes and the categories of
        ``category`` columns.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to a single HDF5 file already on disk.
        params : Dict[str, Any]
            Dataloader parameters, same dict that ``load_preview`` receives.

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Column name -> DashAI type dict.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the file cannot be read as a table.
        """
        import h5py
        from datasets.builder import DatasetGenerationError

        reader = self._reader_for(filepath_or_buffer, params)

        if reader == "pandas":
            dtypes = self._pandas_store_dtypes(filepath_or_buffer, params)
        else:
            try:
                with h5py.File(filepath_or_buffer, "r") as file:
                    node = self._resolve_node(file, params.get("key"))
                    dtypes = self._node_dtypes(node)
            except DatasetGenerationError:
                raise
            except Exception as e:
                raise DatasetGenerationError from e

        columns = self._parse_columns(params)
        if columns is not None:
            dtypes = {name: dtypes[name] for name in columns if name in dtypes}

        return {
            name: self._native_type_for(dtype, reader) for name, dtype in dtypes.items()
        }

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = None,
    ) -> "DashAIDataset":
        """Load uploaded HDF5 files into a DashAI dataset.

        Parameters
        ----------
        filepath_or_buffer : str
            Path or URL to an HDF5 file, or to a ZIP archive with split folders.
        temp_path : str
            Temporary directory for file extraction.
        params : Dict[str, Any]
            Dataloader parameters (``key``, ``columns``, ``start``, ``stop``).
        n_sample : int | None
            Maximum rows to load, or None for all.

        Returns
        -------
        DashAIDataset
            Dataset with the loaded data.
        """
        import pandas as pd
        from datasets import Dataset, DatasetDict

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)

        if prepared_path[1] == "file":
            dataframe = self._read_hdf5_file(prepared_path[0], params)[0]
            if n_sample is not None:
                dataframe = dataframe.head(n_sample)
            dataset_dict = DatasetDict(
                {"train": Dataset.from_pandas(dataframe, preserve_index=False)}
            )
        else:
            train_files = glob.glob(prepared_path[0] + "/train/*")
            test_files = glob.glob(prepared_path[0] + "/test/*")
            val_files = glob.glob(prepared_path[0] + "/val/*") + glob.glob(
                prepared_path[0] + "/validation/*"
            )
            try:
                split_frames = {}
                for split, files in (
                    ("train", train_files),
                    ("test", test_files),
                    ("validation", val_files),
                ):
                    frames = [
                        self._read_hdf5_file(file_path, params)[0]
                        for file_path in sorted(files)
                    ]
                    dataframe = pd.concat(frames)
                    if n_sample is not None:
                        dataframe = dataframe.head(n_sample)
                    split_frames[split] = Dataset.from_pandas(
                        dataframe, preserve_index=False
                    )
                dataset_dict = DatasetDict(split_frames)
            finally:
                shutil.rmtree(prepared_path[0])

        return to_dashai_dataset(dataset_dict)

    def load_preview(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
        n_rows: int = 10,
    ) -> "DataFrame":
        """Load a preview of the HDF5 dataset.

        The row range is narrowed before reading so that only the previewed
        rows are pulled from disk. Stores that reject row selection (the
        pandas ``fixed`` format) are read whole and then truncated.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to the HDF5 file.
        params : Dict[str, Any]
            Dataloader parameters (``key``, ``columns``, ``start``, ``stop``).
        n_rows : int, optional
            Number of rows to preview. Default is 10.

        Returns
        -------
        DataFrame
            A DataFrame containing the preview rows.
        """
        from datasets.builder import DatasetGenerationError

        start = params.get("start") or 0
        stop = params.get("stop")
        preview_stop = start + n_rows if stop is None else min(stop, start + n_rows)

        preview_params = {**params, "start": start, "stop": preview_stop}
        try:
            dataframe = self._read_hdf5_file(filepath_or_buffer, preview_params)[0]
        except DatasetGenerationError:
            dataframe = self._read_hdf5_file(filepath_or_buffer, params)[0]

        return dataframe.head(n_rows)
