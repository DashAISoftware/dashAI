from typing import Any

import requests
from langchain.tools import tool
from langchain_core.tools import BaseTool

from DashAI.back.Agent_tools.utils import (
    check_explorer_status,
    create_explorer_and_enqueue,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.pydantic_models.explorers_models import (
    CreateBoxPlotParams,
    CreateCorrelationMatrixParams,
    CreateCovarianceMatrixParams,
    CreateDensityHeatmapParams,
    CreateDescribeExplorerParams,
    CreateECDFPlotParams,
    CreateHistogramParams,
    CreateMultiColumnBoxPlotParams,
    CreateParallelCategoriesParams,
    CreateParallelCoordinatesParams,
    CreateRowExplorerParams,
    CreateScatterMatrixParams,
    CreateScatterPlotParams,
    CreateWordcloudParams,
    DeleteExplorerById,
    ExplorerColumn,
    GetExplorerResults,
)


@tool(
    "get_explorers",
    description=(
        "Descubre todos los tipos de exploradores disponibles en DashAI para crear "
        "visualizaciones y análisis."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get Explorers", es="Obtener exploradores"
        )
    },
)
def get_explorers() -> list[Any] | str:
    """Retrieve the explorer components available in DashAI.

    Queries the platform for the explorer components that can be used to
    create visualizations and data analyses within notebooks.

    Returns
    -------
    list[Any] | str
        A list containing the available explorer components if the request
        succeeds, or an error message if the explorers cannot be retrieved.
    """
    endpoint = "http://localhost:8000/api/v1/component/"
    params = {"select_types": ["Explorer"]}
    try:
        response = requests.get(
            endpoint,
            params=params,
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 200:
            return f"La herramienta se ha ejecutado con éxito: {response.json()}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los explorers: {exc}"


@tool(
    "delete_explorer_by_id",
    args_schema=DeleteExplorerById,
    description=(
        "Elimina un explorador creado en el notebook usando su explorer_id. "
        "El explorador y sus gráficos se removerán del notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Delete Explorer by ID", es="Eliminar explorador por ID"
        )
    },
)
def delete_explorer_by_id(explorer_id: int) -> str:
    """Delete an explorer from the DashAI platform.

    Permanently removes the explorer identified by ``explorer_id`` together
    with its associated visualizations from the notebook.

    Parameters
    ----------
    explorer_id : int
        Identifier of the explorer to delete.

    Returns
    -------
    str
        A message indicating whether the explorer was deleted successfully or
        describing the error encountered during the deletion process.
    """
    endpoint = f"http://localhost:8000/api/v1/explorer/{explorer_id}"
    try:
        response = requests.delete(
            endpoint, headers={"Content-Type": "application/json"}
        )
        if response.status_code == 204:
            return (
                f"La herramienta se ha ejecutado con éxito: Se ha eliminado "
                f"el explorer {explorer_id} de la plataforma"
            )

        return f"Error al eliminar el explorer: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error durante la eliminacion del explorer: {exc}"


