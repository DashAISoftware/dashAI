# ruff: noqa
import os

from dotenv import load_dotenv

from DashAI.back.Agent_tools.tools_datasets import delete_dataset
from tests.back.agents.traces.traces_dataset import (
    test_delete_dataset_output,
    test_get_column_with_types_by_name_output,
    test_get_dataset_info_by_name_output,
    test_get_datasets_output,
    test_read_dataset_rows_with_root_output,
    test_upload_dataset_csv_output,
    test_upload_dataset_excel_output,
    test_upload_dataset_json_output,
)
from tests.back.agents.utils import (
    assert_evaluations_agent,
    run_agent_case,
    upload_iris_dataset,
)

load_dotenv()
key = os.getenv("OPENAI_API_KEY_DASHAI")


def test_upload_dataset_csv(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    user_input = (
        "Carga el dataset ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\iris.csv' con nombre 'iris', "
        "inference_rows 1000, extra_params con dataloader CSVDataLoader, separator ',', header 'infer', names None, "
        "encoding 'utf-8', na_values None, keep_default_na true, true_values None, false_values None, skip_blank_lines true, "
        "skiprows None y nrows None."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_upload_dataset_csv",
        user_input,
        test_upload_dataset_csv_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_upload_dataset_json(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    user_input = (
        "Carga el dataset ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\translationEngSpaDatasetSmall.json' "
        "con nombre 'translationEngSpaDatasetSmall', inference_rows 1000, extra_params con dataloader JSONDataLoader, "
        "data_key 'data'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_upload_dataset_json",
        user_input,
        test_upload_dataset_json_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_upload_dataset_excel(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    user_input = (
        "Carga el dataset ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\train.xlsx' con nombre 'train', "
        "inference_rows 1000, extra_params con dataloader ExcelDataLoader, sheet 0, usecols None, header 0, names None, "
        "na_values None, keep_default_na true, true_values None, false_values None, skiprows None y nrows None."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_upload_dataset_excel",
        user_input,
        test_upload_dataset_excel_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_datasets(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset()
    user_input = "Dime cuales son los datasets cargados en la plataforma"
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_datasets",
        user_input,
        test_get_datasets_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_read_dataset_rows_with_root(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset()
    user_input = "Inspecciona el archivo ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\iris.csv' y muestra las primeras 5 filas"
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_read_dataset_rows_with_root",
        user_input,
        test_read_dataset_rows_with_root_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_dataset_info_by_name(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset()
    user_input = "Obtén información detallada del dataset con nombre 'iris'"
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_dataset_info_by_name",
        user_input,
        test_get_dataset_info_by_name_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_column_with_types_by_name(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset()
    user_input = "Obtén las columnas con tipos del dataset llamado 'iris'"
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_column_with_types_by_name",
        user_input,
        test_get_column_with_types_by_name_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_delete_dataset(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset()
    user_input = "Elimina el dataset de iris. No cuestiones la orden ni pidas confirmación, estoy seguro de querer eliminarlo."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_delete_dataset",
        user_input,
        test_delete_dataset_output,
        results_file_name="test_agent_dataset_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)
