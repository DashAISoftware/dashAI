import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, Union

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.generative_session_params import (
    GenerativeSessionParams,
)
from DashAI.back.dependencies.database.models import (
    Document,
    GenerativeProcess,
    GenerativeSession,
    GenerativeSessionParameterHistory,
    ProcessData,
    RAGChunkingModel,
    RAGDenseRetriever,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGPrompt,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.tasks.RAG_task import RAGTask

COMPOSITE_RETRIEVER_NAMES: Final = frozenset(
    {"SequentialRetriever", "ParallelRetriever"}
)

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry import ComponentRegistry


router = APIRouter()
log = logging.getLogger(__name__)


def _delete_path(path_value: str | None) -> None:
    if not path_value:
        return
    path = Path(path_value)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def _other_sessions_with_same_config(
    db,
    session_id: int,
    expected_parameters: dict,
    *,
    keys: tuple[str, ...],
) -> bool:
    """Return True when any other session matches all keys in `keys`.

    This avoids generator/list comprehensions for clarity.
    """
    other_sessions = (
        db.query(GenerativeSession).filter(GenerativeSession.id != session_id).all()
    )

    for other_session in other_sessions:
        other_parameters = other_session.parameters or {}
        all_keys_match = True
        for key in keys:
            if other_parameters.get(key) != expected_parameters.get(key):
                all_keys_match = False
                break
        if all_keys_match:
            return True

    return False


def _cleanup_orphaned_rag_resources(
    db,
    session_id: int,
    old_parameters: dict,
    new_parameters: dict | None = None,
) -> None:
    if not old_parameters:
        return

    def _component_changed(key: str) -> bool:
        if new_parameters is None:
            return True
        return old_parameters.get(key) != new_parameters.get(key)

    documents_ids = old_parameters.get("documents") or []
    documents_ids = sorted(documents_ids)

    # ── Retriever cleanup MUST run BEFORE chunking cleanup ──────────
    # _cleanup_unit_retriever queries RAGChunkingModel to obtain
    # chunking_model_id. If chunking models are deleted first, the
    # query returns None and retriever rows are silently skipped.
    # ─────────────────────────────────────────────────────────────────
    retriever_model_params = old_parameters.get("retriever_model")
    if not retriever_model_params:
        retriever_model_params = {}

    retriever_component_name = retriever_model_params.get("component", "")

    should_cleanup_retriever = (
        bool(retriever_model_params)
        and _component_changed("retriever_model")
        and not _other_sessions_with_same_config(
            db,
            session_id,
            old_parameters,
            keys=("documents", "chunking_model", "retriever_model"),
        )
    )

    if should_cleanup_retriever:
        if retriever_component_name in COMPOSITE_RETRIEVER_NAMES:
            _cleanup_composite_retriever(db, old_parameters, documents_ids, session_id)
        else:
            _cleanup_unit_retriever(
                db, old_parameters, documents_ids, retriever_model_params, session_id
            )

    # ── Chunking model cleanup (AFTER retriever) ──────────────────────
    chunking_model_params = old_parameters.get("chunking_model")
    if not chunking_model_params:
        chunking_model_params = {}

    should_cleanup_chunking = (
        bool(chunking_model_params)
        and _component_changed("chunking_model")
        and not _other_sessions_with_same_config(
            db, session_id, old_parameters, keys=("documents", "chunking_model")
        )
    )

    if should_cleanup_chunking:
        chunking_models = (
            db.query(RAGChunkingModel)
            .filter(
                RAGChunkingModel.class_name == chunking_model_params.get("component"),
                RAGChunkingModel.parameters == chunking_model_params.get("params"),
            )
            .all()
        )
        for chunking_model in chunking_models:
            db.delete(chunking_model)


def _find_pipeline_id(db, session_id: int) -> int | None:
    pipeline = db.query(RAGPipeline).filter_by(session_id=session_id).first()
    return pipeline.id if pipeline else None


def _cleanup_composite_retriever(
    db,
    old_parameters,
    documents_ids,
    session_id,
) -> None:
    pipeline_id = _find_pipeline_id(db, session_id)
    if pipeline_id is None:
        return

    retriever_component_name = old_parameters.get("retriever_model", {}).get(
        "component"
    )

    composite_bridges = (
        db.query(RAGRetriever)
        .filter(
            RAGRetriever.pipeline_id == pipeline_id,
            RAGRetriever.class_name == retriever_component_name,
        )
        .all()
    )

    for bridge in composite_bridges:
        child_links = (
            db.query(RAGRetrieverChild)
            .filter_by(parent_id=bridge.id)
            .order_by(RAGRetrieverChild.child_order)
            .all()
        )
        for link in child_links:
            child_bridge = db.query(RAGRetriever).get(link.child_id)
            if child_bridge is None:
                continue
            if child_bridge.sparse_detail:
                _delete_path(child_bridge.sparse_detail.storage_folder)
                db.delete(child_bridge.sparse_detail)
            elif child_bridge.dense_detail:
                db.delete(child_bridge.dense_detail)
        db.delete(bridge)


def _cleanup_unit_retriever(
    db,
    old_parameters,
    documents_ids,
    retriever_model_params,
    session_id,
) -> None:
    # Previously queried non-existent columns (chunking_model_id, document_ids)
    # on RAGDenseRetriever/RAGSparseRetriever. Fixed after schema refactor:
    # trace through the pipeline chain to obtain the valid chunk_set_id column.
    retriever_params = retriever_model_params.get("params", {})

    pipeline_id = _find_pipeline_id(db, session_id)
    if pipeline_id is None:
        return

    bridge = (
        db.query(RAGRetriever)
        .filter(
            RAGRetriever.pipeline_id == pipeline_id,
            RAGRetriever.class_name == retriever_model_params.get("component"),
        )
        .first()
    )
    if bridge is None:
        return

    if "encoding_model" in retriever_params:
        dense_retriever = (
            db.query(RAGDenseRetriever)
            .filter(
                RAGDenseRetriever.bridge_id == bridge.id,
                RAGDenseRetriever.class_name == retriever_model_params.get("component"),
                RAGDenseRetriever.parameters == retriever_params,
            )
            .first()
        )
        if dense_retriever is None:
            return

        chunk_set_id = dense_retriever.chunk_set_id
        embedding_model_id = dense_retriever.embedding_model_id

        embedding_matrices = (
            db.query(RAGEmbeddingMatrix)
            .filter(
                RAGEmbeddingMatrix.chunk_set_id == chunk_set_id,
                RAGEmbeddingMatrix.embedding_model_id == embedding_model_id,
                RAGEmbeddingMatrix.document_id.in_(documents_ids),
            )
            .all()
        )

        matrix_ids = []
        for matrix in embedding_matrices:
            _delete_path(matrix.storage_folder)
            matrix_ids.append(matrix.id)

        if matrix_ids:
            db.query(RAGEmbeddingMatrix).filter(
                RAGEmbeddingMatrix.id.in_(matrix_ids)
            ).delete(synchronize_session=False)

        embedding_model = db.query(RAGEmbeddingModel).get(embedding_model_id)
        if embedding_model is not None:
            db.delete(embedding_model)

        db.delete(dense_retriever)
        db.delete(bridge)
    else:
        sparse_retriever = (
            db.query(RAGSparseRetriever)
            .filter(
                RAGSparseRetriever.bridge_id == bridge.id,
                RAGSparseRetriever.class_name
                == retriever_model_params.get("component"),
                RAGSparseRetriever.parameters == retriever_params,
            )
            .first()
        )
        if sparse_retriever is None:
            return

        _delete_path(sparse_retriever.storage_folder)
        db.delete(sparse_retriever)
        db.delete(bridge)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_generative_session(
    params: GenerativeSessionParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Create a new generative session and log the initial parameters in the history."""
    from DashAI.back.models.base_generative_model import BaseGenerativeModel
    from DashAI.back.tasks.base_generative_task import BaseGenerativeTask

    with session_factory() as db:
        try:
            # Check if the model is registered
            try:
                model_class = component_registry[params.model_name]["class"]
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {params.model_name} is not registered.",
                ) from e

            # Check if the model is a subclass of GenerativeModel
            if not issubclass(model_class, BaseGenerativeModel):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model {params.model_name} is not a valid "
                    f"generative model.",
                )

            # Check if the task is registered
            try:
                task_class = component_registry[params.task_name]["class"]
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task {params.task_name} is not registered.",
                ) from e

            # RAG Task specific handling
            # Frontend will send the ids of the documents to be used in the
            # RAG session but RAG pipeline expects the documents paths of the
            # backend-stored documents
            if task_class == RAGTask:
                try:
                    assert params.parameters["documents"]
                    assert isinstance(params.parameters["documents"], list)
                    assert len(params.parameters["documents"]) > 0

                except (AssertionError, KeyError) as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="RAG Task requires a non-empty list of document IDs.",
                    ) from e

                documents_ids = []
                for doc_id in params.parameters["documents"]:
                    document = db.get(Document, doc_id)
                    if not document:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Document with ID {doc_id} does not exist.",
                        )
                    documents_ids.append(document.id)

                params.parameters["documents"] = documents_ids
            # Continue with the session creation

            # Normalise frontend properties wrapper and validate
            from DashAI.back.core.schema_fields.utils import normalize_payload

            params.parameters = normalize_payload(params.parameters)
            try:
                model_class.SCHEMA.model_validate(params.parameters)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid parameters for model {params.model_name}: {e}",
                ) from e

            # Check if the task is a subclass of BaseGenerativeTask
            if not issubclass(task_class, BaseGenerativeTask):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Task {params.task_name} is not a valid generative task.",
                )

            session = GenerativeSession(
                model_name=params.model_name,
                task_name=params.task_name,
                parameters=params.parameters,
                name=params.name,
                description=params.description,
            )
            db.add(session)
            try:
                db.commit()
            except exc.IntegrityError as e:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Generative session with name '{params.name}' already exists."
                    ),
                ) from e
            db.refresh(session)

            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=session.parameters,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)
            db.commit()

            return {
                "id": session.id,
                "model_name": session.model_name,
                "task_name": session.task_name,
                "parameters": session.parameters,
                "name": session.name,
                "description": session.description,
                "created": session.created,
                "last_modified": session.last_modified,
                "display_name": component_registry[session.task_name]["display_name"],
            }
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{session_id}", status_code=status.HTTP_200_OK)
async def get_generative_session(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    dict
        A dictionary with the generative session on the database

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(f"Generative session {session_id} does not exist in DB."),
                )
            return session
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_generative_sessions(
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Get all generative sessions ordered by creation date.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with all generative sessions on the database,
        ordered by creation date.

    Raises
    ------
    HTTPException
        If there's an internal database error.
    """

    with session_factory() as db:
        try:
            sessions = (
                db.query(GenerativeSession)
                .order_by(GenerativeSession.created.asc())
                .all()
            )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        session_list = []
        for session in sessions:
            session_list.append(
                {
                    "id": session.id,
                    "task_name": session.task_name,
                    "model_name": session.model_name,
                    "parameters": session.parameters,
                    "name": session.name,
                    "description": session.description,
                    "created": session.created,
                    "last_modified": session.last_modified,
                }
            )
        return session_list


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generative_session(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to delete.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            old_parameters = dict(session.parameters or {})

            # Delete all the processes associated with the session
            processes = (
                db.query(GenerativeProcess)
                .filter(GenerativeProcess.session_id == session_id)
                .all()
            )
            # Delete all the process data associated with the processes
            for process in processes:
                process_data = (
                    db.query(ProcessData)
                    .filter(ProcessData.process_id == process.id)
                    .all()
                )
                for data in process_data:
                    db.delete(data)
            # Delete the processes
            for process in processes:
                db.delete(process)

            # Delete the session parameter history entries
            parameters_history = (
                db.query(GenerativeSessionParameterHistory)
                .filter(GenerativeSessionParameterHistory.session_id == session_id)
                .all()
            )
            for entry in parameters_history:
                db.delete(entry)
            # Finally, delete the session itself
            db.delete(session)
            _cleanup_orphaned_rag_resources(db, session_id, old_parameters)
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


@router.patch("/{session_id}", status_code=status.HTTP_200_OK)
async def update_generative_session(
    session_id: int,
    name: Union[str, None] = None,
    description: Union[str, None] = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Update the generative session associated with the provided ID.

    Parameters
    ----------
    session_id : int
        ID of the generative session to update.
    name : Union[str, None], optional
        New name for the session.
    description : Union[str, None], optional
        New description for the session.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Dict
        A dictionary containing the updated generative session record.

    Raises
    ------
    HTTPException
        If the session does not exist, name is invalid, or name already exists.
    """
    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generative session not found",
                )

            # Validate name if provided
            if name is not None:
                if not name or not name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Name cannot be empty",
                    )

                new_name = name.strip()

                # Check if name is different from current name
                if new_name != session.name:
                    # Check if name already exists
                    exists = db.execute(
                        select(GenerativeSession.id).where(
                            GenerativeSession.name == new_name,
                            GenerativeSession.id != session_id,
                        )
                    ).scalar()
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Generative session name already exists",
                        )
                    setattr(session, "name", new_name)

            if description is not None:
                setattr(session, "description", description)

            if name is not None or description is not None:
                session.last_modified = datetime.now()
                db.commit()
                db.refresh(session)
                return session
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
                detail="Generative session name already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.put("/{session_id}/parameters", status_code=status.HTTP_200_OK)
async def update_generative_session_params(
    session_id: int,
    new_params: dict,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Update the parameters of a generative session and log the change.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to update.
    new_params : dict
        The new parameters to set for the generative session.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.

    Returns
    -------
    dict
        A dictionary with the updated generative session.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            old_parameters = dict(session.parameters or {})
            updated_parameters = {**old_parameters, **new_params}

            if "prompt_id" in updated_parameters:
                if "prompt" not in updated_parameters:
                    prompt_db = db.get(RAGPrompt, updated_parameters["prompt_id"])
                    if prompt_db:
                        raw_params = dict(prompt_db.parameters or {})
                        prompt_params = {
                            "template": raw_params.get(
                                "template",
                                raw_params.get("templates", {}).get("en", ""),
                            ),
                        }
                        if "language" in raw_params:
                            prompt_params["language"] = raw_params["language"]
                        updated_parameters["prompt"] = {
                            "component": prompt_db.class_name,
                            "params": prompt_params,
                        }
                del updated_parameters["prompt_id"]

            try:
                task_class = component_registry[session.task_name]["class"]
            except KeyError:
                task_class = None

            if task_class is not None and task_class == RAGTask:
                from DashAI.back.models.RAG.RAG_pipeline import RAGPipeline

                try:
                    RAGPipeline.SCHEMA.model_validate(updated_parameters)
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid parameters for RAG session {session_id}: {e}",
                    ) from e

            session_params_entry = GenerativeSessionParameterHistory(
                session_id=session.id,
                parameters=updated_parameters,
                modified_at=datetime.now(),
            )
            db.add(session_params_entry)

            session.parameters = updated_parameters
            session.last_modified = datetime.now()

            _cleanup_orphaned_rag_resources(
                db, session_id, old_parameters, updated_parameters
            )
            db.commit()
            db.refresh(session)

            return {"id": session.id, "parameters": session.parameters}
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/{session_id}/parameters-history", status_code=status.HTTP_200_OK)
async def get_generative_session_parameters_history(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """
    Get all parameter history entries for a generative session.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve the parameter history for.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.

    Returns
    -------
    list
        A list of dictionaries with all parameter history entries for the session.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """
    with session_factory() as db:
        try:
            # Check if the generative session exists
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            # Get the session parameter history
            parameters_history = (
                db.query(GenerativeSessionParameterHistory)
                .filter(GenerativeSessionParameterHistory.session_id == session_id)
                .order_by(GenerativeSessionParameterHistory.modified_at.asc())
                .all()
            )

            # Convert the objects to dictionaries (explicit loop for clarity)
            history_list = []
            for entry in parameters_history:
                history_list.append(
                    {
                        "id": entry.id,
                        "session_id": entry.session_id,
                        "parameters": entry.parameters,
                        "modified_at": entry.modified_at,
                    }
                )
            return history_list
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.get("/parameters-history/{session_id}", status_code=status.HTTP_200_OK)
async def get_parameter_history_entry(
    session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """
    Get history entry for a generative session by its ID.

    Parameters
    ----------
    session_id : int
        The ID of the generative session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    list
        A list of dictionaries with the parameter history entries for the session.

    Raises
    ------
    HTTPException
        If the generative session does not exist or if there's an internal
        database error.
    """

    with session_factory() as db:
        try:
            # Check if the generative session exists
            session = db.get(GenerativeSession, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Generative session {session_id} does not exist in DB.",
                )

            # Get the parameter history entry for the session
            parameters_history = (
                db.query(GenerativeSessionParameterHistory)
                .filter(GenerativeSessionParameterHistory.session_id == session_id)
                .order_by(GenerativeSessionParameterHistory.modified_at.asc())
                .all()
            )

            params_history_dicts = []
            for p in parameters_history:
                params_history_dicts.append(dict(p.__dict__))

            events = []
            if not params_history_dicts:
                return []

            prev_params = params_history_dicts[0]["parameters"]

            for i in range(1, len(params_history_dicts)):
                curr = params_history_dicts[i]
                curr_params = curr["parameters"]
                changes = []

                for key in curr_params:
                    old_val = prev_params.get(key)
                    new_val = curr_params[key]
                    if old_val != new_val:
                        changes.append(
                            {
                                "parameter": key,
                                "oldValue": old_val,
                                "newValue": new_val,
                            }
                        )

                events.append(
                    {
                        "id": curr["id"],
                        "timestamp": curr["modified_at"],
                        "changes": changes,
                    }
                )
                prev_params = curr_params

            return events

        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
