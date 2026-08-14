"""Unit that loads the dataset a model was trained on."""

import logging
from typing import TYPE_CHECKING

from DashAI.back.core.schema_fields import (
    BaseSchema,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

log = logging.getLogger(__name__)


class LoadTrainingDatasetSchema(BaseSchema):
    train_dataset_file_path: schema_field(
        string_field(),
        placeholder="",
        description=MultilingualString(
            en="Folder of the dataset the model was trained on — the stored "
            "row's own path, not the inner dataset directory.",
            es="Carpeta del conjunto de datos con el que se entrenó el "
            "modelo: la ruta de la propia fila almacenada, no el directorio "
            "interno del conjunto de datos.",
            pt="Pasta do conjunto de dados com que o modelo foi treinado — o "
            "caminho da própria linha armazenada, não o diretório interno do "
            "conjunto de dados.",
            de="Ordner des Datensatzes, mit dem das Modell trainiert wurde — "
            "der Pfad der gespeicherten Zeile selbst, nicht das innere "
            "Datensatzverzeichnis.",
            zh="模型训练所用数据集的文件夹——已存储行自身的路径，而非内部数据集目录。",
        ),
        alias=MultilingualString(
            en="Training dataset folder",
            es="Carpeta del conjunto de entrenamiento",
            pt="Pasta do conjunto de treino",
            de="Ordner des Trainingsdatensatzes",
            zh="训练数据集文件夹",
        ),
    )  # type: ignore


class LoadTrainingDatasetUnit(BaseUnit):
    """Load the dataset a model was trained on, under a key of its own.

    Deliberately not ``LoadDatasetUnit``: this dataset is not the one being
    transformed, it is a *reference* the prediction needs — the task decodes
    predicted class indexes against its labels, and its declared types become
    the schema of the saved result. Publishing it as ``dataset`` would collide
    with the dataset actually being predicted on, since ``PROVIDES`` is fixed
    per class and both would want the same key.

    Two outputs, with different rules on purpose: the live dataset is cached
    for the prediction step, while the types travel as a plain JSON-serializable
    mapping so the saving step never has to reopen the file. Nothing derived
    from the dataset *being predicted on* crosses this boundary.
    """

    SCHEMA = LoadTrainingDatasetSchema

    PROVIDES = ("train_dataset", "train_dataset_types")

    def execute(self, ctx: ExecutionContext) -> None:
        from pathlib import Path

        from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

        file_path = self.config["train_dataset_file_path"]

        try:
            train_dataset: "DashAIDataset" = load_dataset(
                str(Path(f"{file_path}/dataset/"))
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Cannot load training dataset from {file_path}/dataset/"
            ) from e

        ctx.put("train_dataset", train_dataset)
        ctx.put_ref(
            "train_dataset_types",
            {name: kind.to_string() for name, kind in train_dataset.types.items()},
        )
