import os

import pytest
import torch

from DashAI.back.dataloaders.classes.dashai_dataset import (
    select_columns,
    split_dataset,
    split_indexes,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.json_dataloader import JSONDataLoader
from DashAI.back.models import OpusMtEnESTransformer


@pytest.fixture(scope="module", name="translation_dataset")
def translation_dataset_fixture():
    test_dataset_path = "tests/back/models/translationEngSpaDatasetSmall.json"
    dataloader_test = JSONDataLoader()

    datasetdict = dataloader_test.load_data(
        filepath_or_buffer=test_dataset_path,
        temp_path="tests/back/models",
        params={"data_key": "data"},
    )

    datasetdict = to_dashai_dataset(datasetdict)

    train_idx, test_idx, val_idx = split_indexes(
        total_rows=len(datasetdict),
        train_size=0.6,
        test_size=0.2,
        val_size=0.2,
    )

    splited_dataset = split_dataset(
        datasetdict,
        train_indexes=train_idx,
        test_indexes=test_idx,
        val_indexes=val_idx,
    )

    x, y = select_columns(
        splited_dataset,
        ["text"],
        ["class"],
    )
    x = split_dataset(x)
    y = split_dataset(y)

    return (x["train"], y["train"])


@pytest.fixture()
def sample_model() -> OpusMtEnESTransformer:
    model = OpusMtEnESTransformer(
        num_train_epochs=1,
        batch_size=4,
        learning_rate=2e-5,
        device="gpu",
        weight_decay=0.01,
    )
    return model


@pytest.fixture(autouse=True)
def _clear_cuda_cache():
    yield
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def test_model_initialization(sample_model):
    assert sample_model.model is not None
    assert sample_model.tokenizer is not None
    assert sample_model.model_name == "Helsinki-NLP/opus-mt-en-es"
    assert sample_model.fitted is False


def test_tokenize_data(sample_model, translation_dataset):
    x_train, y_train = translation_dataset
    tokenized_dataset = sample_model.tokenize_data(x_train, y_train)

    assert "input_ids" in tokenized_dataset.features
    assert "attention_mask" in tokenized_dataset.features
    assert "labels" in tokenized_dataset.features
    assert len(tokenized_dataset) == len(x_train)


def test_fit(sample_model, translation_dataset):
    x_train, y_train = translation_dataset
    sample_model.fit(x_train, y_train)
    assert sample_model.fitted is True


def test_predict(sample_model, translation_dataset):
    x_train, y_train = translation_dataset

    sample_model.fit(x_train, y_train)
    translations = sample_model.predict(x_train)

    assert isinstance(translations, list)
    assert len(translations) == len(x_train)
    assert all(isinstance(translation, str) for translation in translations)


def test_save_and_load(sample_model, translation_dataset, tmp_path):
    x_train, y_train = translation_dataset
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    sample_model.fit(x_train, y_train)

    save_path = os.path.join(tmp_path, "opus_mt_model")
    sample_model.save(save_path)

    loaded_model = OpusMtEnESTransformer.load(save_path)
    assert loaded_model.fitted, "Model should be fitted after loading"

    sample_model.model.to(device)
    loaded_model.model.to(device)
    for param_original, param_loaded in zip(
        sample_model.model.parameters(), loaded_model.model.parameters()
    ):
        assert torch.equal(
            param_original, param_loaded
        ), """The loaded model should have the same weights
            and parameters as the original model"""
