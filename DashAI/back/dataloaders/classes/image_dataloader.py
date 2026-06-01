"""DashAI Image Dataloader."""

import shutil
from typing import Any, Dict

from beartype import beartype
from datasets import Dataset

from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.dataloader import BaseDataLoader


class ImageDataLoaderSchema(BaseSchema):
    pass


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".tiff",
    ".webp",
}


def _find_imagefolder_root(base_path: str) -> str:
    """Descend into single-child directories until we find the level
    that contains the class subdirectories."""
    import os

    while True:
        entries = [
            e
            for e in os.listdir(base_path)
            if not e.startswith(".") and e != "__MACOSX"
        ]
        if len(entries) == 1 and os.path.isdir(os.path.join(base_path, entries[0])):
            base_path = os.path.join(base_path, entries[0])
        else:
            break
    return base_path


def _load_images_from_directory(data_dir: str, n_sample=None):
    """Walk the directory structure and build a list of dicts with
    'image' (bytes+format) and 'label' (parent folder name) entries.

    This replaces HF's imagefolder loader to guarantee label detection.
    """
    import io
    import os

    from PIL import Image as PILImage

    records = []
    entries = [
        e
        for e in sorted(os.listdir(data_dir))
        if not e.startswith(".") and e != "__MACOSX"
    ]

    for class_name in entries:
        class_path = os.path.join(data_dir, class_name)
        if not os.path.isdir(class_path):
            continue
        for root, _dirs, files in os.walk(class_path):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue
                fpath = os.path.join(root, fname)
                try:
                    img = PILImage.open(fpath)
                    img.load()
                    if img.mode in ("CMYK", "YCbCr", "LAB", "HSV"):
                        img = img.convert("RGB")
                    elif img.mode in ("LA", "PA"):
                        img = img.convert("RGBA")
                    buf = io.BytesIO()
                    fmt = img.format or "PNG"
                    img.save(buf, format=fmt)
                    records.append(
                        {
                            "image": {
                                "bytes": buf.getvalue(),
                                "path": fname,
                            },
                            "label": class_name,
                        }
                    )
                except Exception:
                    continue
                if n_sample and len(records) >= n_sample:
                    return records
    return records


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
        de=(
            "Datenlader für Bilddatensätze. Laden Sie eine ZIP-Datei hoch, die "
            "Bilder in Unterverzeichnissen nach Klassenbezeichnung "
            "organisiert enthält (imagefolder-Format)."
        ),
        zh=(
            "图像数据集加载器。上传一个ZIP文件，其中图像按类别标签组织在子目录中"
            "（imagefolder格式）。"
        ),
    )
    DISPLAY_NAME: str = MultilingualString(
        en="Image Data Loader",
        es="Cargador de Datos de Imágenes",
        de="Bild Datenlader",
        zh="图像数据加载器",
    )

    @beartype
    def load_data(
        self,
        filepath_or_buffer: str,
        temp_path: str,
        params: Dict[str, Any],  # noqa: ARG002
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
        import logging
        import os

        log = logging.getLogger(__name__)

        prepared_path = self.prepare_files(filepath_or_buffer, temp_path)

        if prepared_path[1] != "dir":
            raise ValueError(
                "The image dataloader requires the input file to be a zip file."
            )

        data_dir = _find_imagefolder_root(prepared_path[0])
        log.debug("Resolved data_dir: %s", data_dir)
        log.debug(
            "data_dir contents: %s",
            [e for e in os.listdir(data_dir) if not e.startswith(".")],
        )

        records = _load_images_from_directory(data_dir, n_sample)
        log.debug("Loaded %d images from directory", len(records))

        if not records:
            raise ValueError("No images found in the uploaded zip file.")

        dataset = Dataset.from_list(records)
        log.debug("Dataset columns: %s", dataset.column_names)

        shutil.rmtree(prepared_path[0])

        from DashAI.back.types.categorical import Categorical
        from DashAI.back.types.dashai_image import DashAIImage

        types = {}
        for col in dataset.column_names:
            if col == "image":
                types[col] = DashAIImage()
            else:
                unique_vals = sorted({str(v) for v in dataset[col] if v is not None})
                types[col] = Categorical(values=unique_vals, dtype="string")

        return to_dashai_dataset(dataset, types=types)
