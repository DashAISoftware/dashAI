"""Component API module."""

import io
import logging
from typing import Any, Dict, List, Union

import requests
from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from kink import di, inject
from typing_extensions import Annotated

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.registry import ComponentRegistry

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


def _intersect_component_lists(
    previous_selected_components: Dict[str, Dict[str, Any]],
    component_list: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    selected_components = {
        component_dict["name"]: component_dict
        for component_dict in component_list
        if component_dict["name"] in previous_selected_components
    }
    return selected_components


def _filter_by_language(
    component_dict: Dict[str, Any], language: str | None = None
) -> Dict[str, Any]:
    """
    Recursively filters MultilingualString objects in the component dictionary,
    returning only the string value for the specified language.

    Parameters
    ----------
    component_dict : Dict[str, Any]
        The component dictionary potentially containing MultilingualString objects
    language : str | None, optional
        The language code (e.g., 'en', 'es'). If None, defaults to 'en'

    Returns
    -------
    Dict[str, Any]
        The component dictionary with MultilingualString objects replaced by plain strings
    """
    if language is None:
        language = "en"

    # Extract just the language code (e.g., 'en' from 'en-US')
    lang_code = language.split("-")[0].lower() if language else "en"

    def process_value(value):
        # If it's a MultilingualString, use its get method
        if isinstance(value, MultilingualString):
            return value.get(lang_code)

        # If it's a dictionary, recursively process it
        elif isinstance(value, dict):
            return {k: process_value(v) for k, v in value.items()}

        # If it's a list, recursively process each item
        elif isinstance(value, list):
            return [process_value(item) for item in value]

        # Otherwise, return the value as-is
        else:
            return value

    return process_value(component_dict)


def _delete_class(component_dict: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in component_dict.items() if key != "class"}


@router.get("/")
@inject
async def get_components(
    select_types: Annotated[Union[List[str], None], Query()] = None,
    ignore_types: Annotated[Union[List[str], None], Query()] = None,
    accept_language: str | None = Header(default=None),
    related_component: Union[str, None] = None,
    component_parent: Union[str, None] = None,
    has_related_of_type: Union[str, None] = None,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
) -> List[Dict[str, Any]]:
    """Retrieve components from the register according to the provided parameters.

    When all parameters are None, the method return all registered components.
    If more than one parameter is specified, then the method returns the intersection
    between the retrived components.

    The components returned will depend on the parameters of the request.
    If all parameters are None, then the method returns all registered components.

    Parameters
    ----------
    select_types: Annotated[Union[List[str], None], Query()], optional
        If specified, the function return only the components that extend the
        provided types (e.g., task, model, dataloader, etc...).
        If None, the method returns all components in the registry, by default None.
    ignore_types: Annotated[Union[List[str], None], Query()], optional
        If specified, the function return every components that is not that extend
        the provided types (e.g., task, model, dataloader, etc...).
        If None, the method returns all components in the registry, by default None.
    accept_language: str | None = Header(default=None)
        The 'Accept-Language' header from the request to localize multilingual
        strings in the component schemas, by default None.
    related_component : Union[str , None], optional
        If specified, the function return only the components related with
        the specified compatible component, (usually some task. as
        TabularClassification, Translation, etc.), by default None.
    component_parent : Union[str , None], optional
        If specified, the function return only the components that inheirts the
        indicated component (e.g., ScikitLearnLikeModel), by default None.
    has_related_of_type : Union[str, None], optional
        If specified, the function returns only components that have at least one
        related component of the specified type (e.g., "Model"). This is useful for
        filtering tasks that have associated models, by default None.
    component_registry : ComponentRegistry
        The current app component registry provided by dependency injection.

    Returns
    -------
    list[dict]
        A list with the selected component schemas.

    Raises
    ------
    HTTPException
        If component_type does not exist in the registry
    HTTPException
        If task_name does not exist in the registry
    """
    # when select_type is not none, check if it exists in the registry.
    if select_types is not None:
        for select_type in select_types:
            if select_type not in component_registry._registry:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Select type '{select_type}' does not exist in the registry. "
                        f"Available types: {list(component_registry._registry.keys())}."
                    ),
                )

    # when ignore_type is not none, check if it exists in the registry.
    if ignore_types is not None:
        for ignore_type in ignore_types:
            if ignore_type not in component_registry._registry:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Ignore type '{ignore_type}' does not exist in the registry. "
                        f"Available types: {list(component_registry._registry.keys())}."
                    ),
                )

    # when task_name is not none, check if it exists in the registry.
    if related_component is not None and related_component not in component_registry:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Related component {related_component} does not exist in the registry."
            ),
        )

    # When has_related_type is not none, check if it exists in the registry.
    if (
        has_related_of_type is not None
        and has_related_of_type not in component_registry._registry
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Type '{has_related_of_type}' does not exist in the registry. "
                f"Available types: {list(component_registry._registry.keys())}."
            ),
        )

    # 1. obtain all components from the selected registry/registries
    # if none, get_components_by_type returns all components.
    selected_components = {
        component_dict["name"]: component_dict
        for component_dict in component_registry.get_components_by_types(
            select=select_types
        )
    }

    # 2. ignore the requested types
    if ignore_types is not None:
        selected_components = _intersect_component_lists(
            selected_components,
            component_registry.get_components_by_types(ignore=ignore_types),
        )

    # 3. select only the components related to "related_component"
    if related_component is not None:
        selected_components = _intersect_component_lists(
            selected_components,
            component_registry.get_related_components(related_component),
        )

    # 4. filter if component parent was specified.
    if component_parent is not None:
        selected_components = _intersect_component_lists(
            selected_components,
            component_registry.get_child_components(component_parent, recursive=True),
        )

    # 5. filter if "has_related_of_type" was specified.
    if has_related_of_type is not None:
        components_with_related_type = []
        for comp_name, component_dict in selected_components.items():
            related_components = component_registry.get_related_components(comp_name)
            if any(rel["type"] == has_related_of_type for rel in related_components):
                components_with_related_type.append(component_dict)
        selected_components = _intersect_component_lists(
            selected_components,
            components_with_related_type,
        )

    return [
        _filter_by_language(_delete_class(component_dict), accept_language)
        for component_dict in selected_components.values()
    ]


