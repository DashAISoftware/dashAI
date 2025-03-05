"""DashAI Audio Dataloader."""

import shutil
from typing import Any, Dict

from beartype import beartype
from datasets import Audio, load_dataset

from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader


class AudioDataLoader(BaseDataLoader):
    """Data loader for data from audio files."""

    @beartype
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
    ) -> DashAIDataset:
        """Load and audio dataset into a DatasetDict.

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
        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)
        if prepared_path[1] == "dir":
            dataset = load_dataset(
                "audiofolder",
                data_dir=prepared_path[0],
            ).cast_column(
                "audio",
                Audio(decode=False),
            )
            shutil.rmtree(prepared_path[0])
        else:
            raise Exception(
                "The audio dataloader requires the input file to be a zip file. "
            )
        return to_dashai_dataset(dataset)
