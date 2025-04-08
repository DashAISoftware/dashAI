import logging
from typing import Any, Dict
from DashAI.back.job.base_job import BaseJob

log = logging.getLogger(__name__)

class Metrics(BaseJob):
    def __init__(self, metrics: list) -> None:
        super().__init__(kwargs={"metrics": metrics})

    def set_status_as_delivered(self) -> None:
        log.info("Metrics calculation executed successfully.")

    def run(self, context: Dict[str, Any]) -> Any:
        print(f"Calculating metrics: {self.kwargs['metrics']}")
        return {"metrics": f"Calculated {', '.join(self.kwargs['metrics'])}"}