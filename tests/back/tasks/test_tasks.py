import os
import pathlib

import PIL
import pytest
from datasets import DatasetDict

from DashAI.back.dataloaders.classes.csv_dataloader import CSVDataLoader
from DashAI.back.dataloaders.classes.dashai_dataset import (
    split_dataset,
    split_indexes,
    to_dashai_dataset,
)
from DashAI.back.dataloaders.classes.json_dataloader import JSONDataLoader
from DashAI.back.tasks.tabular_classification_task import TabularClassificationTask
from DashAI.back.tasks.text_classification_task import TextClassificationTask
from DashAI.back.tasks.text_to_image_generation_task import TextToImageGenerationTask
from DashAI.back.tasks.text_to_text_generation_task import TextToTextGenerationTask
from DashAI.back.tasks.translation_task import TranslationTask


def load_csv_into_datasetdict(file_name):
    test_dataset_path = f"tests/back/tasks/{file_name}"
    csv_dataloader = CSVDataLoader()

    datasetdict = csv_dataloader.load_data(
        filepath_or_buffer=test_dataset_path,
        temp_path="tests/back/tasks",
        params={"separator": ","},
    )
    return datasetdict


def test_validate_tabular_task():
    dataset = to_dashai_dataset(load_csv_into_datasetdict("iris.csv"))

    dataset = dataset.change_columns_type(column_types={"Species": "Categorical"})
    tabular_task = TabularClassificationTask()
    inputs_columns = [
        "SepalLengthCm",
        "SepalWidthCm",
        "PetalLengthCm",
        "PetalWidthCm",
    ]
    outputs_columns = ["Species"]
    try:
        tabular_task.validate_dataset_for_task(
            dataset=dataset,
            dataset_name="Iris",
            input_columns=inputs_columns,
            output_columns=outputs_columns,
        )
    except Exception as e:
        pytest.fail(f"Unexpected error in test_validate_task: {repr(e)}")


def test_wrong_type_task():
    dataset = to_dashai_dataset(load_csv_into_datasetdict("iris_extra_feature.csv"))

    dataset = dataset.change_columns_type(column_types={"Species": "Categorical"})

    tabular_task = TabularClassificationTask()

    inputs_columns = [
        "SepalLengthCm",
        "SepalWidthCm",
        "PetalLengthCm",
        "PetalWidthCm",
    ]
    outputs_columns = ["Species", "StemCm"]
    with pytest.raises(TypeError):
        tabular_task.validate_dataset_for_task(
            dataset=dataset,
            dataset_name="Iris",
            input_columns=inputs_columns,
            output_columns=outputs_columns,
        )


def test_prepare_task():
    dataset = to_dashai_dataset(load_csv_into_datasetdict("iris.csv"))
    tabular_task = TabularClassificationTask()
    inputs_columns = [
        "SepalLengthCm",
        "SepalWidthCm",
        "PetalLengthCm",
        "PetalWidthCm",
    ]
    outputs_columns = ["Species"]
    dataset = tabular_task.prepare_for_task(dataset, outputs_columns)
    try:
        tabular_task.validate_dataset_for_task(
            dataset=dataset,
            dataset_name="Iris",
            input_columns=inputs_columns,
            output_columns=outputs_columns,
        )
    except Exception as e:
        pytest.fail(f"Unexpected error in test_prepare_task: {repr(e)}")


def test_not_prepared_task():
    dataset = to_dashai_dataset(load_csv_into_datasetdict("iris.csv"))
    tabular_task = TabularClassificationTask()
    inputs_columns = [
        "SepalLengthCm",
        "SepalWidthCm",
        "PetalLengthCm",
        "PetalWidthCm",
    ]
    outputs_columns = ["Species"]

    with pytest.raises(TypeError):
        tabular_task.validate_dataset_for_task(
            dataset=dataset,
            dataset_name="Iris",
            input_columns=inputs_columns,
            output_columns=outputs_columns,
        )


def test_get_tabular_class_task_metadata():
    tabular_class_task = TabularClassificationTask()
    metadata = tabular_class_task.get_metadata()

    assert len(metadata.keys()) == 4
    assert metadata["inputs_types"] == ["ClassLabel", "Value"]
    assert metadata["outputs_types"] == ["ClassLabel"]
    assert metadata["inputs_cardinality"] == "n"
    assert metadata["outputs_cardinality"] == 1


