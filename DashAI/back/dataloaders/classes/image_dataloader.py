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

        # Convert ClassLabel columns (integers) back to their string names.
        # HF ClassLabel silently casts map() outputs back to int, so we need
        # to build a new dataset with the strings directly.
        from datasets import ClassLabel as HFClassLabel
        from datasets import Features, Value

        if isinstance(dataset, Dataset):
            ds_ref = dataset
        else:
            first_key = list(dataset.keys())[0]
            ds_ref = dataset[first_key]

        classlabel_cols = {}
        for col in ds_ref.column_names:
            feat = ds_ref.features.get(col)
            if isinstance(feat, HFClassLabel):
                classlabel_cols[col] = feat.names

        if classlabel_cols:
            new_features = Features(
                {
                    col: Value("string") if col in classlabel_cols else feat
                    for col, feat in ds_ref.features.items()
                }
            )

            def convert_labels(example):
                for col, names in classlabel_cols.items():
                    example[col] = names[example[col]]
                return example

            if isinstance(dataset, Dataset):
                dataset = dataset.map(convert_labels, features=new_features)
            else:
                for split_name in list(dataset.keys()):
                    dataset[split_name] = dataset[split_name].map(
                        convert_labels, features=new_features
                    )
                ds_ref = dataset[first_key]

        shutil.rmtree(prepared_path[0])

        from DashAI.back.types.categorical import Categorical
        from DashAI.back.types.dashai_image import DashAIImage

        ds_for_types = dataset if isinstance(dataset, Dataset) else ds_ref

        types = {}
        for col in ds_for_types.column_names:
            if col == "image":
                types[col] = DashAIImage()
            else:
                unique_vals = sorted(
                    {str(v) for v in ds_for_types[col] if v is not None}
                )
                types[col] = Categorical(values=unique_vals, dtype="string")

        return to_dashai_dataset(dataset, types=types)
