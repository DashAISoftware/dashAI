# ruff: noqa
from DashAI.back.Agent_tools.tools_datasets import delete_dataset
from DashAI.back.Agent_tools.tools_explorers import create_correlation_matrix
from DashAI.back.Agent_tools.tools_notebook import upload_notebook
from DashAI.back.pydantic_models.datasets_models import ExplorerColumn
from tests.back.agents.traces.traces_explorers import (
    build_test_create_box_plot_output,
    build_test_create_correlation_matrix_output,
    build_test_create_covariance_matrix_output,
    build_test_create_density_heatmap_output,
    build_test_create_describe_dataset_output,
    build_test_create_ecdf_plot_output,
    build_test_create_histogram_output,
    build_test_create_multi_column_box_plot_output,
    build_test_create_parallel_categories_output,
    build_test_create_parallel_coordinates_output,
    build_test_create_row_explorer_output,
    build_test_create_scatter_matrix_output,
    build_test_create_scatter_plot_output,
    build_test_create_wordcloud_output,
    build_test_delete_explorer_by_id_output,
    build_test_get_explorer_results_by_explorer_id_output,
    build_test_get_explorers_output,
)
from tests.back.agents.utils import (
    assert_evaluations_agent,
    run_agent_case,
    upload_iris_dataset,
)


