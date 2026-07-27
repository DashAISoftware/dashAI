# ruff: noqa
from DashAI.back.Agent_tools.tools_datasets import delete_dataset
from DashAI.back.Agent_tools.tools_notebook import upload_notebook
from tests.back.agents.traces.traces_notebooks import (
    build_test_delete_notebook_output,
    build_test_get_notebook_converters_list_by_notebook_id_output,
    build_test_get_notebook_explorer_list_by_notebook_id_output,
    build_test_get_notebooks_output,
    build_test_get_rows_dataset_by_notebook_id_output,
    build_test_upload_notebook_output,
)
from tests.back.agents.utils import (
    assert_evaluations_agent,
    run_agent_case,
    upload_iris_dataset,
)


def test_upload_notebook(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset()
    user_input = "Crea un notebook asociado al dataset iris con nombre 'test_notebook' y descripción 'Notebook de prueba'."
    reference_outputs = build_test_upload_notebook_output(
        1, "test_notebook", "Notebook de prueba"
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_upload_notebook",
        user_input,
        reference_outputs,
        results_file_name="test_agent_notebooks_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_delete_notebook(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset()
    upload_notebook.invoke(
        {"dataset_id": 1, "name": "test_notebook", "description": "Notebook de prueba"}
    )
    user_input = "Elimina el notebook del dataset iris. No cuestiones ni pidas confirmación, estoy seguro de querer eliminarlo."
    reference_outputs = build_test_delete_notebook_output(1)
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_delete_notebook",
        user_input,
        reference_outputs,
        results_file_name="test_agent_notebooks_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_notebooks(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset()
    upload_notebook.invoke(
        {"dataset_id": 1, "name": "test_notebook", "description": "Notebook de prueba"}
    )
    user_input = "Muestra todos los notebooks creados en DashAI"
    reference_outputs = build_test_get_notebooks_output()
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_notebooks",
        user_input,
        reference_outputs,
        results_file_name="test_agent_notebooks_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_notebook_explorer_list_by_notebook_id(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset()
    upload_notebook.invoke(
        {"dataset_id": 1, "name": "test_notebook", "description": "Notebook de prueba"}
    )
    user_input = "Obtén la lista de exploradores del notebook iris"
    reference_outputs = build_test_get_notebook_explorer_list_by_notebook_id_output(1)
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_notebook_explorer_list_by_notebook_id",
        user_input,
        reference_outputs,
        results_file_name="test_agent_notebooks_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_rows_dataset_by_notebook_id(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset()
    upload_notebook.invoke(
        {"dataset_id": 1, "name": "test_notebook", "description": "Notebook de prueba"}
    )
    user_input = "Obtén las filas del dataset asociado al notebook iris desde la fila 0 hasta la 5."
    reference_outputs = build_test_get_rows_dataset_by_notebook_id_output(1)
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_rows_dataset_by_notebook_id",
        user_input,
        reference_outputs,
        results_file_name="test_agent_notebooks_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_notebook_converters_list_by_notebook_id(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset()
    upload_notebook.invoke(
        {"dataset_id": 1, "name": "test_notebook", "description": "Notebook de prueba"}
    )
    user_input = "Obtén la lista de conversores del notebook iris."
    reference_outputs = build_test_get_notebook_converters_list_by_notebook_id_output(1)
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_notebook_converters_list_by_notebook_id",
        user_input,
        reference_outputs,
        results_file_name="test_agent_notebooks_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)