@tool(
    "get_explorer_results_by_explorer_id",
    args_schema=GetExplorerResults,
    description=(
        "Obtiene los resultados y datos del explorador una vez que haya terminado "
        "su ejecución.  Solo es posible ejecutar esta herramienta para aquellos "
        "exploradores de tipo tabular. Retorna gráficos o tablas según el tipo."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get Explorer Results by ID",
            es="Obtener resultados del explorador por ID",
        )
    },
)
def get_explorer_results_by_explorer_id(explorer_id: int) -> dict[str, Any] | str:
    """Retrieve the results of a completed explorer.

    Verifies that the specified explorer has finished executing before
    requesting its results. Depending on the explorer type, the returned
    information may contain data associated with the explorer or a message
    that specify the explorer cannot return data.


    Parameters
    ----------
    explorer_id : int
        Identifier of the explorer whose results will be retrieved.

    Returns
    -------
    dict[str, Any] | str
        The explorer results or a descriptive message indicating that the
        explorer is still running, failed, or produced an unsupported output
        format.
    """
    explorer_info = check_explorer_status(explorer_id)
    if isinstance(explorer_info, str):
        return explorer_info

    status = explorer_info.get("status")

    if status == 4:
        return f"El explorer {explorer_id} terminó con error. "

    if status != 3:
        return f"El explorer {explorer_id} aún no ha terminado de ejecutarse. "

    endpoint = f"http://localhost:8000/api/v1/explorer/{explorer_id}/results/"
    try:
        response = requests.post(
            endpoint,
            json={"options": {}},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            return (
                f"Error al obtener los resultados del explorer {explorer_id}: "
                f"HTTP {response.status_code} - {response.text}"
            )
        results = response.json()
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener los resultados del explorer: {exc}"

    result_type = results.get("type", "")
    data = results.get("data")

    if result_type == "plotly_json":
        return (
            "No es posible obtener los datos asociados a este explorador.  No es "
            "un error del sistema sino que los exploradores de tipo plotly_json "
            "no retornan datos tabulares o numéricos"
        )

    if result_type == "tabular":
        return (
            f"La herramienta se ha ejecutado con éxito.  El explorer id es "
            f"{explorer_id}.  El type es {result_type}. La data es \n {data}"
        )

    if result_type == "image_base64":
        return {
            "explorer_id": explorer_id,
            "type": result_type,
            "message": "El resultado de este explorer es una imagen (base64) que "
            "no puede ser interpretada como datos numéricos o tabulares. Para "
            "analizar el contenido subyacente, considera usar un explorer "
            "diferente que retorne datos tabulares.",
        }
    return (
        "Error crítico. Se obtuvo respuesta desde el endpoint pero el formato "
        "del resultado no se reconoce."
    )


@tool(
    "create_correlation_matrix",
    args_schema=CreateCorrelationMatrixParams,
    description=(
        "Crea una matriz de correlación que muestra las relaciones numéricas "
        "entre variables en el notebook mediante gráfico."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Correlation Matrix",
            es="Crear explorador matriz de correlación",
        )
    },
)
def create_correlation_matrix(
    notebook_id: int,
    columns: list[ExplorerColumn],
    method: str,
    min_periods: int,
    numeric_only: bool,
    plot: bool,
) -> dict:
    """Create a correlation matrix explorer in a notebook.

    Creates a correlation matrix explorer using the selected dataset columns
    and enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset columns included in the correlation analysis.
    method : str
        Correlation method to use (for example, Pearson, Spearman, or Kendall).
    min_periods : int
        Minimum number of observations required to compute each correlation.
    numeric_only : bool
        Whether to restrict the computation to numeric columns.
    plot : bool
        Whether to generate a graphical visualization of the correlation
        matrix.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="CorrelationMatrixExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "method": method,
            "min_periods": min_periods,
            "numeric_only": numeric_only,
            "plot": plot,
        },
    )


@tool(
    "create_covariance_matrix",
    args_schema=CreateCovarianceMatrixParams,
    description=(
        "Crea una matriz de covarianza que mide la variabilidad conjunta entre pares "
        "de columnas numéricas en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Covariance Matrix",
            es="Crear explorador matriz de covarianza",
        )
    },
)
def create_covariance_matrix(
    notebook_id: int,
    columns: list[Any],
    min_periods: int,
    delta_degree_of_freedom: int,
    numeric_only: bool,
    plot: bool,
) -> Any:
    """Create a covariance matrix explorer in a notebook.

    Creates a covariance matrix explorer using the selected dataset columns
    and enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset columns included in the covariance analysis. At least two
        columns must be provided.
    min_periods : int
        Minimum number of observations required to compute a valid covariance
        for each pair of columns.
    delta_degree_of_freedom : int
        Delta degrees of freedom used when computing the covariance matrix.
        This parameter is only applied when ``numeric_only`` is ``True``.
    numeric_only : bool
        Whether to restrict the computation to numeric columns.
    plot : bool
        Whether to generate a graphical visualization of the covariance
        matrix.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="CovarianceMatrixExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "min_periods": min_periods,
            "delta_degree_of_freedom": delta_degree_of_freedom,
            "numeric_only": numeric_only,
            "plot": plot,
        },
    )


