"""Dataloaders tests."""

import shutil

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dataloaders.classes.image_dataloader import ImageDataLoader


def test_image_dataloader_from_zip():
    try:
        test_dataset_path = "tests/back/dataloaders/beans_dataset_small.zip"
        image_dataloader = ImageDataLoader()

        dataset = image_dataloader.load_data(
            filepath_or_buffer=test_dataset_path,
            temp_path="tests/back/dataloaders/beans_dataset_small",
            params={},
        )

        assert isinstance(dataset, DashAIDataset)
    finally:
        shutil.rmtree("tests/back/dataloaders/beans_dataset_small", ignore_errors=True)
