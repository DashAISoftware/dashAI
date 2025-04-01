import logging
from typing import Any

from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.tasks import GenerativeTask

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class GenerativeJob(BaseJob):
    """GenerativeJob class to infer with generative models ."""

    def set_status_as_delivered(self) -> None:
        """Set the status of the job as delivered."""
        generative_process_id: int = self.kwargs["generative_process_id"]
        db: Session = self.kwargs["db"]

        process: GenerativeProcess = db.get(GenerativeProcess, generative_process_id)
        if not process:
            raise JobError(
                f"Generative process {generative_process_id} does not exist in DB."
            )
        try:
            process.set_status_as_delivered()
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise JobError(
                "Internal database error",
            ) from e

    @inject
    def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
        config=lambda di: di["config"],
    ) -> None:
        generative_process_id: int = self.kwargs["generative_process_id"]
        db: Session = self.kwargs["db"]

        generative_process: GenerativeProcess = db.get(
            GenerativeProcess, generative_process_id
        )

        generative_session: GenerativeSession = db.get(
            GenerativeSession, generative_process.session_id
        )

        model_class = component_registry[generative_session.model_name]["class"]
        params = generative_session.parameters

        try:
            model: BaseGenerativeModel = model_class(**params)
        except TypeError as e:
            print(e)
            logging.error(e)

        input_data = generative_process.input

        # Start the generation process
        generative_process.set_status_as_started()
        db.commit()

        # Generate
        output: Any = model.generate(input_data)

        # Process output and store it
        task: GenerativeTask = component_registry[generative_model.task_name]["class"]()
        output: Any = task.process_output(output, config["LOCAL_PATH"])
        generative_process.output = output

        # Finish the generation process
        generative_process.set_status_as_finished()
        db.commit()