@tool(
    "create_multi_column_box_plot",
    args_schema=CreateMultiColumnBoxPlotParams,
    description=(
        "Crea un diagrama de cajas que compara las columnas según datos clave "
        "representados por la caja en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Multi-Column Box Plot",
            es="Crear explorador diagrama de cajas multicolumna",
        )
    },
)
def create_multi_column_box_plot(
    notebook_id: int,
    columns: list[Any],
    horizontal: bool,
    points: str,
    opposite_axis: str | int | None,
) -> Any:
    """Create a multi-column box plot explorer in a notebook.

    Creates a box plot explorer that compares one or more dataset columns and
    enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset columns to include in the visualization. At least one column
        must be provided.
    horizontal : bool
        Whether to display the box plots horizontally instead of vertically.
    points : {"all", "outliers", "False"}
        Determines which sample points are displayed in the plot.
    opposite_axis : str | int | None
        Name or index of the column to use on the opposite axis. If ``None``,
        no opposite axis is used.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="MultiColumnBoxPlotExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "horizontal": horizontal,
            "points": points,
            "opposite_axis": opposite_axis,
        },
    )


@tool(
    "create_parallel_categories",
    args_schema=CreateParallelCategoriesParams,
    description=(
        "Crea un gráfico de categorías paralelas para visualizar relaciones y "
        "patrones entre columnas categóricas en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Parallel Categories",
            es="Crear explorador categorías paralelas",
        )
    },
)
def create_parallel_categories(
    notebook_id: int, columns: list[Any], color_column: int | str | None
) -> Any:
    """Create a parallel categories explorer in a notebook.

    Creates a parallel categories explorer for visualizing relationships
    between categorical variables and enqueues its execution within the
    specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Categorical dataset columns to include in the visualization. At least
        two string columns must be provided.
    color_column : int | str | None
        Name or index of the column used to color the categories. If ``None``,
        the default coloring is applied.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="ParallelCategoriesExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"color_column": color_column},
    )


@tool(
    "create_parallel_coordinates",
    args_schema=CreateParallelCoordinatesParams,
    description=(
        "Crea un gráfico de coordenadas paralelas para visualizar patrones y "
        "correlaciones entre múltiples etiquetas numéricas en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Parallel Coordinates",
            es="Crear explorador coordenadas paralelas",
        )
    },
)
def create_parallel_coordinates(
    notebook_id: int, columns: list[Any], color_column: int | str | None
) -> Any:
    """Create a parallel coordinates explorer in a notebook.

    Creates a parallel coordinates explorer for visualizing relationships
    among multiple numerical variables and enqueues its execution within the
    specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Numeric dataset columns to include in the visualization. At least two
        numeric columns must be provided.
    color_column : int | str | None
        Name or index of the column used to color the plotted lines. If
        ``None``, the default coloring is applied.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="ParallelCordinatesExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"color_column": color_column},
    )


@tool(
    "create_box_plot",
    args_schema=CreateBoxPlotParams,
    description=(
        "Crea un diagrama de cajas que visualiza la dispersión, cuartiles, "
        "mediana y outliers de columnas en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Box Plot", es="Crear explorador diagrama de cajas"
        )
    },
)
def create_box_plot(
    notebook_id: int, columns: list[Any], horizontal: bool, points: str
) -> Any:
    """Create a box plot explorer in a notebook.

    Creates a box plot explorer for visualizing the distribution of one or two
    numerical dataset columns and enqueues its execution within the specified
    notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Numeric dataset columns to include in the visualization. One or two
        columns must be provided.
    horizontal : bool
        Whether to display the box plot horizontally instead of vertically.
    points : {"all", "outliers", "False"}
        Determines which sample points are displayed in the plot.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="BoxPlotExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"horizontal": horizontal, "points": points},
    )


@tool(
    "create_ecdf_plot",
    args_schema=CreateECDFPlotParams,
    description=(
        "Crea un gráfico ECDF que visualiza la función de distribución acumulativa "
        "de datos numéricos en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer ECDF Plot", es="Crear explorador gráfico ECDF"
        )
    },
)
def create_ecdf_plot(
    notebook_id: int,
    columns: list[Any],
    color_column: int | str | None,
    facet_col: int | str | None,
    facet_row: int | str | None,
    ecdf_norm: str,
) -> Any:
    """Create an empirical cumulative distribution function (ECDF) explorer.

    Creates an ECDF plot explorer using the selected numeric dataset columns
    and enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Numeric dataset columns to include in the visualization. At least one
        column must be provided.
    color_column : int | str | None
        Name or index of the column used to color the ECDF curves.
    facet_col : int | str | None
        Name or index of the column used to split the visualization into
        column facets.
    facet_row : int | str | None
        Name or index of the column used to split the visualization into
        row facets.
    ecdf_norm : {"none", "percent", "probability"}
        Normalization applied to the ECDF values.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="ECDFPlotExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "ecdf_norm": ecdf_norm,
            "color_column": color_column,
            "facet_col": facet_col,
            "facet_row": facet_row,
        },
    )


@tool(
    "create_histogram",
    args_schema=CreateHistogramParams,
    description=(
        "Crea un histograma que muestra la distribución de frecuencias y "
        "rangos de valores de una columna en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Histogram", es="Crear explorador histograma"
        )
    },
)
def create_histogram(
    notebook_id: int,
    columns: list[Any],
    nbins: int | None,
    histfunc: str,
    histnorm: str,
    color_group: str | int | None,
    pattern_group: str | int | None,
) -> Any:
    """Create a histogram explorer in a notebook.

    Creates a histogram explorer for visualizing the distribution of a dataset
    column and enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset column to visualize. Exactly one column must be provided.
    nbins : int | None
        Number of histogram bins. If ``None``, an appropriate value is chosen
        automatically.
    histfunc : {"count", "sum", "avg", "min", "max"}
        Aggregation function applied within each histogram bin.
    histnorm : {"", "percent", "probability", "density", "probability density"}
        Normalization applied to the histogram values.
    color_group : str | int | None
        Name or index of the column used to group bars by color.
    pattern_group : str | int | None
        Name or index of the column used to group bars by pattern.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="HistogramPlotExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "histfunc": histfunc,
            "histnorm": histnorm,
            "nbins": nbins,
            "color_group": color_group,
            "pattern_group": pattern_group,
        },
    )