@pytest.fixture(scope="module", name="text_classification_dataset")
def text_classification_dataset_fixture():
    test_dataset_path = "tests/back/tasks/ImdbSentimentDatasetSmall.json"
    json_dataloader = JSONDataLoader()

    dataset = json_dataloader.load_data(
        filepath_or_buffer=test_dataset_path,
        temp_path="tests/back/tasks",
        params={"data_key": "data"},
    )

    dashai_dataset = to_dashai_dataset(dataset)

    total_rows = dashai_dataset.num_rows
    train_indexes, test_indexes, val_indexes = split_indexes(
        total_rows=total_rows, train_size=0.7, test_size=0.1, val_size=0.2
    )
    split_datasetdict = split_dataset(
        dashai_dataset,
        train_indexes=train_indexes,
        test_indexes=test_indexes,
        val_indexes=val_indexes,
    )

    return split_datasetdict


def test_validate_text_dataset(text_classification_dataset: DatasetDict):
    text_class_task = TextClassificationTask()
    inputs_columns = ["text"]
    outputs_columns = ["class"]
    imbd_sentiment_dataset = text_class_task.prepare_for_task(
        text_classification_dataset, outputs_columns
    )
    try:
        text_class_task.validate_dataset_for_task(
            dataset=imbd_sentiment_dataset,
            dataset_name="IMDBDataset",
            input_columns=inputs_columns,
            output_columns=outputs_columns,
        )
    except Exception as e:
        pytest.fail(f"Unexpected error in test_validate_task: {repr(e)}")


def test_get_text_class_task_metadata():
    text_class_task = TextClassificationTask()
    metadata = text_class_task.get_metadata()

    assert len(metadata.keys()) == 4
    assert metadata["inputs_types"] == ["Value"]
    assert metadata["outputs_types"] == ["ClassLabel"]
    assert metadata["inputs_cardinality"] == 1
    assert metadata["outputs_cardinality"] == 1


@pytest.fixture(scope="module", name="translation_dataset")
def translation_dataset_fixture():
    test_dataset_path = "tests/back/tasks/translationEngSpaDatasetSmall.json"
    json_dataloader = JSONDataLoader()

    dataset = json_dataloader.load_data(
        filepath_or_buffer=test_dataset_path,
        temp_path="tests/back/tasks",
        params={"data_key": "data"},
    )

    dataset = to_dashai_dataset(dataset)

    total_rows = dataset.num_rows
    train_indexes, test_indexes, val_indexes = split_indexes(
        total_rows=total_rows, train_size=0.7, test_size=0.1, val_size=0.2
    )
    split_datasetdict = split_dataset(
        dataset,
        train_indexes=train_indexes,
        test_indexes=test_indexes,
        val_indexes=val_indexes,
    )
    return split_datasetdict


def test_validate_translation_task(translation_dataset):
    translation_task = TranslationTask()
    inputs_columns = ["text"]
    outputs_columns = ["class"]
    dataset = translation_task.prepare_for_task(translation_dataset, outputs_columns)
    try:
        translation_task.validate_dataset_for_task(
            dataset=dataset,
            dataset_name="EngSpaDataset",
            input_columns=inputs_columns,
            output_columns=outputs_columns,
        )
    except Exception as e:
        pytest.fail(f"Unexpected error in test_validate_task: {repr(e)}")


def test_get_translation_task_metadata():
    translation_task = TranslationTask()
    metadata = translation_task.get_metadata()

    assert len(metadata.keys()) == 4
    assert metadata["inputs_types"] == ["Value", "Sequence"]
    assert metadata["outputs_types"] == ["Value", "Sequence"]
    assert metadata["inputs_cardinality"] == 1
    assert metadata["outputs_cardinality"] == 1


# Generative tasks
@pytest.fixture(scope="module", name="sample_image")
def sample_image_fixture():
    return PIL.Image.new("RGB", (256, 256), color=(255, 255, 255))


@pytest.fixture(scope="module", name="temp_path")
def temp_path_fixture():
    temp_path = pathlib.Path("tests") / "back" / "tasks" / "temp"
    os.makedirs(temp_path, exist_ok=True)
    yield temp_path
    # Cleanup after all tests in the module using this fixture have finished
    for file in os.listdir(temp_path):
        os.remove(os.path.join(temp_path, file))
    os.rmdir(temp_path)


