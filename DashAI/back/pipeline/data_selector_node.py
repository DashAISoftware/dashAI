import logging
import pathlib
from typing import Any, Dict

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset, load_dataset
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)


class DataSelector(BaseJob):
    """
    DataSelector node for loading datasets in pipelines.

    This node loads datasets from the specified path and makes them available
    for subsequent nodes in the pipeline.

    Parameters
    ----------
    kwargs : Dict[str, Any]
        A dictionary containing the parameters for the node, including:
        - name: Name of the dataset
        - file_path: Path to the dataset directory
    """

    TYPE: str = "DataSelector"

    def __init__(self, **kwargs) -> None:
        super().__init__(kwargs=kwargs)

    def set_status_as_delivered(self) -> None:
        log.debug("DataSelector executed successfully.")

    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        context["dataset_name"] = self.kwargs["name"]
        dataset_dir = pathlib.Path(self.kwargs["file_path"])
        data_path = dataset_dir / "dataset/data.arrow"

        if not data_path.exists():
            raise JobError(f"Dataset not found at {data_path}")

        try:
            loaded_dataset: DashAIDataset = load_dataset(f"{dataset_dir}/dataset")
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Can not load dataset from path {dataset_dir}",
            ) from e

        return {
            "dataset": loaded_dataset,
        }
