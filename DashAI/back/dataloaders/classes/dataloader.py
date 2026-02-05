"""DashAI base class for dataloaders."""

import logging
from abc import abstractmethod
from typing import Any, Dict, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

logger = logging.getLogger(__name__)


class BaseDataLoader(ConfigObject):
    """Abstract class with base methods for DashAI dataloaders."""

    TYPE: Final[str] = "DataLoader"

    @abstractmethod
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = False,
    ) -> DashAIDataset:
        """Load data abstract method.

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
        DashAIDataset
            A DashAI Dataset with the loaded data.
        """
        raise NotImplementedError

    def load_preview(
        self,
        filepath_or_buffer: str,
        params: Dict[str, Any],
        n_rows: int = 10,
    ) -> any:
        """
        Load a preview of the dataset using streaming.

        This is a default implementation that can be overridden by specific dataloaders
        for better performance.

        Parameters
        ----------
        filepath_or_buffer : str
            Path to the file or buffer to load.
        params : Dict[str, Any]
            Parameters for loading the data.
        n_rows : int, optional
            Number of rows to preview. Default is 10.

        Returns
        -------
        DataFrame
            A pandas DataFrame with the preview data.
        """
        raise NotImplementedError(
            "load_preview must be implemented by specific dataloader"
        )

    def prepare_files(self, file_path: str, temp_path: str) -> str:
        """Prepare the files to load the data.

        Args:
            file_path (str): Path of the file to be prepared.
            temp_path (str): Temporary path where the files will be extracted.

        Returns
        -------

            path (str): Path of the files prepared.
            type_path (str): Type of the path.

        """
        from datasets.download.download_manager import DownloadManager

        if file_path.startswith("http"):
            file_path = DownloadManager.download_and_extract(file_path, temp_path)
            return (file_path, "dir")

        if file_path.lower().endswith(".zip"):
            extracted_path = self.extract_files(
                file_path=file_path, temp_path=temp_path
            )
            return (extracted_path, "dir")

        else:
            return (file_path, "file")

    def extract_files(self, file_path: str, temp_path: str) -> str:
        """Extract the files to load the data in a DataDict later.

        Args:
            temp_path (str): Path where dataset will be saved.
            file_path (str): Path of the file to be extracted.
        Returns
        -------
            str: Path of the files extracted.
        """
        import os
        import zipfile

        files_path = os.path.join(temp_path, "files")
        os.makedirs(files_path, exist_ok=True)
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(files_path)
        return files_path
