import logging
from typing import TYPE_CHECKING, Any

from kink import inject
from sqlalchemy import exc

from DashAI.back.dependencies.database.models import (
    AgenticConversationMessages,
    AgenticConversations,
    AgenticParameters,
    AgenticProcess,
)
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class AgenticJob(BaseJob):
    """AgenticJob class to do actions and answer queries ."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered."""
        agentic_process_id: int = self.kwargs["agentic_process_id"]

        with session_factory() as db:
            agenticProcess: AgenticProcess = db.get(AgenticProcess, agentic_process_id)
            if not agenticProcess:
                raise JobError(
                    f"Agentic process {agentic_process_id} does not exist in DB."
                )
            try:
                agenticProcess.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Internal database error",
                ) from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as error."""
        agentic_process_id: int = self.kwargs.get("agentic_process_id")
        if agentic_process_id is None:
            return

        with session_factory() as db:
            agenticProcess: AgenticProcess = db.get(AgenticProcess, agentic_process_id)
            if not agenticProcess:
                return

            try:
                agenticProcess.set_status_as_error()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        agentic_process_id = self.kwargs.get("agentic_process_id")
        if not agentic_process_id:
            return "Agentic Process"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                agenticProcess: AgenticProcess = db.get(
                    AgenticProcess, agentic_process_id
                )
                if agenticProcess:
                    conversation: AgenticConversations = db.get(
                        AgenticConversations, agenticProcess.conversation_id
                    )
                    if conversation and conversation.name:
                        return (
                            f"Agentic process "
                            f"'{agentic_process_id}' executed on conversation "
                            f"'{conversation.name}'"
                        )
        except Exception:
            return "Agentic Process"

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        # (Lazy imports removed to avoid duplicate and unused imports warnings)
        agent = None
        agentic_process = None
        params_process = None
        with session_factory() as db:
            try:
                agentic_process_id = self.kwargs["agentic_process_id"]
                configuration_id = self.kwargs["configuration_id"]

                try:
                    agentic_process: AgenticProcess = db.get(
                        AgenticProcess, agentic_process_id
                    )
                    if not agentic_process:
                        raise JobError(
                            f"Agentic process {agentic_process_id} not found in DB."
                        )
                except Exception as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.commit()
                    raise JobError("Error retrieving agentic process.") from e

                try:
                    agentic_conversation: AgenticConversations = db.get(
                        AgenticConversations, agentic_process.conversation_id
                    )
                    if not agentic_conversation:
                        raise JobError(
                            f"Conversation "
                            f"{agentic_process.conversation_id} not found in DB."
                        )
                except Exception as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.commit()
                    raise JobError("Error retrieving agentic Conversation.") from e
                try:
                    params_process: AgenticParameters = db.get(
                        AgenticParameters, configuration_id
                    )
                    if not params_process:
                        raise JobError(
                            f"Configuration {configuration_id} not found in DB."
                        )
                except Exception as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.commit()
                    raise JobError("Error retrieving agentic parameters.") from e

                try:
                    agent_class = component_registry[params_process.model_name]["class"]
                    params = params_process.parameters
                    selected_tools = params_process.tools
                    agent = agent_class(
                        **{
                            **params,
                            "conversation_id": agentic_conversation.id,
                            "selected_tools": selected_tools,
                        }
                    )
                except Exception as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Error instantiating agent with given parameters."
                    ) from e

                input_data = agentic_process.input
                try:
                    agentic_process.set_status_as_started()
                    db.commit()
                except exc.SQLAlchemyError as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.commit()
                    raise JobError(
                        "Failed to update agentic process status in database."
                    ) from e

                try:
                    output: Any = agent.generate(
                        [{"role": "user", "content": str(input_data[0].text)}]
                    )
                    if output is None or output == "":
                        output = "Error: The agent did not return any output."
                except Exception as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.add(
                        AgenticConversationMessages(
                            text=f"Error details: {str(e)}",
                            process_id=agentic_process.id,
                            is_input=False,
                        )
                    )
                    db.commit()
                    raise JobError("Error during agentic process.") from e

                try:
                    output_for_database = AgenticConversationMessages(
                        text=output,
                        process_id=agentic_process.id,
                        is_input=False,
                    )

                    db.add(output_for_database)
                    db.commit()

                    db.refresh(agentic_process)
                    agentic_process.set_status_as_finished()
                    db.commit()
                except Exception as e:
                    log.exception(e)
                    agentic_process.set_status_as_error()
                    db.commit()
                    raise JobError("Error processing and saving agentic output.") from e

            finally:
                # útil cuando se implemente un agente con llm local.
                if agent:
                    del agent
                # if torch.cuda.is_available():  # noqa: ERA001
                #     torch.cuda.empty_cache()   # noqa: ERA001
                # gc.collect()  # noqa: ERA001
