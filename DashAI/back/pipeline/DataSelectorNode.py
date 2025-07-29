import logging
import pathlib
from typing import Any, Dict

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, load_dataset
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)

class DataSelector(BaseJob):
    TYPE = "DataSelector"

    def __init__(self, **kwargs) -> None:
        super().__init__(kwargs=kwargs)

    def set_status_as_delivered(self) -> None:
        log.info("DataSelector executed successfully.")

    async def run(self, context: Dict[str, Any]) -> Any:
        context["dataset_name"] = self.kwargs["name"]
        dataset_dir = pathlib.Path(self.kwargs["file_path"])
        data_path = dataset_dir / "dataset/data.arrow"

        if not data_path.exists():
            raise JobError("No se encontró el dataset en: {}".format(data_path))

        try:
            loaded_dataset: DashAIDataset = load_dataset(
                    f"{dataset_dir}/dataset"
                )
        except Exception as e:
                log.exception(e)
                raise JobError(
                    f"Can not load dataset from path {dataset_dir}",
                ) from e
            
        except Exception as e:
            log.error(f"Error al cargar el dataset: {e}")
            raise JobError(f"Error cargando el dataset: {e}")

        log.info(f"Dataset cargado correctamente desde: {dataset_dir}")

        return {
            "dataset": loaded_dataset,
        }