def test_get_explorers(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset("iris_explorers_get")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_get_explorers",
            "description": "Notebook de prueba",
        }
    )

    reference_outputs = build_test_get_explorers_output()
    user_input = "Muestra los exploradores disponibles en DashAI."
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_explorers",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_delete_explorer_by_id(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_delete")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_delete_explorer",
            "description": "Notebook de prueba",
        }
    )
    columns_tool = [
        ExplorerColumn(
            columnName="sepal_length",
            valueType="Float",
            dataType="float64",
            id=1,
            order=1,
        ),
        ExplorerColumn(
            columnName="sepal_width",
            valueType="Float",
            dataType="float64",
            id=2,
            order=2,
        ),
    ]
    explorer_result = create_correlation_matrix.invoke(
        {
            "notebook_id": 1,
            "columns": columns_tool,
            "method": "pearson",
            "min_periods": 1,
            "numeric_only": True,
            "plot": False,
            "name": "Explorador de prueba",
        }
    )
    explorer_id = explorer_result["explorer"]["id"]
    user_input = "Elimina el explorer del notebook iris."
    reference_outputs = build_test_delete_explorer_by_id_output(explorer_id)
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_delete_explorer_by_id",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_get_explorer_results_by_explorer_id(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_results")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_results_explorer",
            "description": "Notebook de prueba",
        }
    )
    columns_tool = [
        ExplorerColumn(
            columnName="sepal_length",
            valueType="Float",
            dataType="float64",
            id=1,
            order=1,
        ),
        ExplorerColumn(
            columnName="sepal_width",
            valueType="Float",
            dataType="float64",
            id=2,
            order=2,
        ),
    ]
    explorer_result = create_correlation_matrix.invoke(
        {
            "notebook_id": 1,
            "columns": columns_tool,
            "method": "pearson",
            "min_periods": 1,
            "numeric_only": True,
            "plot": False,
            "name": "Explorador de prueba",
        }
    )
    user_input = "Obtén los resultados de la matriz de correlación del notebook iris.  Si no es posible obtenerlos dado que es plotly_json, está bien."
    reference_outputs = build_test_get_explorer_results_by_explorer_id_output(1)
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_get_explorer_results_by_explorer_id",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_correlation_matrix(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_corr")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_correlation_matrix",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_correlation_matrix_output(
        1, columns_payload, "pearson", 1, True, False, "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer de matriz de correlación en el notebook usando la herramienta create_correlation_matrix con columnas sepal_length y sepal_width, method pearson, "
        "min_periods 1, numeric_only true, plot false y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_correlation_matrix",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_covariance_matrix(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_cov")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_covariance_matrix",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_covariance_matrix_output(
        1, columns_payload, 1, 1, True, False, "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer de matriz de covarianza en el notebook usando la herramienta create_covariance_matrix con columnas sepal_length y sepal_width, min_periods 1, "
        "delta_degree_of_freedom 1, numeric_only true, plot false y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_covariance_matrix",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_multi_column_box_plot(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_box")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_multi_column_box_plot",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_multi_column_box_plot_output(
        1, columns_payload, False, "outliers", None, "Explorador de prueba"
    )
    user_input = (
        "Crea un box plot multicolumna en el notebook usando la herramienta create_multi_column_box_plot con columnas sepal_length y sepal_width, horizontal false, "
        "points outliers, opposite_axis None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_multi_column_box_plot",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_parallel_categories(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_parallel_cat")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_parallel_categories",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "species",
            "valueType": "String",
            "dataType": "object",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_parallel_categories_output(
        1, columns_payload, None, "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer de categorías paralelas en el notebook usando la herramienta create_parallel_categories con columnas species y sepal_length, color_column None y "
        "nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_parallel_categories",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_parallel_coordinates(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_parallel_coord")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_parallel_coordinates",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_parallel_coordinates_output(
        1, columns_payload, None, "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer de coordenadas paralelas en el notebook usando la herramienta create_parallel_coordinates con columnas sepal_length y sepal_width, color_column None "
        "y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_parallel_coordinates",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_box_plot(agent, llm_judge, tool_calling_evaluator, tool_args_evaluator):
    upload_iris_dataset("iris_explorers_box_plot")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_box_plot",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        }
    ]
    reference_outputs = build_test_create_box_plot_output(
        1, columns_payload, False, "outliers", "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer de box plot en el notebook usando la herramienta create_box_plot con columna sepal_length, horizontal false, "
        "points outliers y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_box_plot",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_ecdf_plot(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_ecdf")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_ecdf_plot",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        }
    ]
    reference_outputs = build_test_create_ecdf_plot_output(
        1, columns_payload, None, None, None, "probability", "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer ECDF en el notebook usando la herramienta create_ecdf_plot con columna sepal_length, color_column None, facet_col None, "
        "facet_row None, ecdf_norm probability y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_ecdf_plot",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_histogram(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_histogram")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_histogram",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        }
    ]
    reference_outputs = build_test_create_histogram_output(
        1, columns_payload, None, "count", "", None, None, "Explorador de prueba"
    )
    user_input = (
        "Crea un histograma en el notebook usando la herramienta create_histogram con columna sepal_length, nbins None, histfunc count, "
        "histnorm '' , color_group None, pattern_group None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_histogram",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_wordcloud(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_wordcloud")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_wordcloud",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "species",
            "valueType": "String",
            "dataType": "object",
            "id": 1,
            "order": 1,
        }
    ]
    reference_outputs = build_test_create_wordcloud_output(
        1, columns_payload, 200, None, "Explorador de prueba"
    )
    user_input = (
        "Crea una nube de palabras en el notebook usando la herramienta create_wordcloud con columna species, max_words 200, "
        "background_color None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_wordcloud",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_scatter_plot(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_scatter_plot")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_scatter_plot",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_scatter_plot_output(
        1, columns_payload, None, None, None, "Explorador de prueba"
    )
    user_input = (
        "Crea un gráfico de dispersión en el notebook usando la herramienta create_scatter_plot con columnas sepal_length y sepal_width, "
        "color_group None, simbol_group None, point_size None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_scatter_plot",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_density_heatmap(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_density_heatmap")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_density_heatmap",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_density_heatmap_output(
        1, columns_payload, None, None, "Explorador de prueba"
    )
    user_input = (
        "Crea un mapa de calor de densidad en el notebook usando la herramienta create_density_heatmap con columnas sepal_length y sepal_width, "
        "nbinsx None, nbinsy None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_density_heatmap",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_scatter_matrix(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_scatter_matrix")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_scatter_matrix",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_scatter_matrix_output(
        1, columns_payload, None, None, "Explorador de prueba"
    )
    user_input = (
        "Crea una matriz de dispersión en el notebook usando la herramienta create_scatter_matrix con columnas sepal_length y sepal_width, "
        "color_group None, simbol_group None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_scatter_matrix",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_describe_dataset(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_describe")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_describe_dataset",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        },
        {
            "columnName": "sepal_width",
            "valueType": "Float",
            "dataType": "float64",
            "id": 2,
            "order": 2,
        },
    ]
    reference_outputs = build_test_create_describe_dataset_output(
        1, columns_payload, "25, 50, 75", "all", None, "Explorador de prueba"
    )
    user_input = (
        "Crea un explorer descriptivo del dataset en el notebook usando la herramienta create_describe_dataset con columnas "
        "sepal_length y sepal_width, percentiles '25, 50, 75', include 'all', exclude None y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_describe_dataset",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)


def test_create_row_explorer(
    agent, llm_judge, tool_calling_evaluator, tool_args_evaluator
):
    upload_iris_dataset("iris_explorers_row")
    upload_notebook.invoke(
        {
            "dataset_id": 1,
            "name": "notebook_create_row_explorer",
            "description": "Notebook de prueba",
        }
    )
    columns_payload = [
        {
            "columnName": "sepal_length",
            "valueType": "Float",
            "dataType": "float64",
            "id": 1,
            "order": 1,
        }
    ]
    reference_outputs = build_test_create_row_explorer_output(
        1, columns_payload, 50, False, True, "Explorador de prueba"
    )
    user_input = (
        "Crea un explorador de filas en el notebook usando la herramienta create_row_explorer con columna sepal_length, row_ammount 50, "
        "shuffle false, from_top true y nombre 'Explorador de prueba'."
    )
    results = run_agent_case(
        agent,
        llm_judge,
        tool_calling_evaluator,
        tool_args_evaluator,
        "test_create_row_explorer",
        user_input,
        reference_outputs,
        results_file_name="test_agent_explorers_results.json",
    )
    delete_dataset.invoke({"dataset_id": 1})
    assert_evaluations_agent(results)
