import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from fastapi import APIRouter, Depends, Form, HTTPException, status
from kink import di
from sqlalchemy import exc, select
from typing_extensions import Annotated

from DashAI.back.api.api_v1.schemas.agentic_conversation_params import (
    AgenticConfigurationParams,
    AgenticConversationParams,
    AgenticConversationUpdateParams,
    AgenticUpdateConfigurationParams,
)
from DashAI.back.dependencies.database.models import (
    AgenticConversationMessages,
    AgenticConversations,
    AgenticParameters,
    AgenticProcess,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

router = APIRouter()
log = logging.getLogger(__name__)


router = APIRouter()
log = logging.getLogger(__name__)


def _serialize_agentic_message(message: AgenticConversationMessages) -> Dict[str, Any]:
    """Convert an agentic conversation message into a JSON-serializable dictionary.

    Returns
    -------
    dict
        Dictionary containing the message identifier, text, associated process,
        and whether the message corresponds to user input.
    """
    return {
        "id": message.id,
        "text": message.text,
        "process_id": message.process_id,
        "is_input": message.is_input,
    }


def _serialize_agentic_process(process: AgenticProcess) -> Dict[str, Any]:
    """Convert an agentic process into a JSON-serializable dictionary.

    The serialized representation includes the process metadata together with
    its input and output messages.

    Returns
    -------
    dict
        Dictionary containing the process metadata and serialized input and
        output messages.
    """
    return {
        "id": process.id,
        "conversation_id": process.conversation_id,
        "start_time": process.start_time,
        "end_time": process.end_time,
        "status": process.status.value,
        "input": [_serialize_agentic_message(msg) for msg in process.input],
        "output": [_serialize_agentic_message(msg) for msg in process.output],
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_agentic_conversation(
    params: AgenticConversationParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Create a new agentic conversation
    Parameters
    ----------
    params: An instance of the AgenticConversations model containing the name and
    description of the conversation to be created.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary containing the details of the created agentic conversation.
    """

    with session_factory() as db:
        try:
            conversation = AgenticConversations(
                name=params.name, description=params.description
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)

            return {
                "id": conversation.id,
                "name": conversation.name,
                "description": conversation.description,
                "last_modified": conversation.last_modified,
                "created": conversation.created,
            }
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{conversation_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agentic_conversation(
    conversation_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete a agentic conversation by its ID.

    Parameters
    ----------
    conversation_id : int
        The ID of the agentic conversation to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If the agentic conversation does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            config = di["config"]
            conn = sqlite3.connect(
                str(config["SQLITE_DB_PATH"]), check_same_thread=False
            )
            checkpointer = SqliteSaver(conn)
            checkpointer.delete_thread(conversation_id)

            conversation = db.get(AgenticConversations, conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Agentic conversation {conversation_id} does not exist in DB."
                    ),
                )

            db.delete(conversation)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e
        finally:
            db.rollback()
            db.close()


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_conversations(
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get all agentic conversations ordered by creation date.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with all agentic conversations on the database,
        ordered by creation date.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            conversations = (
                db.query(AgenticConversations)
                .order_by(AgenticConversations.created.desc())
                .all()
            )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        conversation_list = []
        for conversation in conversations:
            conversation_list.append(
                {
                    "id": conversation.id,
                    "created": conversation.created,
                    "name": conversation.name,
                    "description": conversation.description,
                    "last_modified": conversation.last_modified,
                }
            )
        return conversation_list


@router.patch("/{conversation_id}/", status_code=status.HTTP_200_OK)
async def update_conversation(
    conversation_id: int,
    params: AgenticConversationUpdateParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Update the conversation associated with the provided ID.

    Parameters
    ----------
    conversation_id : int
        ID of the conversation to update.
    params : AgenticConversationUpdateParams
        Parameters for updating the conversation.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A dictionary containing the updated conversation record.

    Raises
    ------
    HTTPException
        If the conversation does not exist, name is invalid, or name already exists.
    """
    with session_factory() as db:
        try:
            conversation = db.get(AgenticConversations, conversation_id)
            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="The conversation has not been found in the database",
                )

            # Validate name if provided
            if params.name is not None:
                if not params.name or not params.name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Name cannot be empty",
                    )

                new_name = params.name.strip()

                # Check if name is different from current name
                if new_name != conversation.name:
                    # Check if name already exists
                    exists = db.execute(
                        select(AgenticConversations.id).where(
                            AgenticConversations.name == new_name,
                            AgenticConversations.id != conversation_id,
                        )
                    ).scalar()
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Conversation session name already exists",
                        )
                    setattr(conversation, "name", new_name)

            if params.description is not None:
                setattr(conversation, "description", params.description)

            if params.name is not None or params.description is not None:
                conversation.last_modified = datetime.now()
                db.commit()
                db.refresh(conversation)
                return conversation
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except HTTPException:
            raise
        except exc.IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation session name already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/conversation/{conversation_id}/", status_code=status.HTTP_200_OK)
