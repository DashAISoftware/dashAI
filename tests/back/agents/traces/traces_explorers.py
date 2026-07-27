# ruff: noqa
def build_test_get_explorers_output():
    return [
        {
            "role": "user",
            "content": "Muestra los exploradores disponibles en DashAI usando la herramienta get_explorers.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "get_explorers", "arguments": {}}}],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_delete_explorer_by_id_output(explorer_id):
    return [
        {
            "role": "user",
            "content": f"Elimina el explorer con id {explorer_id} usando la herramienta delete_explorer_by_id.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "delete_explorer_by_id",
                        "arguments": {"explorer_id": explorer_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_get_explorer_results_by_explorer_id_output(explorer_id):
    return [
        {
            "role": "user",
            "content": f"Obtén los resultados del explorer con id {explorer_id} usando la herramienta get_explorer_results_by_explorer_id.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "get_explorer_results_by_explorer_id",
                        "arguments": {"explorer_id": explorer_id},
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_correlation_matrix_output(
    notebook_id, columns, method, min_periods, numeric_only, plot, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "method": method,
        "min_periods": min_periods,
        "numeric_only": numeric_only,
        "plot": plot,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer de matriz de correlación en el notebook con id {notebook_id} usando la herramienta create_correlation_matrix.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_correlation_matrix",
                        "arguments": arguments,
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_covariance_matrix_output(
    notebook_id, columns, min_periods, delta_degree_of_freedom, numeric_only, plot, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "min_periods": min_periods,
        "delta_degree_of_freedom": delta_degree_of_freedom,
        "numeric_only": numeric_only,
        "plot": plot,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer de matriz de covarianza en el notebook con id {notebook_id} usando la herramienta create_covariance_matrix.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_covariance_matrix",
                        "arguments": arguments,
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_multi_column_box_plot_output(
    notebook_id, columns, horizontal, points, opposite_axis, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "horizontal": horizontal,
        "points": points,
        "opposite_axis": opposite_axis,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un box plot multicolumna en el notebook con id {notebook_id} usando la herramienta create_multi_column_box_plot.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_multi_column_box_plot",
                        "arguments": arguments,
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_parallel_categories_output(
    notebook_id, columns, color_column, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "color_column": color_column,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer de categorías paralelas en el notebook con id {notebook_id} usando la herramienta create_parallel_categories.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_parallel_categories",
                        "arguments": arguments,
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_parallel_coordinates_output(
    notebook_id, columns, color_column, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "color_column": color_column,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer de coordenadas paralelas en el notebook con id {notebook_id} usando la herramienta create_parallel_coordinates.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_parallel_coordinates",
                        "arguments": arguments,
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_box_plot_output(notebook_id, columns, horizontal, points, name):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "horizontal": horizontal,
        "points": points,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer de box plot en el notebook con id {notebook_id} usando la herramienta create_box_plot.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_box_plot", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_ecdf_plot_output(
    notebook_id, columns, color_column, facet_col, facet_row, ecdf_norm, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "color_column": color_column,
        "facet_col": facet_col,
        "facet_row": facet_row,
        "ecdf_norm": ecdf_norm,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer ECDF en el notebook con id {notebook_id} usando la herramienta create_ecdf_plot.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_ecdf_plot", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_histogram_output(
    notebook_id, columns, nbins, histfunc, histnorm, color_group, pattern_group, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "nbins": nbins,
        "histfunc": histfunc,
        "histnorm": histnorm,
        "color_group": color_group,
        "pattern_group": pattern_group,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un histograma en el notebook con id {notebook_id} usando la herramienta create_histogram.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_histogram", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_wordcloud_output(
    notebook_id, columns, max_words, background_color, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "max_words": max_words,
        "background_color": background_color,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea una nube de palabras en el notebook con id {notebook_id} usando la herramienta create_wordcloud.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_wordcloud", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_scatter_plot_output(
    notebook_id, columns, color_group, simbol_group, point_size, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "color_group": color_group,
        "simbol_group": simbol_group,
        "point_size": point_size,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un gráfico de dispersión en el notebook con id {notebook_id} usando la herramienta create_scatter_plot.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_scatter_plot", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_density_heatmap_output(
    notebook_id, columns, nbinsx, nbinsy, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "nbinsx": nbinsx,
        "nbinsy": nbinsy,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un mapa de calor de densidad en el notebook con id {notebook_id} usando la herramienta create_density_heatmap.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_density_heatmap", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_scatter_matrix_output(
    notebook_id, columns, color_group, simbol_group, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "color_group": color_group,
        "simbol_group": simbol_group,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea una matriz de dispersión en el notebook con id {notebook_id} usando la herramienta create_scatter_matrix.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_scatter_matrix", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_describe_dataset_output(
    notebook_id, columns, percentiles, include, exclude, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "percentiles": percentiles,
        "include": include,
        "exclude": exclude,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorer descriptivo del dataset en el notebook con id {notebook_id} usando la herramienta create_describe_dataset.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "create_describe_dataset",
                        "arguments": arguments,
                    }
                }
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]


def build_test_create_row_explorer_output(
    notebook_id, columns, row_ammount, shuffle, from_top, name
):
    arguments = {
        "notebook_id": notebook_id,
        "columns": columns,
        "row_ammount": row_ammount,
        "shuffle": shuffle,
        "from_top": from_top,
        "name": name,
    }
    return [
        {
            "role": "user",
            "content": f"Crea un explorador de filas en el notebook con id {notebook_id} usando la herramienta create_row_explorer.",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "create_row_explorer", "arguments": arguments}}
            ],
        },
        {"role": "tool", "content": ""},
        {"role": "assistant", "content": ""},
    ]
