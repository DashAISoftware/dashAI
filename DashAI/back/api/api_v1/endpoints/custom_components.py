"""Custom component (in-app authoring) API."""

from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Any, Dict, List

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.custom_component_params import (
    BaseClassInfo,
    BaseClassSummary,
    CustomComponentCreate,
    CustomComponentResponse,
    CustomComponentUpdate,
    ValidationRequest,
    ValidationResponse,
)
from DashAI.back.custom_components.introspection import (
    describe_base,
    get_supported_base_classes,
)
from DashAI.back.custom_components.registry_bridge import (
    register_custom,
    unregister_custom,
)
from DashAI.back.custom_components.startup import (
    forget_custom_component,
    record_custom_component,
)
from DashAI.back.custom_components.validator import validate_source
from DashAI.back.dependencies.database.models import CustomComponent

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry import ComponentRegistry

logger = logging.getLogger(__name__)

router = APIRouter()


def _write_source_file(
    config: Dict[str, Any], component_id: int, class_name: str, source: str
) -> str:
    base_dir = pathlib.Path(config["CUSTOM_COMPONENTS_PATH"])
    base_dir.mkdir(parents=True, exist_ok=True)
    file_path = base_dir / f"{component_id}_{class_name}.py"
    file_path.write_text(source, encoding="utf-8")
    return str(file_path)


def _delete_source_file(path_str: str | None) -> None:
    if not path_str:
        return
    path = pathlib.Path(path_str)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            logger.exception("Failed to delete custom component file %s", path)


@router.get("/base-classes", response_model=List[BaseClassSummary])
async def list_base_classes() -> List[Dict[str, Any]]:
    """List base classes that can be extended via the editor."""
    return get_supported_base_classes()


@router.get("/base-classes/{name}", response_model=BaseClassInfo)
async def get_base_class(name: str) -> Dict[str, Any]:
    """Introspect a base class: abstract methods, attributes, starter skeleton."""
    try:
        return describe_base(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/validate", response_model=ValidationResponse)
async def validate_component(body: ValidationRequest) -> Dict[str, Any]:
    """Dry-run check: compile source, load class, verify inheritance + abstracts.

    Does NOT persist or register anything.
    """
    result = validate_source(
        source=body.source_code,
        class_name=body.class_name,
        base_class_name=body.base_class,
    )
    return result.to_dict()


@router.get("/", response_model=List[CustomComponentResponse])
@inject
async def list_custom_components(
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """List every stored custom component."""
    with session_factory() as db:
        rows = db.execute(select(CustomComponent)).scalars().all()
        return [CustomComponentResponse.model_validate(r) for r in rows]


@router.get("/{component_id}", response_model=CustomComponentResponse)
@inject
async def get_custom_component(
    component_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    with session_factory() as db:
        row = db.get(CustomComponent, component_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Custom component not found")
        return CustomComponentResponse.model_validate(row)


@router.post(
    "/",
    response_model=CustomComponentResponse,
    status_code=status.HTTP_201_CREATED,
)
@inject
async def create_custom_component(
    body: CustomComponentCreate,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Validate, persist, then register a custom component into the live registry."""
    result = validate_source(
        source=body.source_code,
        class_name=body.class_name,
        base_class_name=body.base_class,
    )
    if not result.ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": result.errors, "warnings": result.warnings},
        )

    if body.class_name in component_registry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Component '{body.class_name}' is already registered. "
                "Pick a different class name."
            ),
        )

    base_type = result.cls.TYPE  # set on the base class via __init_subclass
    with session_factory() as db:
        row = CustomComponent(
            class_name=body.class_name,
            base_type=base_type,
            base_class=body.base_class,
            source_code=body.source_code,
            description=body.description,
        )
        db.add(row)
        try:
            db.flush()
            row.file_path = _write_source_file(
                config, row.id, row.class_name, body.source_code
            )
            db.commit()
            db.refresh(row)
        except exc.SQLAlchemyError as e:
            db.rollback()
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        try:
            register_custom(result.cls, component_registry)
        except ValueError as e:
            db.delete(row)
            db.commit()
            _delete_source_file(row.file_path)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(e)
            ) from e

        record_custom_component(row)
        return CustomComponentResponse.model_validate(row)


@router.put("/{component_id}", response_model=CustomComponentResponse)
@inject
async def update_custom_component(
    component_id: int,
    body: CustomComponentUpdate,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
):
    """Edit an existing component: re-validate, re-write file, re-register."""
    with session_factory() as db:
        row = db.get(CustomComponent, component_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Custom component not found")

        new_source = (
            body.source_code if body.source_code is not None else row.source_code
        )
        new_class = body.class_name if body.class_name is not None else row.class_name
        new_base = body.base_class if body.base_class is not None else row.base_class

        result = validate_source(
            source=new_source, class_name=new_class, base_class_name=new_base
        )
        if not result.ok:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"errors": result.errors, "warnings": result.warnings},
            )

        old_class_name = row.class_name
        unregister_custom(row.class_name, component_registry)
        if new_class != row.class_name and new_class in component_registry:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Component '{new_class}' is already registered.",
            )

        row.class_name = new_class
        row.base_class = new_base
        row.base_type = result.cls.TYPE
        row.source_code = new_source
        if body.description is not None:
            row.description = body.description

        _delete_source_file(row.file_path)
        try:
            db.flush()
            row.file_path = _write_source_file(
                config, row.id, row.class_name, new_source
            )
            db.commit()
            db.refresh(row)
        except exc.SQLAlchemyError as e:
            db.rollback()
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

        register_custom(result.cls, component_registry)
        if old_class_name != row.class_name:
            forget_custom_component(old_class_name)
        record_custom_component(row)
        return CustomComponentResponse.model_validate(row)


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_custom_component(
    component_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> None:
    with session_factory() as db:
        row = db.get(CustomComponent, component_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Custom component not found")
        unregister_custom(row.class_name, component_registry)
        _delete_source_file(row.file_path)
        db.delete(row)
        db.commit()
        forget_custom_component(row.class_name)
