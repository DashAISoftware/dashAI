# ruff: noqa
from typing import Any


def build_test_get_sessions_output():
    return [
        {
            "role": "user",
            "content": "Muestra las sesiones de modelos disponibles en DashAI",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "get_sessions", "arguments": {}}}],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_session_parameters_output(model_session_id: int):
    return [
        {
            "role": "user",
            "content": f"Obtén los parámetros de la sesión de modelo con id {model_session_id}",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_session_parameters",
                        "arguments": {"model_session_id": model_session_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_delete_session_output(model_session_id: int):
    return [
        {
            "role": "user",
            "content": f"Elimina la sesión de modelo con id {model_session_id} usando la herramienta delete_session.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "delete_session",
                        "arguments": {"model_session_id": model_session_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_models_execution_metrics_output(model_session_id: int):
    return [
        {
            "role": "user",
            "content": f"Obtén las métricas de ejecución de los modelos de la sesión con id {model_session_id} usando la herramienta get_models_execution_metrics.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_models_execution_metrics",
                        "arguments": {"model_session_id": model_session_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_session_output(
    dataset_id: int,
    task_name: str,
    name: str,
    input_columns: list[str],
    output_columns: list[str],
    splits: dict[str, Any],
):
    return [
        {
            "role": "user",
            "content": f"Crea una sesión de modelo para el dataset con id {dataset_id} usando la herramienta create_session.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_session",
                        "arguments": {
                            "dataset_id": dataset_id,
                            "task_name": task_name,
                            "name": name,
                            "input_columns": input_columns,
                            "output_columns": output_columns,
                            "splits": splits,
                        },
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_add_model_to_session_output(
    model_session_id: int,
    model_name: str,
    run_name: str,
    parameters: dict[str, Any],
    optimizer_name: str,
    optimizer_parameters: dict[str, Any] | None,
    goal_metric: str,
    description: str,
):
    return [
        {
            "role": "user",
            "content": f"Agrega un modelo {model_name} a la sesión de modelo con id {model_session_id}.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "add_model_to_session",
                        "arguments": {
                            "model_session_id": model_session_id,
                            "model_name": model_name,
                            "run_name": run_name,
                            "parameters": parameters,
                            "optimizer_name": optimizer_name,
                            "optimizer_parameters": optimizer_parameters,
                            "goal_metric": goal_metric,
                            "description": description,
                        },
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_delete_model_from_session_output(run_id: int):
    return [
        {
            "role": "user",
            "content": f"Elimina el modelo con run_id {run_id} de la sesión.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "delete_model_from_session",
                        "arguments": {"run_id": run_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_run_model_output(run_id: int):
    return [
        {"role": "user", "content": f"Ejecuta el modelo con run_id {run_id}."},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "run_model", "arguments": {"run_id": run_id}}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]
