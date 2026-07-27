from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class DeleteExplorerById(BaseModel):
    explorer_id: int = Field(..., description="ID del explorer a eliminar")


class GetExplorerResults(BaseModel):
    explorer_id: int = Field(
        ..., description="ID del explorer para obtener sus resultados"
    )


class ExplorerColumn(BaseModel):
    columnName: str = Field(  # noqa: N815
        ..., description="Nombre de la columna"
    )
    valueType: Literal[  # noqa: N815
        "Float",
        "String",
        "Integer",
        "Categorical",
        "Image",
        "Text",
    ] = Field(..., description="Tipo de valor de la columna")
    dataType: Literal["float64", "int64", "string", "object", "bool"] = Field(  # noqa: N815
        ..., description="Tipo de dato de la columna"
    )
    id: int = Field(..., description="ID de la columna")
    order: int = Field(..., description="Orden de la columna en el dataset")


class CreateCorrelationMatrixParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas seleccionadas para la matriz de correlación. "
            "Debe haber al menos dos columnas y deben ser tipo Float, "
            "Integer o Categorical."
        ),
    )
    method: Literal["pearson", "kendall", "spearman"] = Field(
        "pearson", description="Método de correlación a usar"
    )
    min_periods: int = Field(
        1,
        description=(
            "Número mínimo de observaciones requeridas por par de "
            "columnas para obtener un resultado válido. Solo con pearson o spearman"
        ),
    )
    numeric_only: bool = Field(
        True,
        description=(
            "Si es True, incluye solo columnas numéricas al calcular la "
            "correlación; de lo contrario incluye todas."
        ),
    )
    plot: bool = Field(True, description="Si es True, el resultado será graficado.")


class CreateCovarianceMatrixParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas para la matriz de covarianza (mínimo 2). "
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    min_periods: int = Field(
        1,
        description=(
            "Número mínimo de observaciones requeridas por par de columnas "
            "para obtener un resultado válido."
        ),
    )
    delta_degree_of_freedom: int = Field(
        1,
        description=(
            "Grados de libertad delta a usar al calcular la matriz "
            "de covarianza. Solo se usa si numeric_only es True."
        ),
    )
    numeric_only: bool = Field(
        True,
        description=(
            "Si es True, incluye solo columnas numéricas en el cálculo; "
            "de lo contrario incluye todas las columnas."
        ),
    )
    plot: bool = Field(True, description="Si es True, el resultado será graficado.")


class CreateMultiColumnBoxPlotParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas (mínimo 1)"
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    horizontal: bool = Field(
        False,
        description=(
            "Si es True, el diagrama de caja será horizontal; en caso "
            "contrario, vertical."
        ),
    )
    points: Literal["all", "outliers", "False"] = Field(
        "outliers", description="Determina qué puntos se muestran."
    )
    opposite_axis: Optional[Union[str, int]] = Field(
        None, description="Nombre o índice de columna para el eje opuesto."
    )


class CreateParallelCategoriesParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas de tipo string (mínimo 2)"
            "Las columnas deben ser de tipo Categorical."
        ),
    )
    color_column: Optional[Union[int, str]] = Field(
        None, description="Columna usada para colorear los puntos."
    )


class CreateParallelCoordinatesParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas numéricas (mínimo 2)"
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    color_column: Optional[Union[int, str]] = Field(
        None, description="Columna usada para colorear los puntos."
    )


class CreateBoxPlotParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas numéricas (1 o 2)"
            "Las columnas deben ser de tipo Float o Integer."
        ),
    )
    horizontal: bool = Field(
        False,
        description=(
            "Si es True, el diagrama de caja será horizontal; en caso "
            "contrario, vertical."
        ),
        examples=[True, False],
    )
    points: Literal["all", "outliers", "False"] = Field(
        "outliers",
        description=(
            "Las opciones son 'all', 'outliers' o 'False'. Determina qué puntos se "
            "muestran en el gráfico."
        ),
    )


class CreateECDFPlotParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas numéricas (mínimo 1)"
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    color_column: Optional[Union[int, str]] = Field(
        None, description="Columna usada para colorear el gráfico ECDF."
    )
    facet_col: Optional[Union[int, str]] = Field(
        None, description="Columna usada para facetar el gráfico ECDF por columnas."
    )
    facet_row: Optional[Union[int, str]] = Field(
        None, description="Columna usada para facetar el gráfico ECDF por filas."
    )
    ecdf_norm: str = Field(
        "probability",
        description="Tipo de normalización usada en el gráfico ECDF.",
        examples=["none", "percent", "probability"],
    )


class CreateHistogramParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista con exactamente 1 columna"
            "La columna debe ser de tipo Float, Integer o Categorical."
        ),
    )
    nbins: Optional[int] = Field(
        None, description="Número de bins a usar en el histograma."
    )
    histfunc: Literal["count", "sum", "avg", "min", "max"] = Field(
        "count",
        description="Función de agrupación usada para este trazo de histograma.",
    )
    histnorm: Literal[
        "", "percent", "probability", "density", "probability density"
    ] = Field(
        "",
        description=(
            "Tipo de normalización usada en este histograma. Cadena "
            "vacía para sin normalización."
        ),
    )
    color_group: Optional[Union[str, int]] = Field(
        None,
        description="Nombre o índice de columna para agrupar puntos por color.",
        examples=["species", None],
    )
    pattern_group: Optional[Union[str, int]] = Field(
        None,
        description="Nombre o índice de columna para agrupar patrones de puntos.",
        examples=["region", None],
    )


class CreateWordcloudParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas de tipo string (mínimo 1)"
            "Las columnas deben ser de tipo Text."
        ),
    )
    max_words: int = Field(
        200, description="Número máximo de palabras a mostrar en la nube de palabras."
    )
    background_color: Optional[str] = Field(
        None,
        description=(
            "Color de fondo de la nube de palabras. Si es None, el fondo "
            "es transparente."
        ),
        examples=["white", "black", None],
    )


class CreateScatterPlotParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista con exactamente 2 columnas"
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    color_group: Optional[Union[int, str]] = Field(
        None, description="Nombre o índice de columna para agrupar puntos por color."
    )
    simbol_group: Optional[Union[int, str]] = Field(
        None, description="Nombre o índice de columna para agrupar símbolos de puntos."
    )
    point_size: Optional[Union[int, str]] = Field(
        None,
        description="Nombre o índice de columna para definir el tamaño de cada punto.",
    )


class CreateDensityHeatmapParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista con exactamente 2 columnas"
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    nbinsx: Optional[int] = Field(
        None, description="Número de bins a lo largo del eje x."
    )
    nbinsy: Optional[int] = Field(
        None, description="Número de bins a lo largo del eje y."
    )


class CreateScatterMatrixParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ...,
        description=(
            "Lista de columnas numéricas (mínimo 2)"
            "Las columnas deben ser de tipo Float, Integer o Categorical."
        ),
    )
    color_group: Optional[Union[str, int]] = Field(
        None, description="Nombre o índice de columna para agrupar puntos por color."
    )
    simbol_group: Optional[Union[str, int]] = Field(
        None, description="Nombre o índice de columna para agrupar símbolos de puntos."
    )


class CreateDescribeExplorerParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ..., description="Lista de columnas (mínimo 1)"
    )
    percentiles: Optional[str] = Field(
        "25, 50, 75",
        description=(
            "Percentiles a incluir en la exploración. Use enteros entre 0 y"
            "100 separados por coma."
        ),
    )
    include: Optional[str] = Field(
        "all", description="Tipos de datos a incluir en la exploración."
    )
    exclude: Optional[str] = Field(
        None, description="Tipos de datos a excluir de la exploración."
    )


class CreateRowExplorerParams(BaseModel):
    notebook_id: int = Field(
        ..., description="ID del notebook donde se creará el explorador"
    )
    columns: list[ExplorerColumn] = Field(
        ..., description="Lista de columnas (mínimo 1)"
    )
    row_ammount: int = Field(
        50, description="Número máximo de filas a tomar.", examples=[10, 50, 100]
    )
    shuffle: bool = Field(
        False,
        description="Barajar las filas durante la exploración.",
        examples=[True, False],
    )
    from_top: bool = Field(
        True,
        description=(
            "Tomar filas desde el inicio del dataset. En caso contrario, "
            "tomarlas desde el final."
        ),
        examples=[True, False],
    )
