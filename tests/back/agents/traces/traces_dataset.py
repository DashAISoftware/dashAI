# ruff: noqa
test_get_datasets_output = [
    {
        "role": "user",
        "content": "Dime cuales son los datasets cargados en la plataforma?",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "get_datasets", "arguments": {}}}],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_upload_dataset_csv_output = [
    {
        "role": "user",
        "content": (
            "Carga el dataset ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\iris.csv' "
            "con nombre 'iris', inference_rows 1000, extra_params con dataloader CSVDataLoader, separator ',', header infer, "
            "names None, encoding 'utf-8', na_values None, keep_default_na true, true_values None, false_values None, "
            "skip_blank_lines true, skiprows 0 y nrows None. Usa la herramienta upload_dataset."
        ),
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "upload_dataset",
                    "arguments": {
                        "file_path": "C:\\Users\\FANB\\Undecimo semestre\\Datasets\\iris.csv",
                        "name": "iris",
                        "inference_rows": 1000,
                        "extra_params": {
                            "dataloader": "CSVDataLoader",
                            "separator": ",",
                            "header": "infer",
                            "names": None,
                            "encoding": "utf-8",
                            "na_values": None,
                            "keep_default_na": True,
                            "true_values": None,
                            "false_values": None,
                            "skip_blank_lines": True,
                            "skiprows": None,
                            "nrows": None,
                        },
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_upload_dataset_json_output = [
    {
        "role": "user",
        "content": (
            "Carga el dataset ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\translationEngSpaDatasetSmall.json' "
            "con nombre 'translationEngSpaDatasetSmall', inference_rows 1000, extra_params con dataloader JSONDataLoader, "
            "data_key None. Usa la herramienta upload_dataset."
        ),
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "upload_dataset",
                    "arguments": {
                        "file_path": "C:\\Users\\FANB\\Undecimo semestre\\Datasets\\translationEngSpaDatasetSmall.json",
                        "name": "translationEngSpaDatasetSmall",
                        "inference_rows": 1000,
                        "extra_params": {
                            "dataloader": "JSONDataLoader",
                            "data_key": "data",
                        },
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_upload_dataset_excel_output = [
    {
        "role": "user",
        "content": (
            "Carga el dataset ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\train.xlsx' "
            "con nombre 'train', inference_rows 1000, extra_params con dataloader ExcelDataLoader, sheet 0, usecols None, "
            "header 0, names None, na_values None, keep_default_na true, true_values None, false_values None, "
            "skiprows None y nrows None. Usa la herramienta upload_dataset."
        ),
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "upload_dataset",
                    "arguments": {
                        "file_path": "C:\\Users\\FANB\\Undecimo semestre\\Datasets\\train.xlsx",
                        "name": "train",
                        "inference_rows": 1000,
                        "extra_params": {
                            "dataloader": "ExcelDataLoader",
                            "sheet": 0,
                            "usecols": None,
                            "header": 0,
                            "names": None,
                            "na_values": None,
                            "keep_default_na": True,
                            "true_values": None,
                            "false_values": None,
                            "skiprows": None,
                            "nrows": None,
                        },
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_read_dataset_rows_with_root_output = [
    {
        "role": "user",
        "content": (
            "Inspecciona el archivo ubicado en la ruta 'C:\\Users\\FANB\\Undecimo semestre\\Datasets\\iris.csv' "
            "y muestra las primeras 5 filas usando la herramienta read_dataset_rows_with_root."
        ),
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "read_dataset_rows_with_root",
                    "arguments": {
                        "root": "C:\\Users\\FANB\\Undecimo semestre\\Datasets\\iris.csv",
                        "number_rows_to_read": 5,
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_get_dataset_info_by_name_output = [
    {
        "role": "user",
        "content": "Obtén información detallada del dataset con nombre 'iris' usando la herramienta get_dataset_info_by_name.",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "get_dataset_info_by_name",
                    "arguments": {
                        "dataset_name": "iris",
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_get_column_with_types_by_name_output = [
    {
        "role": "user",
        "content": "Obtén las columnas con tipos del dataset llamado 'iris' usando la herramienta get_column_with_types_by_name.",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "get_column_with_types_by_name",
                    "arguments": {
                        "dataset_name": "iris",
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]


test_delete_dataset_output = [
    {
        "role": "user",
        "content": "Elimina el dataset con id 1 usando la herramienta delete_dataset.",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "delete_dataset",
                    "arguments": {
                        "dataset_id": 1,
                    },
                }
            }
        ],
    },
    {"role": "tool", "content": ""},
    {"role": "assistant", "content": ""},
]
