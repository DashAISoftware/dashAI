import os
from pathlib import Path

import numpy as np
import pytest
from datasets import DatasetDict

from DashAI.back.dataloaders.classes.dashai_dataset import (
    select_columns,
    split_dataset,
    split_indexes,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.json_dataloader import JSONDataLoader
from DashAI.back.models import RandomForestClassifier
from DashAI.back.models.model_factory import ModelFactory
from DashAI.back.models.scikit_learn.bow_text_classification_model import (
    BagOfWordsTextClassificationModel,
)


@pytest.fixture(scope="module", name="splited_dataset")
def splited_dataset_fixture():
    test_dataset_path = "tests/back/models/dummy_text.json"
    dataloader_test = JSONDataLoader()

    datasetdict = dataloader_test.load_data(
        filepath_or_buffer=test_dataset_path,
        temp_path="tests/back/models",
        params={"data_key": "data"},
    )

    datasetdict = to_dashai_dataset(datasetdict)

    train_idx, test_idx, val_idx = split_indexes(
        total_rows=datasetdict.num_rows,
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

    return (x, y)


@pytest.fixture(scope="module", name="model_params")
def model_params_fixture() -> dict:
    return {
        "tabular_classifier": {
            "component": "RandomForestClassifier",
            "params": {
                "n_estimators": 1,
                "max_depth": None,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "max_leaf_nodes": None,
                "random_state": None,
            },
        },
        "ngram_min_n": 1,
        "ngram_max_n": 1,
    }


@pytest.fixture(name="sample_model")
def model_fixture(model_params: dict):
    bowtc_model = BagOfWordsTextClassificationModel
    factory = ModelFactory(bowtc_model, model_params)
    return factory.model


def test_model_initialization(sample_model: BagOfWordsTextClassificationModel):
    assert sample_model.classifier is not None
    assert sample_model.vectorizer is not None
    assert isinstance(sample_model, BagOfWordsTextClassificationModel)
    assert isinstance(sample_model.classifier, RandomForestClassifier)
    assert sample_model.vectorizer.ngram_range == (1, 1)


def test_vectorize_text(
    splited_dataset: DatasetDict, sample_model: BagOfWordsTextClassificationModel
):
    x, y = splited_dataset
    x = x["train"]
    input_column = x.column_names[0]
    sample_model.vectorizer.fit(x[input_column])
    vectorizer_func = sample_model.get_vectorizer(input_column)
    vectorized_dataset = x.map(vectorizer_func, remove_columns="text")
    assert len(vectorized_dataset) > 0
    assert "text0" in vectorized_dataset.column_names


def test_fit_model(
    splited_dataset: DatasetDict, sample_model: BagOfWordsTextClassificationModel
):
    x, y = splited_dataset
    x = x["train"]
    y = y["train"]
    sample_model.fit(x, y)

    assert hasattr(sample_model.vectorizer, "vocabulary_")
    assert hasattr(sample_model.classifier, "estimators_")


def test_predict_model(
    splited_dataset: DatasetDict, sample_model: BagOfWordsTextClassificationModel
):
    x, y = splited_dataset
    x = x["test"]
    input_column = x.column_names[0]
    sample_model.vectorizer.fit(x[input_column])
    vectorizer_func = sample_model.get_vectorizer(input_column)
    vectorized_dataset = x.map(vectorizer_func, remove_columns="text")
    vectorized_dataset = to_dashai_dataset(vectorized_dataset)
    sample_model.classifier.fit(vectorized_dataset, y["test"])
    predictions = sample_model.predict(x)
    assert isinstance(predictions, np.ndarray)
    assert len(predictions) == len(y["test"])


def test_save_and_load_model(
    splited_dataset: DatasetDict,
    sample_model: BagOfWordsTextClassificationModel,
    tmp_path: Path,
):
    x, y = splited_dataset
    sample_model.fit(x["train"], y["train"])
    nwft_filename = os.path.join(tmp_path, "nwft_model")
    sample_model.save(nwft_filename)
    loaded_model = sample_model.load(nwft_filename)

    original_predictions = sample_model.predict(x["test"])
    loaded_predictions = loaded_model.predict(x["test"])

    assert np.array_equal(original_predictions, loaded_predictions)

    os.remove(nwft_filename)


def test_get_schema_from_model_class():
    model_schema = BagOfWordsTextClassificationModel.get_schema()

    assert isinstance(model_schema, dict)
    assert "type" in model_schema
    assert model_schema["type"] == "object"
    assert "properties" in model_schema
    assert isinstance(model_schema["properties"], dict)
    assert {"tabular_classifier", "ngram_min_n", "ngram_max_n"} == model_schema[
        "properties"
    ].keys()
    assert model_schema["properties"]["tabular_classifier"]["type"] == "object"
    assert (
        model_schema["properties"]["tabular_classifier"]["parent"]
        == "TabularClassificationModel"
    )
    assert model_schema["properties"]["ngram_min_n"]["type"] == "integer"
    assert model_schema["properties"]["ngram_min_n"]["minimum"] == 1
    assert model_schema["properties"]["ngram_min_n"]["placeholder"] == 1
    assert model_schema["properties"]["ngram_max_n"]["type"] == "integer"
    assert model_schema["properties"]["ngram_max_n"]["minimum"] == 1
    assert model_schema["properties"]["ngram_max_n"]["placeholder"] == 1
    assert "required" in model_schema
    assert set(model_schema["required"]) == {
        "tabular_classifier",
        "ngram_min_n",
        "ngram_max_n",
    }
