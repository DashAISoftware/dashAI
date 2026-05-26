"""Tests for the MLP Image Classifier and Image Classification pipeline."""

import os
import shutil
import tempfile
import zipfile

import numpy as np
import pytest
from PIL import Image

from DashAI.back.dataloaders.classes.image_dataloader import ImageDataLoader
from DashAI.back.models.mlp_image_classifier import MLPImageClassifier


@pytest.fixture(scope="module")
def image_zip_path():
    """Create a temporary zip with synthetic images in imagefolder format.

    Structure:
        class_0/img_0.png, img_1.png, ...
        class_1/img_0.png, img_1.png, ...
    """
    tmp_dir = tempfile.mkdtemp()
    img_dir = os.path.join(tmp_dir, "images")

    num_classes = 3
    images_per_class = 10

    for cls in range(num_classes):
        cls_dir = os.path.join(img_dir, f"class_{cls}")
        os.makedirs(cls_dir)
        for i in range(images_per_class):
            arr = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
            img = Image.fromarray(arr)
            img.save(os.path.join(cls_dir, f"img_{i}.png"))

    zip_path = os.path.join(tmp_dir, "test_images.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(img_dir):
            for f in files:
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, img_dir)
                zf.write(full, arcname)

    yield zip_path

    shutil.rmtree(tmp_dir)


@pytest.fixture(scope="module")
def loaded_dataset(image_zip_path):
    """Load the synthetic image dataset using ImageDataLoader."""
    loader = ImageDataLoader()
    temp_path = tempfile.mkdtemp()
    try:
        dataset = loader.load_data(
            filepath_or_buffer=image_zip_path,
            temp_path=temp_path,
            params={},
        )
        return dataset
    finally:
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)


def test_image_dataloader_loads_correctly(loaded_dataset):
    assert loaded_dataset is not None
    assert len(loaded_dataset) == 30  # 3 classes * 10 images
    assert "image" in loaded_dataset.features
    assert "label" in loaded_dataset.features


def test_mlp_image_classifier_train_and_predict(loaded_dataset):
    from DashAI.back.dataloaders.classes.dashai_dataset import (
        select_columns,
        split_dataset,
        split_indexes,
    )

    total_rows = loaded_dataset.num_rows
    train_idx, test_idx, val_idx = split_indexes(
        total_rows=total_rows,
        train_size=0.7,
        test_size=0.15,
        val_size=0.15,
    )
    split_ds = split_dataset(
        loaded_dataset,
        train_indexes=train_idx,
        test_indexes=test_idx,
        val_indexes=val_idx,
    )

    x, y = select_columns(split_ds, ["image"], ["label"])
    x = split_dataset(x)
    y = split_dataset(y)

    model = MLPImageClassifier(epochs=2, learning_rate=0.01, hidden_dims=[32])
    model.train(x["train"], y["train"])

    predictions = model.predict(x["test"])
    assert isinstance(predictions, np.ndarray)
    assert len(predictions) == x["test"].num_rows
    assert predictions.shape[1] == 3  # 3 classes


def test_mlp_image_classifier_save_and_load(loaded_dataset):
    from DashAI.back.dataloaders.classes.dashai_dataset import (
        select_columns,
        split_dataset,
        split_indexes,
    )

    total_rows = loaded_dataset.num_rows
    train_idx, test_idx, val_idx = split_indexes(
        total_rows=total_rows,
        train_size=0.7,
        test_size=0.15,
        val_size=0.15,
    )
    split_ds = split_dataset(
        loaded_dataset,
        train_indexes=train_idx,
        test_indexes=test_idx,
        val_indexes=val_idx,
    )

    x, y = select_columns(split_ds, ["image"], ["label"])
    x = split_dataset(x)
    y = split_dataset(y)

    model = MLPImageClassifier(epochs=1, learning_rate=0.01, hidden_dims=[32])
    model.train(x["train"], y["train"])

    with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
        save_path = f.name

    try:
        model.save(save_path)
        loaded_model = MLPImageClassifier.load(save_path)

        original_preds = model.predict(x["test"])
        loaded_preds = loaded_model.predict(x["test"])

        np.testing.assert_array_almost_equal(original_preds, loaded_preds, decimal=5)
    finally:
        os.remove(save_path)