async def get_messages_conversation_id(
    conversation_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get messages by conversation ID.

    Parameters
    ----------
    conversation_id : int
        The ID of the conversation to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the conversation data.

    Raises
    ------
    HTTPException
        If the conversation is not found or if there's an internal database error.
    """
    with session_factory() as db:
        try:
            processes = (
                db.query(AgenticProcess)
                .filter_by(conversation_id=conversation_id)
                .order_by(AgenticProcess.id.asc())
                .all()
            )

            return [_serialize_agentic_process(process) for process in processes]
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.post("/process/", status_code=status.HTTP_201_CREATED)
async def upload_agentic_process(
    conversation_id: Annotated[int, Form(...)],
    configuration_id: Annotated[int, Form(...)],
    input_data: Annotated[str, Form(...)],
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Create a new agentic process.

    Parameters
    ----------
    conversation_id : int
        The ID of the conversation to which this process belongs.
    configuration_id : int
        The ID of the configuration to execute the process with.
    input_data : str
        User message text used as process input.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the new agentic process on the database
        and the input/output data.

    Raises
    ------
    HTTPException
        If there's an internal database error or if the conversation ID does not
        exist.
    """
    with session_factory() as db:
        try:
            conversation = (
                db.query(AgenticConversations).filter_by(id=conversation_id).first()
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation with ID {conversation_id} does not exist.",
                )

            configuration = (
                db.query(AgenticParameters).filter_by(id=configuration_id).first()
            )
            if not configuration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Configuration with ID {configuration_id} does not exist.",
                )

            if not input_data or not input_data.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Input data cannot be empty.",
                )

            process = AgenticProcess(
                conversation_id=conversation_id,
            )
            db.add(process)
            db.commit()
            db.refresh(process)

            input_data = AgenticConversationMessages(
                text=input_data.strip(),
                is_input=True,
                process_id=process.id,
            )
            db.add(input_data)
            db.commit()
            db.refresh(process)

            return _serialize_agentic_process(process)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{process_id}", status_code=status.HTTP_200_OK)
async def get_agentic_process(
    process_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get an agentic process by its session ID.

    Parameters
    ----------
    process_id : str
        The ID of the agentic process to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the agentic process data.

    Raises
    ------
    HTTPException
        If the agentic process is not found or if there's an internal database error.
    """
    with session_factory() as db:
        try:
            process = db.get(AgenticProcess, process_id)
            if process is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agentic process with ID {process_id} does not exist.",
                )

            return _serialize_agentic_process(process)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agentic_process(
    process_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete an agentic process by its ID.

    Parameters
    ----------
    process_id : str
        The ID of the agentic process to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    None

    Raises
    ------
    HTTPException
        If the agentic process is not found or if there's an internal database error.
    """
    with session_factory() as db:
        try:
            process = db.get(AgenticProcess, process_id)
            if not process:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agentic process with ID {process_id} does not exist.",
                )

            db.delete(process)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.post("/configuration/")
