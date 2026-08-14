"""Unit that loads a stored dataset into memory."""

import logging
from typing import TYPE_CHECKING

from DashAI.back.core.schema_fields import BaseSchema, int_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.database.models import Dataset
from DashAI.back.job.base_job import JobError
from DashAI.back.units.base_unit import BaseUnit
from DashAI.back.units.context import ExecutionContext

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

log = logging.getLogger(__name__)


class LoadDatasetSchema(BaseSchema):
    dataset_id: schema_field(
        int_field(gt=0),
        placeholder=1,
        description=MultilingualString(
            en="Identifier of the stored dataset to load.",
            es="Identificador del conjunto de datos almacenado a cargar.",
            pt="Identificador do conjunto de dados armazenado a carregar.",
            de="Kennung des zu ladenden gespeicherten Datensatzes.",
            zh="要加载的已存储数据集的标识符。",
        ),
        alias=MultilingualString(
            en="Dataset",
            es="Conjunto de datos",
            pt="Conjunto de dados",
            de="Datensatz",
            zh="数据集",
        ),
    )  # type: ignore


class LoadDatasetUnit(BaseUnit):
    """Load a dataset from disk into the execution context.

    Resolves the dataset row to find where it is stored and materialises it, so
    downstream units receive a dataset instead of an identifier.
    """

    SCHEMA = LoadDatasetSchema

    PROVIDES = ("dataset",)

    def execute(self, ctx: ExecutionContext) -> None:
        from kink import di

        from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

        session_factory = di["session_factory"]
        dataset_id: int = self.config["dataset_id"]

        with session_factory() as db:
            dataset: Dataset = db.get(Dataset, dataset_id)
            if not dataset:
                raise JobError(f"Dataset {dataset_id} does not exist in DB.")
            file_path = dataset.file_path

        try:
            loaded_dataset: "DashAIDataset" = load_dataset(f"{file_path}/dataset")
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not load dataset from path {file_path}",
            ) from e

        ctx.put_ref("dataset_id", dataset_id)
        ctx.put("dataset", loaded_dataset)
