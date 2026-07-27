from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class CSVUploadParams(BaseModel):
    dataloader: Literal["CSVDataLoader"] = Field(
        "CSVDataLoader", description="Tipo de dataloader a utilizar."
    )
    separator: Literal[",", ";", "blank space", "tab"] = Field(
        ",", description="Separador de columnas del archivo CSV."
    )
    header: Union[str, int, list[int]] = Field(
        "infer",
        description=(
            "Número(s) de fila que contienen las etiquetas de columna y marcan "
            "el inicio de los datos (indexado desde cero). El comportamiento "
            "predeterminado es inferir los nombres de columna. Si los nombres de "
            "columna se pasan explícitamente, esto debe establecerse en '0'. "
            "Header también puede ser una lista de enteros que especifican las "
            "ubicaciones de fila para MultiIndex en las columnas."
        ),
    )
    names: Optional[str] = Field(
        None,
        description=(
            "Nombres de columnas separados por coma, ej.: 'col1,col2,col3'. Si el "
            "archivo tiene encabezado, pasar header=0 para sobreescribirlo."
        ),
    )
    encoding: Literal["utf-8", "latin1", "cp1252", "iso-8859-1"] = Field(
        "utf-8",
        description=(
            "Codificación del archivo. Los valores admitidos son 'utf-8', "
            "'latin1', 'cp1252', 'iso-8859-1'."
        ),
    )
    na_values: Optional[str] = Field(
        None,
        description=(
            "Valores adicionales a reconocer como NA/NaN, separados por coma, "
            "ej.: 'NULL,missing,n/a'. None para usar solo los predeterminados."
        ),
    )
    keep_default_na: bool = Field(
        True,
        description=(
            "Si se deben incluir los valores NaN predeterminados al analizar "
            "los datos (se recomienda True)."
        ),
    )
    true_values: Optional[str] = Field(
        None,
        description=(
            "Valores a interpretar como True, separados por coma, "
            "ej.: 'yes,true,1,on'. None para no realizar conversión."
        ),
    )
    false_values: Optional[str] = Field(
        None,
        description=(
            "Valores separados por comas a considerar como False. Ejemplo: "
            "'no,false,0,off'. None para no realizar conversión."
        ),
    )
    skip_blank_lines: bool = Field(
        True,
        description=(
            "Si es True, omitir líneas en blanco en lugar de interpretarlas "
            "como valores NaN."
        ),
    )
    skiprows: Optional[int] = Field(
        None,
        ge=0,
        description=(
            "Filas a omitir después del encabezado. >= 0. None para no omitir ninguna."
        ),
    )
    nrows: Optional[int] = Field(
        None,
        ge=0,
        description=(
            "Número de filas a leer del archivo. None para leer todas las filas."
        ),
    )


class JSONUploadParams(BaseModel):
    dataloader: Literal["JSONDataLoader"] = Field(
        "JSONDataLoader", description="Tipo de dataloader a utilizar."
    )
    data_key: Optional[Literal["data"]] = Field(
        None,
        description=(
            "Clave del campo raíz que contiene los registros, cuando el "
            "JSON tiene la forma {'data': [{...}]} entonces colocar 'data'. "
            "None si es una lista directa [{...}]."
        ),
    )


class ExcelUploadParams(BaseModel):
    dataloader: Literal["ExcelDataLoader"] = Field(
        "ExcelDataLoader", description="Tipo de dataloader a utilizar."
    )
    sheet: Union[str, int] = Field(
        0,
        description=(
            "El nombre de la hoja a leer o su índice basado en cero. Si se "
            "proporciona una cadena, el lector buscará una hoja con ese nombre "
            "exacto. Si se proporciona un entero, el lector seleccionará la hoja "
            "en el índice correspondiente."
        ),
    )
    header: Optional[int] = Field(
        0,
        ge=0,
        description=(
            "El número de fila donde se encuentran los nombres de columna indexado "
            "desde 0. Si es 'null', se considerará que el archivo no tiene nombres de "
            "columna."
        ),
    )
    usecols: Optional[str] = Field(
        None,
        description=(
            "Columnas a importar en formato de letras o rango de Excel. "
            "ej.: 'A:E' o 'A,C,E:F'. None para importar todas las columnas."
        ),
    )
    skiprows: Optional[int] = Field(
        None,
        ge=0,
        description="Filas a omitir al inicio del archivo. >= 0. None para no omitir.",
    )
    nrows: Optional[int] = Field(
        None, ge=1, description="Número de filas a leer. >= 1. None para leer todas."
    )
    names: Optional[str] = Field(
        None,
        description=(
            "Nombres de columnas separados por coma, ej.: 'col1,col2,col3'. "
            "None para usar la fila del encabezado del archivo."
        ),
    )
    na_values: Optional[str] = Field(
        None,
        description=(
            "Valores adicionales a reconocer como NA/NaN, separados por coma, "
            "ej.: 'NA,N/A/null'. None para usar solo los predeterminados."
        ),
    )
    keep_default_na: bool = Field(
        True,
        description=(
            "True para incluir los valores NaN predeterminados al analizar los datos."
        ),
    )
    true_values: Optional[str] = Field(
        None,
        description=(
            "Valores a interpretar como True, separados por coma. ej.: "
            "'yes,true,1'. None para no realizar conversión."
        ),
    )
    false_values: Optional[str] = Field(
        None,
        description=(
            "Valores a interpretar como False, separados por coma. ej.: "
            "'no,false,0'. None para no realizar conversión."
        ),
    )


class UploadDataset(BaseModel):
    file_path: str = Field(
        ..., description="Ruta absoluta del archivo del dataset (CSV, JSON o Excel)."
    )
    name: str = Field(
        ..., description="Nombre con el que se registrará el dataset en DashAI."
    )
    inference_rows: int = Field(
        1000,
        ge=1,
        description=("Filas usadas para inferir los tipos de columnas. >= 1."),
    )
    extra_params: Union[CSVUploadParams, JSONUploadParams, ExcelUploadParams] = Field(
        ...,
        discriminator="dataloader",
        description=(
            "Parámetros específicos del dataloader. Usar CSVUploadParams para .csv, "
            "JSONUploadParams para .json, ExcelUploadParams para .xlsx/.xls y otros "
            "formatos Excel."
        ),
    )


class DeleteDataset(BaseModel):
    dataset_id: int = Field(..., description="ID del dataset a eliminar")


class GetDatasetInfoByName(BaseModel):
    dataset_name: str = Field(
        ..., description="Nombre del dataset para obtener su información"
    )


class GetDatasetRowsWithRoot(BaseModel):
    root: str = Field(
        ..., description="Ruta del archivo del dataset para leer sus filas"
    )
    number_rows_to_read: int = Field(
        5, description="Número de filas a leer del dataset"
    )


class GetColumnsWithTypesInput(BaseModel):
    dataset_id: int = Field(
        ..., description="ID del dataset del cual obtener las columnas con sus tipos"
    )


class GetColumnsByNameInput(BaseModel):
    dataset_name: str = Field(
        ...,
        description="Nombre del dataset del cual obtener las columnas con sus tipos",
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
