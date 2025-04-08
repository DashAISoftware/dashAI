import logging
import os
import pathlib
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from kink import di, inject
from sqlalchemy import exc
from sqlalchemy.orm.session import sessionmaker

from DashAI.back.config import DefaultSettings
from DashAI.back.dependencies.database.models import Pipeline
from DashAI.back.api.api_v1.schemas.pipelines_params import (
    PipelineCreateParams,
    PipelineUpdateParams,
)
from DashAI.back.job.pipeline_job import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
@inject
async def get_pipelines(
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Retrieve all pipelines."""
    logger.debug("Retrieving all pipelines.")
    with session_factory() as db:
        try:
            pipelines = db.query(Pipeline).all()
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return pipelines


@router.get("/{pipeline_id}")
@inject
async def get_pipeline(
    pipeline_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Retrieve a specific pipeline by ID."""
    logger.debug("Retrieving pipeline with id %s", pipeline_id)
    with session_factory() as db:
        try:
            pipeline = db.get(Pipeline, pipeline_id)
            if not pipeline:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pipeline not found",
                )
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return pipeline


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def create_pipeline(
    params: PipelineCreateParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Create a new pipeline."""
    logger.debug("Creating a new pipeline with params: %s", params)
    settings = DefaultSettings()
    with session_factory() as db:
        try:
            steps_dict = [step.model_dump() if hasattr(step, "model_dump") else step for step in params.steps or []]
                          
            new_pipeline = Pipeline(
                name=params.name,
                description=params.description,
                steps=steps_dict,
            )
            db.add(new_pipeline)
            db.commit()
            db.refresh(new_pipeline)

            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            sqlite_db_path = pathlib.Path(sqlite_local, settings.SQLITE_DB_PATH)
            run_pipeline(sqlite_db_path, logging_level=logging.DEBUG, pipeline_id=new_pipeline.id)

        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return new_pipeline

@router.put("/{pipeline_id}")
@inject
async def update_pipeline(
    pipeline_id: int,
    params: PipelineUpdateParams,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Update a specific pipeline."""
    logger.debug("Updating pipeline with id %s", pipeline_id)
    with session_factory() as db:
        try:
            pipeline = db.get(Pipeline, pipeline_id)
            if not pipeline:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pipeline not found",
                )

            pipeline.name = params.name or pipeline.name
            pipeline.description = params.description or pipeline.description
            pipeline.steps = params.steps or pipeline.steps

            db.commit()
            db.refresh(pipeline)
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return pipeline


@router.delete("/{pipeline_id}")
@inject
async def delete_pipeline(
    pipeline_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Delete a specific pipeline."""
    logger.debug("Deleting pipeline with id %s", pipeline_id)
    with session_factory() as db:
        try:
            pipeline = db.get(Pipeline, pipeline_id)
            if not pipeline:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pipeline not found",
                )

            db.delete(pipeline)
            db.commit()
        except exc.SQLAlchemyError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    return {"message": "Pipeline deleted successfully"}

from DashAI.back.pipeline.validator.validator import VALIDATOR_MAP
from fastapi import Request

@router.post("/validate_node")
@inject
async def validate_node(
    request: Request,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    """Validate a single node configuration."""
    payload = await request.json()
    node_type = payload.get("type")
    node_data = payload.get("config")

    validator_class = VALIDATOR_MAP.get(node_type)
    if not validator_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown node type: {node_type}",
        )

    with session_factory() as db:
        validator = validator_class(node_data, db)
        return validator.validate()
