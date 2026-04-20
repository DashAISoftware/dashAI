"""Custom component (in-app authoring) API."""

from __future__ import annotations

import inspect
import logging
import pathlib
import sys
from typing import TYPE_CHECKING, Any, Dict, List

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.custom_component_params import (
    BaseClassInfo,
    BaseClassSummary,
    ComponentSourceResponse,
    CustomComponentCreate,
    CustomComponentResponse,
    CustomComponentUpdate,
    ValidationRequest,
    ValidationResponse,
)
from DashAI.back.custom_components.introspection import (
    describe_base,
    get_supported_base_classes,
    resolve_base_class,
)
from DashAI.back.custom_components.originals import has_original
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


def _detect_base_class(cls: type) -> str | None:
    """Return the name of the first supported base class `cls` extends, if any."""
    from DashAI.back.custom_components.introspection import _SUPPORTED_BASES

    for base_name, info in _SUPPORTED_BASES.items():
        if info["class"] in cls.__mro__ and info["class"] is not cls:
            return base_name
    return None


def _read_module_source(cls: type) -> str:
    """Return the full source file that defines `cls`.

    Core and plugin components typically define their Pydantic schema class
    and all imports at module scope next to the component class. Returning
    only `inspect.getsource(cls)` strips those away and leaves the user with
    an uneditable snippet. Read the whole module instead so the editor shows
    everything the user needs to tweak.
    """
    module = sys.modules.get(cls.__module__)
    if module is not None:
        try:
            return inspect.getsource(module)
        except (OSError, TypeError):
            pass

    # Fallback: read the source file directly.
    try:
        path = inspect.getsourcefile(cls) or inspect.getfile(cls)
    except TypeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not locate source for '{cls.__name__}': {e}",
        ) from e
    if not path:
        raise HTTPException(
            status_code=500,
            detail=f"Could not locate source file for '{cls.__name__}'.",
        )
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read source for '{cls.__name__}': {e}",
        ) from e


def _classify_origin(cls: type) -> str:
    """Best-effort classification of a component's origin by module path."""
    module = cls.__module__ or ""
    if module.startswith("dashai_custom_"):
        return "custom"
    if module.startswith("DashAI."):
        return "core"
    return "plugin"


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


@router.get("/source/{class_name}", response_model=ComponentSourceResponse)
@inject
async def get_component_source(
    class_name: str,
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Return the source for any registered component (core, plugin, or custom).

    For components backed by a custom-component row we return that row's
    source; for core/plugin classes we fall back to `inspect.getsource`.
    """
    if class_name not in component_registry:
        raise HTTPException(
            status_code=404, detail=f"Component '{class_name}' not found."
        )
    cls = component_registry[class_name]["class"]

    # Is this component currently an override?
    with session_factory() as db:
        row = (
            db.execute(
                select(CustomComponent).where(CustomComponent.class_name == class_name)
            )
            .scalars()
            .first()
        )

    if row is not None:
        source_code = row.source_code
        base_class = row.base_class
        base_type = row.base_type
        origin = "custom-override" if row.is_override else "custom"
    else:
        source_code = _read_module_source(cls)
        base_class = _detect_base_class(cls) or ""
        base_type = getattr(cls, "TYPE", "")
        origin = _classify_origin(cls)

    editable = base_class != "" and _is_base_editable(base_class)

    return ComponentSourceResponse(
        class_name=class_name,
        source_code=source_code,
        base_class=base_class,
        base_type=base_type,
        import_path=getattr(cls, "__module__", None),
        origin=origin,
        editable=editable,
    )


def _is_base_editable(base_name: str) -> bool:
    try:
        resolve_base_class(base_name)
        return True
    except ValueError:
        return False


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
    """Validate and register a custom component.

    If a component with the same class_name is already registered AND holds a
    snapshotted original (i.e. it's a core or plugin class), the new class is
    persisted as an override and replaces the original in the registry. A
    subsequent DELETE restores the original via `unregister_custom`.
    """
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

    is_override = False
    if body.class_name in component_registry:
        if has_original(body.class_name):
            is_override = True
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Component '{body.class_name}' already exists as a custom "
                    "component. Edit or delete the existing one instead."
                ),
            )

    base_type = result.cls.TYPE
    with session_factory() as db:
        row = CustomComponent(
            class_name=body.class_name,
            base_type=base_type,
            base_class=body.base_class,
            source_code=body.source_code,
            description=body.description,
            is_override=is_override,
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
            register_custom(result.cls, component_registry, override=is_override)
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
        # Drop the current class; we may be renaming the override or just
        # replacing its body.
        unregister_custom(
            row.class_name,
            component_registry,
            restore_original=False,
        )
        if (
            new_class != row.class_name
            and new_class in component_registry
            and not has_original(new_class)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Component '{new_class}' already exists as a custom "
                    "component. Pick a different name."
                ),
            )

        row.class_name = new_class
        row.base_class = new_base
        row.base_type = result.cls.TYPE
        row.source_code = new_source
        # We already unregistered the current class; can't use the registry to
        # decide override-ness. A component is an override iff it shadows a
        # class we snapshotted at startup.
        row.is_override = has_original(new_class)
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

        register_custom(result.cls, component_registry, override=row.is_override)
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
    """Delete a user-authored component.

    For overrides, this acts as a revert: the override is dropped and the
    snapshotted original is re-registered under the same name so the rest of
    the app sees the built-in/plugin class again.
    """
    with session_factory() as db:
        row = db.get(CustomComponent, component_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Custom component not found")
        # Restore the original only if this row was an override.
        unregister_custom(
            row.class_name,
            component_registry,
            restore_original=row.is_override,
        )
        _delete_source_file(row.file_path)
        db.delete(row)
        db.commit()
        forget_custom_component(row.class_name)
