import logging
from typing import Any, Dict, List

from DashAI.back.dataloaders.classes.dashai_dataset import (
    get_column_names_from_indexes,
)
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)


class SplitData(BaseJob):
    """Pipeline node that configures the data partition of the dataset.

    It resolves the input/output column names and stores the split ratios
    in the pipeline context.  The actual ``prepare_for_task`` and split
    operations are deferred to the *TaskAndModel* node which knows the
    chosen task.

    Parameters
    ----------
    input_columns : List[int]
        Column indices to use as input features.
    output_columns : List[int]
        Column indices to use as output targets.
    splits : Dict[str, float]
        Dictionary with ``train``, ``validation``, and ``test`` ratios
        (must sum to 1).
    """

    def __init__(
        self,
        input_columns: List[int],
        output_columns: List[int],
        splits: Dict[str, float],
    ) -> None:
        super().__init__(
            kwargs={
                "input_columns": input_columns,
                "output_columns": output_columns,
                "splits": splits,
            },
        )
        self.input_columns = input_columns
        self.output_columns = output_columns
        self.splits = splits

    # -- BaseJob interface ---------------------------------------------------

    def set_status_as_delivered(self) -> None:
        log.debug("SplitData executed successfully.")

    def set_status_as_error(self) -> None:
        log.error("SplitData encountered an error.")

    def get_job_name(self) -> str:
        return "SplitData"

    # -- Execution -----------------------------------------------------------

    async def run(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve column names and store split config in *context*.

        The following keys are added to ``context``:
        * ``input_columns`` – resolved column names
        * ``output_columns`` – resolved column names
        * ``input_columns_idx`` – original column indices
        * ``output_columns_idx`` – original column indices
        * ``split_ratios`` – the requested split ratios dict
        """
        dataset = context["dataset"]

        try:
            input_columns_names = get_column_names_from_indexes(
                dataset, self.input_columns
            )
            output_columns_names = get_column_names_from_indexes(
                dataset, self.output_columns
            )
        except Exception as e:
            log.exception(e)
            raise JobError(
                "Cannot resolve column names from the dataset.",
            ) from e

        # Populate context for downstream nodes
        context["input_columns"] = input_columns_names
        context["output_columns"] = output_columns_names
        context["input_columns_idx"] = self.input_columns
        context["output_columns_idx"] = self.output_columns
        context["split_ratios"] = self.splits

        return {
            "split_data": {
                "input_columns": self.input_columns,
                "output_columns": self.output_columns,
                "splits": self.splits,
            },
        }