async def upload_configuration_agent(
    params: AgenticConfigurationParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Create a new agentic configuration
    Parameters
    ----------
    params: An instance of the AgenticConfigurationParams model containing the
    configuration details.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary containing the details of the created agentic configuration.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    configuration = AgenticParameters(
        configuration_name=params.configuration_name,
        configuration_description=params.configuration_description,
        family_model_name=params.family_model_name,
        model_name=params.model_name,
        parameters=params.parameters,
        tools=params.tools,
    )
    with session_factory() as db:
        try:
            db.add(configuration)
            db.commit()
            db.refresh(configuration)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return configuration


@router.get("/configuration/", status_code=status.HTTP_200_OK)
async def get_configurations_agent(
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get all agentic configurations ordered by last modification date.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with all agentic configurations on the database,
        ordered by last modification date.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """
    with session_factory() as db:
        try:
            configurations = (
                db.query(AgenticParameters)
                .order_by(AgenticParameters.last_modified.desc())
                .all()
            )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        configuration_list = []
        for configuration in configurations:
            configuration_list.append(
                {
                    "id": configuration.id,
                    "created": configuration.created,
                    "name": configuration.configuration_name,
                    "description": configuration.configuration_description,
                    "last_modified": configuration.last_modified,
                }
            )
        return configuration_list


@router.get("/configuration/{configuration_id}", status_code=status.HTTP_200_OK)
async def get_configuration_agent_by_id(
    configuration_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Retrieve an agentic configuration by its identifier.

    Returns the complete persisted configuration, including the selected model
    family, model, parameters, and enabled tools. This endpoint is intended to
    populate the agent configuration editor.

    Parameters
    ----------
    configuration_id : int
        Identifier of the configuration to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        Factory used to create a SQLAlchemy session.

    Returns
    -------
    dict
        Dictionary containing the configuration metadata, selected model,
        parameters, and tools.

    Raises
    ------
    HTTPException
        If the configuration does not exist or an internal database error
        occurs.
    """
    with session_factory() as db:
        try:
            configuration = db.get(AgenticParameters, configuration_id)
            if configuration is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Agentic configuration {configuration_id} "
                        f"does not exist in DB."
                    ),
                )

            return {
                "id": configuration.id,
                "created": configuration.created,
                "last_modified": configuration.last_modified,
                "configuration_name": configuration.configuration_name,
                "configuration_description": configuration.configuration_description,
                "family_model_name": configuration.family_model_name,
                "model_name": configuration.model_name,
                "parameters": configuration.parameters,
                "tools": configuration.tools,
            }
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete(
    "/configuration/{configuration_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_configuration_agent(
    configuration_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete a agentic configuration by its ID.

    Parameters
    ----------
    configuration_id : int
        The ID of the agentic configuration to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If the agentic configuration does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            configuration = db.get(AgenticParameters, configuration_id)
            if not configuration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Agentic configuration {configuration_id} "
                        f"does not exist in DB."
                    ),
                )

            db.delete(configuration)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e
        finally:
            db.rollback()
            db.close()


@router.patch("/configuration/{configuration_id}", status_code=status.HTTP_200_OK)
async def update_configuration_agent(
    configuration_id: int,
    params: AgenticUpdateConfigurationParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Update the configuration associated with the provided ID.

    Parameters
    ----------
    configuration_id : int
        ID of the configuration to update.
    params : AgenticConfigurationParams
        Parameters for updating the configuration.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A dictionary containing the updated configuration record.

    Raises
    ------
    HTTPException
        If the configuration does not exist, name is invalid, or name already exists.
    """
    with session_factory() as db:
        try:
            configuration = db.get(AgenticParameters, configuration_id)
            if configuration is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="The configuration has not been found in the database",
                )

            # Validate name if provided
            if params.configuration_name is not None:
                if (
                    not params.configuration_name
                    or not params.configuration_name.strip()
                ):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Name cannot be empty",
                    )

                new_name = params.configuration_name.strip()

                # Check if name is different from current name
                if new_name != configuration.configuration_name:
                    # Check if name already exists
                    exists = db.execute(
                        select(AgenticParameters.id).where(
                            AgenticParameters.configuration_name == new_name,
                            AgenticParameters.id != configuration_id,
                        )
                    ).scalar()
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Configuration name already exists",
                        )
                    setattr(configuration, "configuration_name", new_name)
            if params.configuration_description is not None:
                new_description = params.configuration_description.strip()
                setattr(configuration, "configuration_description", new_description)

            if params.family_model_name is not None:
                setattr(configuration, "family_model_name", params.family_model_name)
            if params.model_name is not None:
                setattr(configuration, "model_name", params.model_name)
            if params.parameters is not None:
                setattr(configuration, "parameters", params.parameters)
            if params.tools is not None:
                setattr(configuration, "tools", params.tools)

            if (
                params.configuration_name is not None
                or params.configuration_description is not None
                or params.family_model_name is not None
                or params.model_name is not None
                or params.parameters is not None
                or params.tools is not None
            ):
                configuration.last_modified = datetime.now()
                db.commit()
                db.refresh(configuration)
                return configuration
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except HTTPException:
            raise
        except exc.IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Configuration name already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