@router.get("/{id}/")
@inject
def get_component_by_id(
    id: str,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
) -> Dict[str, Any]:
    """Return an specific component using its id (the id is the component class name).

        Parameters
        ----------
        id : str
            A component identificator
    component_registry : ComponentRegistry
            The current app component registry provided by dependency injection.

        Returns
        -------
        dict
            The retrieved component dict.

        Raises
        ------
        HTTPException
            If the id does not exists in the registry.
    """
    if id not in component_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Component {id} not found in the registry.",
        )
    return _delete_class(component_registry[id])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_component() -> None:
    """Create component placeholder.

    Raises
    ------
    HTTPException
        Always raises exception as it was intentionally not implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Method not implemented"
    )


@router.delete("/")
async def delete_component() -> None:
    """Delete component placeholder.

    Raises
    ------
    HTTPException
        Always raises exception as it was intentionally not implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Method not implemented"
    )


@router.patch("/")
async def update_component() -> None:
    """Update component placeholder.

    Raises
    ------
    HTTPException
        Always raises exception as it was intentionally not implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Method not implemented"
    )


@router.get("/image/{component_name}/", status_code=status.HTTP_200_OK)
async def get_component_image(
    component_name: str,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    config: Dict[str, Any] = Depends(lambda: di["config"]),
) -> StreamingResponse:
    """Return the image of a specific component.

    Parameters
    ----------
    component_name : str
        The name of the component to retrieve the image for.
    component_registry : ComponentRegistry
        The current app component registry provided by dependency injection.

    Returns
    -------
    StreamingResponse
        The image of the component.
    """
    if component_name not in component_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Component {component_name} not found in the registry.",
        )

    local_path_image = config["BACK_PATH"] / "static" / "images"
    image_path: str = (
        component_registry[component_name]
        .get("metadata", {})
        .get("image_preview", None)
    )
    if not image_path:
        with open(local_path_image / "placeholder.svg", "rb") as image_file:
            return StreamingResponse(
                io.BytesIO(image_file.read()), media_type="image/svg+xml"
            )

    # If it is a URL, we obtain the image from the URL
    if image_path.startswith(("http://", "https://")):
        response = requests.get(image_path, timeout=5)
        if response.status_code == 200:
            return StreamingResponse(
                io.BytesIO(response.content), media_type="image/png"
            )
        else:
            with open(local_path_image / "placeholder.svg", "rb") as image_file:
                return StreamingResponse(
                    io.BytesIO(image_file.read()), media_type="image/svg+xml"
                )

    # Otherwise, we assume it is a local path
    try:
        with open(local_path_image / image_path, "rb") as image_file:
            return StreamingResponse(
                io.BytesIO(image_file.read()), media_type="image/png"
            )
    except FileNotFoundError:
        with open(local_path_image / "placeholder.svg", "rb") as image_file:
            return StreamingResponse(
                io.BytesIO(image_file.read()), media_type="image/svg+xml"
            )
