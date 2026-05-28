import logging
from typing import TYPE_CHECKING, Any

from kink import inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
)
from DashAI.back.job.base_job import BaseJob, JobError
from DashAI.back.models.RAG.document_loader import DocumentLoader
from DashAI.back.models.RAG.pipeline_repository import PipelineRepository
from DashAI.back.models.RAG.rag_models_factory import RAGModelsFactory
from DashAI.back.models.RAG.RAG_pipeline import (
    RAGPipeline,
    RAGPipelineConfig,
)
from DashAI.back.tasks.RAG_task import RAGTask

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class RAGJob(BaseJob):
    """RAGJob handles the full RAG pipeline lifecycle as a background job."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered."""
        generative_process_id: int = self.kwargs["generative_process_id"]

        with session_factory() as db:
            process: GenerativeProcess = db.get(
                GenerativeProcess, generative_process_id
            )
            if not process:
                raise JobError(
                    f"Generative process {generative_process_id} does not exist in DB."
                )
            try:
                process.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Internal database error") from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as error."""
        generative_process_id: int = self.kwargs.get("generative_process_id")
        if generative_process_id is None:
            return

        with session_factory() as db:
            process: GenerativeProcess = db.get(
                GenerativeProcess, generative_process_id
            )
            if not process:
                return
            try:
                process.set_status_as_error()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        generative_process_id = self.kwargs.get("generative_process_id")
        if not generative_process_id:
            return "RAG Process"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                process: GenerativeProcess = db.get(
                    GenerativeProcess, generative_process_id
                )
                if process:
                    session: GenerativeSession = db.get(
                        GenerativeSession, process.session_id
                    )
                    if session and session.name:
                        return f"RAG: {session.name}"
                    return f"RAG Process #{generative_process_id}"
        except Exception as e:
            log.exception(f"Error getting job name: {e}")

        return f"RAG Process #{generative_process_id}"

    @inject
    def run(self) -> None:
        import gc

        import torch
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        model = None
        generative_process = None
        # NOTE: The DB session spans the entire job lifecycle including LLM
        # inference, which risks connection timeouts for long-running
        # generations. No obvious solution yet.
        with session_factory() as db:
            try:
                generative_process_id: int = self.kwargs["generative_process_id"]

                try:
                    generative_process: GenerativeProcess = db.get(
                        GenerativeProcess, generative_process_id
                    )
                    if not generative_process:
                        raise JobError(
                            f"Generative process {generative_process_id} "
                            "not found in DB."
                        )
                except Exception as e:
                    log.exception(e)
                    if generative_process:
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
                    pipeline_config = RAGPipelineConfig.from_kwargs(
                        db=db,
                        component_registry=component_registry,
                        session_id=generative_session.id,
                        env_rag_path=config["RAG_PATH"],
                        **generative_session.parameters,
                    )
                    models = RAGModelsFactory(
                        db,
                        component_registry,
                        config["RAG_PATH"],
                    )
                    repo = PipelineRepository(db)
                    doc_loader = DocumentLoader(db)
                    model: RAGPipeline = RAGPipeline(
                        pipeline_config,
                        models,
                        repo,
                        doc_loader,
                    )
                except Exception as e:
                    log.exception(e)
                    generative_process.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Error instantiating RAG pipeline with given parameters."
                    ) from e

                input_data = generative_process.input

                try:
                    task = RAGTask()
                except Exception as e:
                    log.exception(e)
                    generative_process.set_status_as_error()
                    db.commit()
                    raise JobError("Error instantiating RAG task.") from e

                try:
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
                    raise JobError(
                        "Failed to update process status in database."
                    ) from e

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
                    raise JobError("Error during RAG model generation.") from e

                try:
                    output = task.process_output(
                        output, images_path=config["IMAGES_PATH"]
                    )
                    outputs_for_database = []
                    for o in output:
                        if not isinstance(o, tuple) or len(o) != 2:
                            raise JobError(
                                "Output from task must be a list of "
                                "tuples (data, type)."
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

                    db.refresh(generative_process)
                    generative_process.set_status_as_finished()
                    db.commit()
                except Exception as e:
                    log.exception(e)
                    generative_process.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Error processing and saving RAG generation output."
                    ) from e

            finally:
                if model:
                    del model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()