# Text To Text Generation Task
def test_get_text_to_text_task_metadata():
    text_to_text_task = TextToTextGenerationTask()
    metadata = text_to_text_task.get_metadata()

    assert len(metadata.keys()) == 4
    assert metadata["inputs_types"] == ["str"]
    assert metadata["outputs_types"] == ["str"]
    assert metadata["inputs_cardinality"] == 1
    assert metadata["outputs_cardinality"] == 1


def test_prepare_for_task_text_to_text():
    text_to_text_task = TextToTextGenerationTask()
    input_data = ["What is the capital of France?"]
    prepared_input = text_to_text_task.prepare_for_task(input_data)

    assert prepared_input == "Q: What is the capital of France?\nA:"


def test_prepare_for_task_text_to_text_with_history():
    text_to_text_task = TextToTextGenerationTask()
    input_data = ["What is the capital of France?"]
    history = [(["What is the capital of Spain?"], ["Madrid"])]
    prepared_input = text_to_text_task.prepare_for_task(input_data, history=history)

    expected_output = (
        "Q: What is the capital of Spain?\nA: Madrid\n"
        "Q: What is the capital of France?\nA:"
    )
    assert prepared_input == expected_output


def prepare_input_for_database_text_to_text():
    text_to_text_task = TextToTextGenerationTask()
    input_data = ["What is the capital of France?"]
    prepared_input = text_to_text_task.prepare_input_for_database(input_data)

    assert prepared_input == input_data


def process_output_text_to_text():
    text_to_text_task = TextToTextGenerationTask()
    output_data = ["Paris is the capital of France."]
    processed_output = text_to_text_task.process_output(output_data)

    assert processed_output == output_data


def process_input_from_database_text_to_text():
    text_to_text_task = TextToTextGenerationTask()
    input_data = ["What is the capital of France?"]
    processed_input = text_to_text_task.process_input(input_data)

    assert processed_input == input_data


# Text To Image Generation Task
def test_get_text_to_image_task_metadata():
    text_to_image_task = TextToImageGenerationTask()
    metadata = text_to_image_task.get_metadata()

    assert len(metadata.keys()) == 4
    assert metadata["inputs_types"] == ["str"]
    assert metadata["outputs_types"] == ["Image"]
    assert metadata["inputs_cardinality"] == 1
    assert metadata["outputs_cardinality"] == "n"


def test_prepare_for_task_text_to_image():
    text_to_image_task = TextToImageGenerationTask()
    input_data = ["A beautiful landscape"]
    prepared_input = text_to_image_task.prepare_for_task(input_data)

    assert prepared_input == "A beautiful landscape"


def test_input_for_database_text_to_image():
    text_to_image_task = TextToImageGenerationTask()
    input_data = ["A beautiful landscape"]
    prepared_input = text_to_image_task.prepare_input_for_database(input_data)

    assert prepared_input == input_data


def test_process_output_text_to_image(sample_image, temp_path):
    text_to_image_task = TextToImageGenerationTask()
    output_data = [sample_image]
    processed_output = text_to_image_task.process_output(
        output_data, images_path=temp_path
    )

    assert isinstance(processed_output, list)
    assert all(isinstance(img, str) for img in processed_output)
    # Check if the image is saved in the temp path
    assert len(os.listdir(temp_path)) == 1


def test_process_output_from_database_text_to_image():
    text_to_image_task = TextToImageGenerationTask()
    output_data = ["dir/sample_image_0.png", "dir/sample_image_1.png"]
    processed_output = text_to_image_task.process_output_from_database(output_data)

    assert isinstance(processed_output, list)
    assert all(isinstance(img, str) for img in processed_output)
    assert len(processed_output) == 2
    assert processed_output[0] == "sample_image_0.png"
    assert processed_output[1] == "sample_image_1.png"


def test_process_input_from_database_text_to_image():
    text_to_image_task = TextToImageGenerationTask()
    input_data = ["A beautiful landscape"]
    processed_input = text_to_image_task.process_input_from_database(input_data)

    assert processed_input == input_data
