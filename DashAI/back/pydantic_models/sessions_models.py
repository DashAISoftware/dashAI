from typing import Literal, Union

from pydantic import BaseModel, Field


class GetSessionParameters(BaseModel):
    model_session_id: int = Field(
        ...,
        description=(
            "ID de la sesión del módulo 'Modelos' de la cual se quieren "
            "obtener los detalles y parámetros"
        ),
    )


class DeleteSession(BaseModel):
    model_session_id: int = Field(
        ..., description="ID de la sesión del módulo 'Modelos' a eliminar"
    )


class GetModelSessionMetrics(BaseModel):
    model_session_id: int = Field(
        ...,
        description=(
            "ID de la sesión del módulo 'Modelos' de la cual se quieren "
            "obtener las métricas asociados a los modelos de la sesión"
        ),
    )


class DeleteModelFromSessionParams(BaseModel):
    run_id: int = Field(
        ...,
        description=(
            "ID del modelo (run) que se quiere eliminar dentro de una "
            "sesión del módulo 'Modelos'. No corresponde al model_session_id."
        ),
    )


class RunModelParams(BaseModel):
    run_id: int = Field(
        ...,
        description=(
            "ID del modelo (run) que se quiere entrenar dentro de una sesión del "
            "módulo 'Modelos'. No corresponde al model_session_id."
        ),
    )


class ManualDivision(BaseModel):
    train: list[int] = Field(
        ...,
        description=(
            "Lista de indices del dataset que se usarán para el conjunto "
            "de entrenamiento"
        ),
    )
    validation: list[int] = Field(
        ...,
        description=(
            "Lista de indices del dataset que se usarán para el conjunto de validación"
        ),
    )
    test: list[int] = Field(
        ...,
        description=(
            "Lista de indices del dataset que se usarán para el conjunto de prueba."
        ),
    )
    splitType: str = "manual"  # noqa: N815


class RandomDivision(BaseModel):
    train: float = Field(
        default=0.6,
        ge=0,
        le=1,
        description=(
            "Valor entre 0 y 1 que representa la proporción del dataset "
            "que se usará para entrenamiento"
        ),
    )
    validation: float = Field(
        default=0.2,
        ge=0,
        le=1,
        description=(
            "Valor entre 0 y 1 que representa la proporción del dataset que se usará "
            "para validación"
        ),
    )
    test: float = Field(
        default=0.2,
        ge=0,
        le=1,
        description=(
            "Valor entre 0 y 1 que representa la proporción del dataset que se usará "
            "para prueba"
        ),
    )
    shuffle: bool = Field(
        default=True,
        description=(
            "Valor que indica si se deben mezclar los datos antes de dividirlos en "
            "conjuntos de entrenamiento, validación y prueba"
        ),
    )
    stratify: bool = Field(
        default=True,
        description=(
            "Valor que indica si se debe realizar una división estratificada del "
            "dataset al crear los conjuntos de entrenamiento, validación y prueba"
        ),
    )
    seed: int = Field(
        default=42,
        description=(
            "Valor de la semilla para la generación de números aleatorios "
            "al mezclar y dividir el dataset"
        ),
    )
    splitType: str = "random"  # noqa: N815


class CreateSessionParams(BaseModel):
    dataset_id: int = Field(
        ...,
        description=(
            "ID del dataset a usar para la nueva sesión de modelo. "
            "Cada dataset tiene un ID único."
        ),
    )
    task_name: Literal[
        "TabularClassificationTask",
        "TextClassificationTask",
        "TranslationTask",
        "RegressionTask",
    ] = Field(
        ..., description="Nombre del tipo de tarea que ejecutará la sesión de modelo"
    )
    name: str = Field(..., description="Nombre de la sesión de modelo")
    input_columns: list[str] = Field(
        ...,
        description=(
            "Nombres de las columnas del dataset que se usarán como entrada "
            "para el entrenamiento de modelos."
        ),
    )
    output_columns: list[str] = Field(
        ...,
        description=(
            "Nombres de las columnas del dataset que se usarán como salida "
            "para el entrenamiento de modelos."
        ),
    )
    splits: Union[ManualDivision, RandomDivision] = Field(
        ...,
        description=(
            "Parámetros para dividir el dataset en conjuntos de entrenamiento, "
            "validación y prueba. Puede ser una división manual o una división "
            "aleatoria con opciones de mezcla y estratificación."
        ),
    )