@tool(
    "create_wordcloud",
    args_schema=CreateWordcloudParams,
    description=(
        "Crea una nube de palabras que resume visualmente las palabras más frecuentes "
        "en columnas de texto del notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Wordcloud", es="Crear explorador nube de palabras"
        )
    },
)
def create_wordcloud(
    notebook_id: int, columns: list[Any], max_words: int, background_color: str | None
) -> Any:
    """Create a word cloud explorer in a notebook.

    Creates a word cloud explorer that summarizes the most frequent words in
    one or more text columns and enqueues its execution within the specified
    notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Text dataset columns to analyze. At least one string column must be
        provided.
    max_words : int
        Maximum number of words displayed in the word cloud.
    background_color : str | None
        Background color of the word cloud. If ``None``, a transparent
        background is used.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="WordcloudExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"max_words": max_words, "background_color": background_color},
    )


@tool(
    "create_scatter_plot",
    args_schema=CreateScatterPlotParams,
    description=(
        "Crea un gráfico de dispersión que visualiza la relación y correlación "
        "entre dos variables numéricas en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Scatter Plot",
            es="Crear explorador gráfico de dispersión",
        )
    },
)
def create_scatter_plot(
    notebook_id: int,
    columns: list[Any],
    color_group: int | str | None,
    simbol_group: int | str | None,
    point_size: int | str | None,
) -> Any:
    """Create a scatter plot explorer in a notebook.

    Creates a scatter plot explorer for visualizing the relationship between
    two numeric dataset columns and enqueues its execution within the
    specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Numeric dataset columns to visualize. Exactly two columns must be
        provided.
    color_group : int | str | None
        Name or index of the column used to color the points.
    simbol_group : int | str | None
        Name or index of the column used to assign different point symbols.
    point_size : int | str | None
        Name or index of the column used to determine the size of each point.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="ScatterPlotExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "color_group": color_group,
            "simbol_group": simbol_group,
            "point_size": point_size,
        },
    )


@tool(
    "create_density_heatmap",
    args_schema=CreateDensityHeatmapParams,
    description=(
        "Crea un mapa de calor de densidad que muestra la concentración de "
        "puntos y patrones para dos variables en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Density Heatmap",
            es="Crear explorador mapa de calor de densidad",
        )
    },
)
def create_density_heatmap(
    notebook_id: int, columns: list[Any], nbinsx: int | None, nbinsy: int | None
) -> Any:
    """Create a density heatmap explorer in a notebook.

    Creates a density heatmap explorer for visualizing the concentration of
    observations across two dataset columns and enqueues its execution within
    the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset columns to analyze. Exactly two columns must be provided.
    nbinsx : int | None
        Number of bins along the x-axis. If ``None``, the value is selected
        automatically.
    nbinsy : int | None
        Number of bins along the y-axis. If ``None``, the value is selected
        automatically.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="DensityHeatmapExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"nbinsx": nbinsx, "nbinsy": nbinsy},
    )


@tool(
    "create_scatter_matrix",
    args_schema=CreateScatterMatrixParams,
    description=(
        "Crea una matriz de dispersión que compara todas las relaciones por pares "
        "entre múltiples variables numéricas en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Scatter Matrix",
            es="Crear explorador matriz de dispersión",
        )
    },
)
def create_scatter_matrix(
    notebook_id: int,
    columns: list[Any],
    color_group: str | int | None,
    simbol_group: str | int | None,
) -> Any:
    """Create a scatter matrix explorer in a notebook.

    Creates a scatter matrix explorer for comparing pairwise relationships
    among multiple numeric dataset columns and enqueues its execution within
    the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Numeric dataset columns to visualize. At least two columns must be
        provided.
    color_group : str | int | None
        Name or index of the column used to color the plotted points.
    simbol_group : str | int | None
        Name or index of the column used to assign different point symbols.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="ScatterMatrixExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"color_group": color_group, "simbol_group": simbol_group},
    )


