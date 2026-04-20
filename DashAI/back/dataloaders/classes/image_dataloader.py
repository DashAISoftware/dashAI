"""DashAI Image Dataloader."""

import shutil
from typing import Any, Dict

from beartype import beartype
from datasets import Dataset, IterableDatasetDict, load_dataset

from DashAI.back.core.schema_fields import none_type, schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader


class ImageDataLoaderSchema(BaseSchema):
    name: schema_field(
        none_type(string_field()),
        "",
        (
            "Custom name to register your dataset. If no name is specified, "
            "the name of the uploaded file will be used."
        ),
    )  # type: ignore


class ImageDataLoader(BaseDataLoader):
    """Data loader for image datasets.

    Expects a zip file containing images organized in subdirectories by class
    label (imagefolder format).
    """

    COMPATIBLE_COMPONENTS = ["ImageClassificationTask"]
    SCHEMA = ImageDataLoaderSchema

    DESCRIPTION: str = MultilingualString(
        en=(
            "Data loader for image datasets. Upload a ZIP file containing "
            "images organized in subdirectories by class label "
            "(imagefolder format)."
        ),
        es=(
            "Cargador de datos para datasets de imágenes. Suba un archivo "
            "ZIP con imágenes organizadas en subdirectorios por etiqueta "
            "de clase (formato imagefolder)."
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Image Data Loader",
        es="Cargador de Datos de Imágenes",
    )

    @beartype
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],
        n_sample: int | None = None,
    ) -> DashAIDataset:
        """Load an image dataset.

        Parameters
        ----------
        filepath_or_buffer : str
            An URL where the dataset is located or a FastAPI/Uvicorn uploaded
            file object.
        temp_path : str
            The temporary path where the files will be extracted and then
            uploaded.
        params : Dict[str, Any]
            Dict with the dataloader parameters.
        n_sample : int | None
            Indicates how many rows to load from the dataset, all rows if None.

        Returns
        -------
        DashAIDataset
            A DashAI Dataset with the loaded image data.
        """
        import io

        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)

        if prepared_path[1] != "dir":
            raise ValueError(
                "The image dataloader requires the input file to be a zip file."
            )

        dataset = load_dataset(
            "imagefolder",
            data_dir=prepared_path[0],
            streaming=bool(n_sample),
            cache_dir=temp_path,
        )

        if n_sample:
            if isinstance(dataset, IterableDatasetDict):
                dataset = dataset["train"]
            dataset = Dataset.from_list(list(dataset.take(n_sample)))

        def convert_image_to_bytes(example):
            buffer = io.BytesIO()
            img_format = example["image"].format or "PNG"
            example["image"].save(buffer, format=img_format)
            return {"image": {"bytes": buffer.getvalue(), "format": img_format}}

        dataset = dataset.map(convert_image_to_bytes)

        shutil.rmtree(prepared_path[0])

        from DashAI.back.types.categorical import Categorical
        from DashAI.back.types.dashai_image import DashAIImage

        if isinstance(dataset, Dataset):
            ds_for_types = dataset
        else:
            first_key = list(dataset.keys())[0]
            ds_for_types = dataset[first_key]

        types = {}
        for col in ds_for_types.column_names:
            if col == "image":
                types[col] = DashAIImage()
            else:
                unique_vals = sorted({v for v in ds_for_types[col] if v is not None})
                types[col] = Categorical(values=unique_vals, dtype="string")

        return to_dashai_dataset(dataset, types=types)
