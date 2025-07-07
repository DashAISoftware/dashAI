import gc
import logging
from typing import Any

import torch
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
)
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.base_generative_model import BaseGenerativeModel
from DashAI.back.tasks import BaseGenerativeTask

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
    async def run(
        self,
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
        config=lambda di: di["config"],
    ) -> None:
        model = None
        generative_process = None
        try:
            generative_process_id: int = self.kwargs["generative_process_id"]
            db: Session = self.kwargs["db"]

            try:
                generative_process: GenerativeProcess = db.get(
                    GenerativeProcess, generative_process_id
                )
                if not generative_process:
                    raise JobError(
                        f"Generative process {generative_process_id} not found in DB."
                    )
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error retrieving generative process.") from e

            try:
                generative_session: GenerativeSession = db.get(
                    GenerativeSession, generative_process.session_id
                )
                if not generative_session:
                    raise JobError(
                        f"Session {generative_process.session_id} not found in DB."
                    )
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error retrieving generative session.") from e

            try:
                model_class = component_registry[generative_session.model_name]["class"]
                params = generative_session.parameters
                model: BaseGenerativeModel = model_class(**params)
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(
                    "Error instantiating model with given parameters."
                ) from e

            input_data = generative_process.input

            try:
                task_class = component_registry[generative_session.task_name]["class"]
                task: BaseGenerativeTask = task_class()
            except KeyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError(
                    f"Task '{generative_session.task_name}' not found in registry."
                ) from e
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error instantiating task.") from e

            try:
                use_history = getattr(task_class, "USE_HISTORY", False)
                if use_history:
                    history = [
                        (proc.input[0].data, proc.output[0].data)
                        for proc in db.query(GenerativeProcess)
                        .filter(GenerativeProcess.session_id == generative_session.id)
                        .filter(GenerativeProcess.status == "FINISHED")
                        .all()
                    ]
                    input_data = task.prepare_for_task(
                        input_data,
                        history=history,
                    )
                else:
                    input_data = task.prepare_for_task(input_data)
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error preparing task with history.") from e

            try:
                generative_process.set_status_as_started()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Failed to update process status in database.") from e

            try:
                output: Any = model.generate(input_data)
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.add(
                    ProcessData(
                        data=f"Error details: {str(e)}",
                        data_type="str",
                        process_id=generative_process.id,
                        is_input=False,
                    )
                )
                db.commit()
                raise JobError("Error during model generation.") from e

            try:
                output: Any = task.process_output(
                    output, images_path=config["IMAGES_PATH"]
                )
                outputs_for_database = []
                for o in output:
                    if not isinstance(o, tuple) or len(o) != 2:
                        raise JobError(
                            "Output from task must be a list of tuples (data, type)."
                        )
                    output_data, output_type = o
                    process_data = ProcessData(
                        data=output_data,
                        data_type=output_type,
                        process_id=generative_process.id,
                        is_input=False,
                    )
                    outputs_for_database.append(process_data)

                db.add_all(outputs_for_database)
                db.commit()

                # Update the generative process with the output
                db.refresh(generative_process)
                generative_process.set_status_as_finished()
                db.commit()
            except Exception as e:
                log.exception(e)
                generative_process.set_status_as_error()
                db.commit()
                raise JobError("Error processing and saving generation output.") from e

        finally:
            if model:
                del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