@tool(
    "create_describe_dataset",
    args_schema=CreateDescribeExplorerParams,
    description=(
        "Crea un resumen estadístico detallado de cada columna teniendo la respuesta "
        "de la herramienta los campos:"
        "- Count: Cantidad de valores no nulos en la columna\n"
        "- unique: Cantidad de valores únicos de columnas categóricas\n"
        "- top: Valor más frecuente en columnas categóricas\n"
        "- freq: Frecuencia del valor más frecuente en columnas categóricas\n"
        "- mean: Promedio de columnas numéricas\n"
        "- std: Desviación estándar de columnas numéricas\n"
        "- min: Valor mínimo de columnas numéricas\n"
        "- x%: Valores asociadas al percentil x para columnas numéricas\n"
        "- max: Valor máximo de columnas numéricas\n"
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Describe Dataset",
            es="Crear explorador describir dataset",
        )
    },
)
def create_describe_dataset(
    notebook_id: int,
    columns: list[Any],
    percentiles: str | None,
    include: str | None,
    exclude: str | None,
) -> Any:
    """Create a descriptive statistics explorer in a notebook.

    Creates an explorer that computes descriptive statistics for the selected
    dataset columns and enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset columns to analyze. At least one column must be provided.
    percentiles : str | None
        Comma-separated list of percentiles to include in the summary.
    include : str | None
        Data types to include in the descriptive analysis.
    exclude : str | None
        Data types to exclude from the descriptive analysis.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="DescribeExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={"percentiles": percentiles, "include": include, "exclude": exclude},
    )


@tool(
    "create_row_explorer",
    args_schema=CreateRowExplorerParams,
    description=(
        "Crea un visor de filas que muestra muestras de datos del dataset "
        "para inspeccionar valores reales en el notebook."
    ),
    extras={
        "display_name": MultilingualString(
            en="Create explorer Row Explorer", es="Crear explorador visor de filas"
        )
    },
)
def create_row_explorer(
    notebook_id: int,
    columns: list[ExplorerColumn],
    row_ammount: int,
    shuffle: bool,
    from_top: bool,
) -> Any:
    """Create a row explorer in a notebook.

    Creates a row explorer for inspecting a sample of dataset rows and
    enqueues its execution within the specified notebook.

    Parameters
    ----------
    notebook_id : int
        Identifier of the notebook where the explorer will be created.
    columns : list[ExplorerColumn]
        Dataset columns to include in the output. At least one column must be
        provided.
    row_ammount : int
        Maximum number of rows to retrieve.
    shuffle : bool
        Whether to randomly shuffle the selected rows.
    from_top : bool
        Whether to retrieve rows from the beginning of the dataset. If
        ``False``, rows are retrieved from the end.

    Returns
    -------
    dict
        Dictionary containing the information required to track the created
        explorer and its execution.
    """
    return create_explorer_and_enqueue(
        exploration_type="RowExplorer",
        notebook_id=notebook_id,
        columns=columns,
        parameters={
            "row_ammount": row_ammount,
            "shuffle": shuffle,
            "from_top": from_top,
        },
    )


EXPLORER_TOOLS: list[BaseTool] = [
    get_explorers,
    delete_explorer_by_id,
    get_explorer_results_by_explorer_id,
    create_correlation_matrix,
    create_covariance_matrix,
    create_multi_column_box_plot,
    create_parallel_categories,
    create_parallel_coordinates,
    create_box_plot,
    create_ecdf_plot,
    create_histogram,
    create_wordcloud,
    create_scatter_plot,
    create_density_heatmap,
    create_scatter_matrix,
    create_describe_dataset,
    create_row_explorer,
]
