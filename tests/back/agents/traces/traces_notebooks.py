# ruff: noqa
def build_test_upload_notebook_output(
    dataset_id: int, notebook_name: str, description: str
):
    return [
        {
            "role": "user",
            "content": (
                f"Crea un notebook asociado al dataset con id {dataset_id} con nombre '{notebook_name}' "
                f"y descripción '{description}'. Usa la herramienta upload_notebook."
            ),
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "upload_notebook",
                        "arguments": {
                            "dataset_id": dataset_id,
                            "name": notebook_name,
                            "description": description,
                        },
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_delete_notebook_output(notebook_id: int):
    return [
        {
            "role": "user",
            "content": (
                f"Elimina el notebook con id {notebook_id} usando la herramienta delete_notebook. "
                "No cuestiones ni pidas confirmación, estoy seguro de querer eliminarlo."
            ),
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "delete_notebook",
                        "arguments": {"notebook_id": notebook_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_notebooks_output():
    return [
        {
            "role": "user",
            "content": "Muestra todos los notebooks creados en DashAI usando la herramienta get_notebooks.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "get_notebooks", "arguments": {}}}],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_notebook_explorer_list_by_notebook_id_output(notebook_id: int):
    return [
        {
            "role": "user",
            "content": (
                f"Obtén la lista de exploradores del notebook con id {notebook_id} usando la herramienta "
                "get_notebook_explorer_list_by_notebook_id."
            ),
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_notebook_explorer_list_by_notebook_id",
                        "arguments": {"notebook_id": notebook_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_rows_dataset_by_notebook_id_output(notebook_id: int):
    return [
        {
            "role": "user",
            "content": (
                f"Obtén las filas del dataset asociado al notebook con id {notebook_id} desde la fila 0 hasta la 5 "
                "usando la herramienta get_rows_dataset_by_notebook_id."
            ),
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_rows_dataset_by_notebook_id",
                        "arguments": {
                            "notebook_id": notebook_id,
                            "start_row": 0,
                            "end_row": 5,
                        },
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_notebook_converters_list_by_notebook_id_output(notebook_id: int):
    return [
        {
            "role": "user",
            "content": (
                f"Obtén la lista de conversores del notebook con id {notebook_id} usando la herramienta "
                "get_notebook_converters_list_by_notebook_id."
            ),
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_notebook_converters_list_by_notebook_id",
                        "arguments": {"notebook_id": notebook_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]
