"""DashAI Image Dataloader."""

import shutil
from typing import Any, Dict

from beartype import beartype
from datasets import load_dataset
from kink import inject

from DashAI.back.core.schema_fields import none_type, schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader
from DashAI.back.dependencies.registry import ComponentRegistry


class ImageDataloaderSchema(BaseSchema):
    name: schema_field(
        none_type(string_field()),
        "",
        (
            "Custom name to register your dataset. If no name is specified, "
            "the name of the uploaded file will be used."
        ),
    )  # type: ignore


class ImageDataLoader(BaseDataLoader):
    """Data loader for data from image files."""

    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    SCHEMA = ImageDataloaderSchema
    @beartype
    @inject
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        config: Dict[str, Any] = lambda di: di["config"],
    ) -> DashAIDataset:
        """Load an image dataset.

        Parameters
        ----------
        filepath_or_buffer : str
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
        image_save_path = config["DATASETS_PATH"] / params["name"] / "dataset"
        prepared_path = self.prepare_files(filepath_or_buffer, image_save_path)

        if prepared_path[1] == "dir":
            dataset = load_dataset(
                "imagefolder",
                data_dir=prepared_path[0]
            )
        else:
            raise Exception(
                "The image dataloader requires the input file to be a zip file."
            ) from None
        return to_dashai_dataset(dataset)
