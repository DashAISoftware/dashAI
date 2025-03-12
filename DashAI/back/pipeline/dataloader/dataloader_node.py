import logging
from typing import Any, Dict, Union

from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader
from datasets import DatasetDict
from starlette.datastructures import UploadFile

logger = logging.getLogger(__name__)

class DataloaderNode:
    """Node for handling dataset upload by delegating to existing methods."""

    def __init__(self, dataloader: BaseDataLoader, temp_path: str):
        """
        Initializes the DataloaderNode.

        Parameters
        ----------
        dataloader : BaseDataLoader
            An instance of a dataloader that implements dataset processing methods.
        temp_path : str
            Temporary directory where files will be processed.
        """
        self.dataloader = dataloader
        self.temp_path = temp_path

    def process(self, input_data: Union[UploadFile, str], params: Dict[str, Any]) -> DatasetDict:
        """
        Process the input data and return a HuggingFace DatasetDict.

        Parameters
        ----------
        input_data : Union[UploadFile, str]
            File uploaded by the user or a file path.
        params : Dict[str, Any]
            Parameters for the dataloader.

        Returns
        -------
        DatasetDict
            A HuggingFace DatasetDict object.
        """
        try:
            files_path = self.dataloader.extract_files(self.temp_path, input_data)
            dataset = self.dataloader.load_data(files_path, self.temp_path, params)
            return dataset
        except Exception as e:
            logger.error(f"Error processing dataset in DataloaderNode: {e}")
            raise
