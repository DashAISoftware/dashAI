import json
import logging
import os
import pathlib
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
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

@router.get("/predict_summary")
@inject
async def pipeline_predict_summary(
    pred_name: str = Query(...),
):
    settings = DefaultSettings()
    sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
    path = os.path.join(sqlite_local, "pipelines", "predictions", pred_name)
    summary = {}
    try:
        with open(path, "r") as f:
            try:
                data = json.load(f)["prediction"]
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400, detail="Invalid JSON format"
                ) from e

            summary["total_data_points"] = len(data)

            # Verificar si los datos son strings
            if isinstance(data[0], str):
                summary["data_type"] = "string"
            else:
                summary["data_type"] = "numeric"
                class_set = set(data)
                classes = [str(item) for item in class_set]
                summary["Unique_classes"] = len(classes)
                class_distribution = []
                id = 1
                for class_name in classes:
                    try:
                        occurrences = data.count(int(class_name))
                    except ValueError as e:
                        raise HTTPException(
                            status_code=400, detail=f"Invalid class value: {class_name}"
                        ) from e
                    distribution = {
                        "id": id,
                        "Class": class_name,
                        "Ocurrences": occurrences,
                        "Percentage": round(occurrences / len(data) * 100, 2),
                    }
                    id += 1
                    class_distribution.append(distribution)
                summary["class_distribution"] = class_distribution

            sample_data = [
                {"id": idx, "value": value} for idx, value in enumerate(data[:50], 1)
            ]
            summary["sample_data"] = sample_data
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Prediction not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return summary

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
                steps=steps_dict,
                edges=params.edges,
                exploration=None,
                train=None,
                prediction=None,
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
    settings = DefaultSettings(),
):
    """Update a specific pipeline."""
    with session_factory() as db:
        try:
            pipeline = db.get(Pipeline, pipeline_id)
            if not pipeline:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pipeline not found",
                )
            
            steps_dict = [step.model_dump() if hasattr(step, "model_dump") else step for step in params.steps or []]

            pipeline.name = params.name or pipeline.name
            pipeline.steps = steps_dict or pipeline.steps
            pipeline.edges = params.edges or pipeline.edges

            db.commit()
            db.refresh(pipeline)

            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            sqlite_db_path = pathlib.Path(sqlite_local, settings.SQLITE_DB_PATH)
            run_pipeline(sqlite_db_path, logging_level=logging.DEBUG, pipeline_id=pipeline_id)

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
