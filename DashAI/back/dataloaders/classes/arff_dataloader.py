"""DashAI ARFF Dataloader."""

import glob
import shutil
from typing import TYPE_CHECKING, Any, Dict

from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class ARFFDataloaderSchema(BaseSchema):
    """Schema for ARFFDataLoader hyperparameters.

    ARFF files are self-describing; no parameters are required.
    """


class ARFFDataLoader(BaseDataLoader):
    """Data loader that ingests tabular data from ARFF files into DashAI datasets.

    Reads Weka ARFF files using scipy, decodes nominal attributes from bytes
    to UTF-8 strings, and converts the result into DashAI datasets. Handles
    multi-file uploads via ZIP archives containing train/test/val split folders.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".arff"})
    COMPATIBLE_COMPONENTS = ["TabularClassificationTask"]
    SCHEMA = ARFFDataloaderSchema

    DESCRIPTION: str = MultilingualString(
        en=(
            "Data loader for tabular data in ARFF files "
            "(Weka Attribute-Relation File Format). "
            "ARFF files are self-describing and require no additional parameters."
        ),
        es=(
            "Cargador de datos para datos tabulares en archivos ARFF "
            "(formato Weka Attribute-Relation File Format). "
            "Los archivos ARFF son autodescriptivos y no requieren "
            "parámetros adicionales."
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="ARFF Data Loader",
        es="Cargador de Datos ARFF",
    )

    def _read_arff_file(self, filepath: str):
        """Read an ARFF file and return a pandas DataFrame.

        Parameters
        ----------
        filepath : str
            Path to the ARFF file.

        Returns
        -------
        pd.DataFrame
            DataFrame with nominal columns decoded from bytes to UTF-8.

        Raises
        ------
        datasets.builder.DatasetGenerationError
            If the file cannot be parsed as valid ARFF.
        """
        import pandas as pd
        from datasets.builder import DatasetGenerationError
        from scipy.io import arff

        try:
            data, _ = arff.loadarff(filepath)
        except Exception as e:
            raise DatasetGenerationError from e

        arff_df = pd.DataFrame(data)
        for col in arff_df.columns:
            if arff_df[col].dtype == object:
                arff_df[col] = arff_df[col].str.decode("utf-8")
        return arff_df

    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = None,
    ) -> "DashAIDataset":
        """Load uploaded ARFF files into a DatasetDict.

        Parameters
        ----------
        filepath_or_buffer : str
            Path or URL to an ARFF file or a ZIP archive with split folders.
        temp_path : str
            Temporary directory for file extraction.
        params : Dict[str, Any]
            Dataloader parameters (unused; ARFF is self-describing).
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

        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)

        if prepared_path[1] == "file":
            arff_df = self._read_arff_file(prepared_path[0])
            if n_sample is not None:
                arff_df = arff_df.head(n_sample)
            dataset_dict = DatasetDict(
                {"train": Dataset.from_pandas(arff_df, preserve_index=False)}
            )
        else:
            train_files = glob.glob(prepared_path[0] + "/train/*")
            test_files = glob.glob(prepared_path[0] + "/test/*")
            val_files = glob.glob(prepared_path[0] + "/val/*") + glob.glob(
                prepared_path[0] + "/validation/*"
            )
            try:
                train_df = pd.concat(
                    [self._read_arff_file(f) for f in sorted(train_files)]
                )
                test_df = pd.concat(
                    [self._read_arff_file(f) for f in sorted(test_files)]
                )
                val_df = pd.concat([self._read_arff_file(f) for f in sorted(val_files)])
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
        """Load a preview of the ARFF dataset.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to the ARFF file.
        params : Dict[str, Any]
            Unused parameters.
        n_rows : int, optional
            Maximum rows to return. Default is 100.

        Returns
        -------
        pd.DataFrame
            Preview DataFrame.
        """
        arff_df = self._read_arff_file(filepath_or_buffer)
        return arff_df.head(n_rows)
