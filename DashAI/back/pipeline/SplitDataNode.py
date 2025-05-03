import json
import logging
import pathlib
from typing import Any, Dict, List

import pandas as pd
from datasets import Dataset
from DashAI.back.dataloaders.classes.dashai_dataset import prepare_for_experiment, select_columns, split_dataset
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)

class SplitData(BaseJob):
    def __init__(self, input_columns: List[str], output_columns: List[str], splits: Dict[str, float]) -> None:
        super().__init__(kwargs={"input_columns": input_columns, "output_columns": output_columns, "splits": splits})
        self.input_columns = input_columns
        self.output_columns = output_columns
        self.splits = splits

    def set_status_as_delivered(self) -> None:
        log.info("Split Data executed successfully.")

    def run(self, context: Dict[str, Any]) -> Any:

        try:
            prepared_dataset = prepare_for_experiment(
                    dataset=context["dataset"],
                    splits=self.splits,
                    output_columns=self.output_columns,
                )
            
            x, y = select_columns(
                    prepared_dataset,
                    self.input_columns,
                    self.output_columns,
                )
            
            x = split_dataset(x)
            y = split_dataset(y)

        except Exception as e:  
            log.error(f"Error during data splitting: {e}")
            raise JobError(f"Error during data splitting: {e}")

        return {
                "splits": {
                    "x": x,
                    "y": y,
                }
            }