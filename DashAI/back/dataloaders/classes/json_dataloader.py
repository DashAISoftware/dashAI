"""DashAI JSON Dataloader."""

from typing import TYPE_CHECKING, Any, Dict

from DashAI.back.core.schema_fields import none_type, schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class JSONDataloaderSchema(BaseSchema):
    """Schema for JSONDataLoader hyperparameters.

    Configures the ``data_key`` (optional top-level JSON key whose value is
    the list of records) and the dataset split ratios. When ``data_key`` is
    ``None``, the entire JSON value is interpreted as the record list.
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
    data_key: schema_field(
        none_type(string_field()),
        placeholder="data",
        description=MultilingualString(
            en=(
                "In case the data has the form "
                '{"data": [{"col1": val1, "col2": val2, ...}]} '
                '(also known as "table" in pandas), name of the field "data", '
                "where the list with dictionaries with the data should be found. "
                "In case the format is only a list of dictionaries (also known as "
                '"records" orient in pandas), set this value as null.'
            ),
            es=(
                "En caso de que los datos tengan la forma "
                '{"data": [{"col1": val1, "col2": val2, ...}]} '
                '(también conocido como "table" en pandas), nombre del campo "data", '
                "donde se debe encontrar la lista con diccionarios con los datos. "
                "En caso de que el formato sea solo una lista de diccionarios "
                '(también conocido como orientación "records" en pandas), '
                "establezca este valor como null."
            ),
        ),
        alias=MultilingualString(en="Data key", es="Clave de datos"),
    )  # type: ignore


class JSONDataLoader(BaseDataLoader):
    """Data loader that ingests record-oriented JSON files into DashAI datasets.

    Parses JSON files containing an array of record objects (one object per
    row) and converts them to ``DashAIDataset`` train/validation/test splits.
    An optional ``data_key`` parameter allows the records to be nested under a
    top-level key (e.g. ``{"data": [{...}, ...]}``) rather than at the root.

    Multi-file uploads are concatenated before splitting, and the split ratios
    are validated before loading to provide early failure feedback.
    """

    COMPATIBLE_COMPONENTS = [
        "TabularClassificationTask",
        "TextClassificationTask",
        "TranslationTask",
    ]
    SCHEMA = JSONDataloaderSchema

    DESCRIPTION: str = MultilingualString(
        en=(
            "Data loader for tabular data in JSON files. "
            "Supports both standard JSON array format (a list of dictionaries) "
            "and nested JSON data where records are contained within a specific key."
        ),
        es=(
            "Cargador de datos para datos tabulares en archivos JSON. "
            "Soporta tanto el formato de array JSON estándar (una lista de "
            "diccionarios) como datos JSON anidados donde los registros están "
            "contenidos dentro de una clave específica."
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="JSON Data Loader",
        es="Cargador de Datos JSON",
    )

    def _check_params(self, params: Dict[str, Any]) -> None:
        """Validate JSON dataloader parameters before loading.

        Parameters
        ----------
        params : Dict[str, Any]
            Parameter dictionary that must contain ``data_key`` (str or None).

        Raises
        ------
        ValueError
            If ``data_key`` is not present in ``params``.
        TypeError
            If ``data_key`` is not a string or ``None``.
        """
        if "data_key" not in params:
            raise ValueError(
                "Error trying to load the JSON dataset: "
                "data_key parameter was not provided."
            )

        if not (isinstance(params["data_key"], str) or params["data_key"] is None):
            raise TypeError(
                "params['data_key'] should be a string or None, "
                f"got {type(params['data_key'])}"
            )

    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = None,
    ) -> "DashAIDataset":
        """Load the uploaded JSON dataset into a DatasetDict.

        Parameters
        ----------
        filepath_or_buffer : str
            An URL where the dataset is located or a FastAPI/Uvicorn uploaded file
            object.
        temp_path : str
            The temporary path where the files will be extracted and then uploaded.
        params : Dict[str, Any]
            Dict with the dataloader parameters. The options are:
            - data_key (str): The key of the json where the data is contained.
        n_sample : int | None
            Indicates how many rows load from the dataset, all rows if null.

        Returns
        -------
        DatasetDict
            A HuggingFace's Dataset with the loaded data.
        """
        import shutil

        from datasets import Dataset, IterableDatasetDict, load_dataset

        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        self._check_params(params)
        field = params["data_key"]
        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)

        if prepared_path[1] == "file":
            dataset = load_dataset(
                "json",
                data_files=prepared_path[0],
                field=field,
                streaming=bool(n_sample),
            )
        else:
            dataset = load_dataset(
                "json", data_dir=prepared_path[0], field=field, streaming=bool(n_sample)
            )
            shutil.rmtree(prepared_path[0])
        if n_sample:
            if type(dataset) is IterableDatasetDict:
                dataset = dataset["train"]
            dataset = Dataset.from_list(list(dataset.take(n_sample)))
        return to_dashai_dataset(dataset)

    def load_preview(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
        n_rows: int = 100,
    ):
        """
        Load a preview of the JSON dataset using streaming.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to the JSON file.
        params : Dict[str, Any]
            Parameters for loading the JSON (data_key).
        n_rows : int, optional
            Number of rows to preview. Default is 100.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing the preview rows.
        """
        from itertools import islice

        import pandas as pd
        from datasets import load_dataset

        self._check_params(params)
        field = params.get("data_key")

        dataset_stream = load_dataset(
            "json",
            data_files=filepath_or_buffer,
            field=field,
            streaming=True,
            split="train",
        )

        sample_rows = list(islice(dataset_stream, n_rows))

        return pd.DataFrame(sample_rows)
