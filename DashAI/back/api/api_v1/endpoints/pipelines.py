import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from kink import di, inject
from sqlalchemy import exc
from sqlalchemy.orm.session import sessionmaker

from DashAI.back.api.api_v0.endpoints.session_class import Session
from DashAI.back.config import DefaultSettings
from DashAI.back.dependencies.database.models import Pipeline
from DashAI.back.api.api_v1.schemas.pipelines_params import (
    PipelineCreateParams,
    PipelineUpdateParams,
)
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.pipeline.validator.pipeline_validator import PipelineValidator
from DashAI.back.pipeline.validator.validator import VALIDATOR_MAP

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

@router.get("/nodes")
async def get_nodes():
    try:
        json_path = Path(__file__).resolve().parents[3] / "pipeline" / "nodes.json"
        with open(json_path, "r") as f:
            nodes = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load node definitions",
        ) from e

    return nodes

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
    with session_factory() as db:
        try:
            pipeline = db.get(Pipeline, pipeline_id)
            if not pipeline:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pipeline not found",
                )
            
            pipeline.exploration = None
            pipeline.train = None
            pipeline.prediction = None

            steps_dict = [step.model_dump() if hasattr(step, "model_dump") else step for step in params.steps or []]

            pipeline.name = params.name or pipeline.name
            pipeline.steps = steps_dict or pipeline.steps
            pipeline.edges = params.edges or pipeline.edges

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

@router.post("/validate_pipeline")
@inject
async def validate_pipeline(
    request: Request,
):
    """Validate a pipeline configuration."""
    payload = await request.json()
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])

    validator = PipelineValidator(nodes, edges)
    return validator.validate()

@router.get("/{pipeline_id}/dataexploration/results/")
@inject
async def get_pipeline_dataexploration_results(
    pipeline_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
):
    """Get results for all Data Exploration steps of a pipeline."""
    db: Session = session_factory()

    try:
        pipeline = db.get(Pipeline, pipeline_id)
        if not pipeline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline with id {pipeline_id} not found",
            )
    except exc.SQLAlchemyError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving pipeline from the database",
        ) from e

    dataexploration = pipeline.exploration
    if not dataexploration or not isinstance(dataexploration, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline has no valid Data Exploration step",
        )

    results = {}

    for exploration_id, exploration_info in dataexploration.items():
        exploration_type = exploration_info["exploration_type"]
        exploration_path = exploration_info["path"]
        parameters = exploration_info.get("parameters", {})
        name = exploration_info.get("name")

        try:
            explorer_component_class = component_registry[exploration_type]["class"]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exploration type '{exploration_type}' not found in registry",
            )

        try:
            explorer_instance: BaseExplorer = explorer_component_class(**parameters)
            result = explorer_instance.get_results(
                exploration_path=exploration_path,
                options={},
            )
            results[exploration_id] = {
                "exploration_type": exploration_type,
                "results": result,
                "name": name,
            }
        except Exception as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error while getting results for '{exploration_type}'",
            ) from e

    return results
