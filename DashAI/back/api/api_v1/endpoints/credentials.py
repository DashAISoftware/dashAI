"""Credential API endpoints."""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from kink import di
from pydantic import BaseModel

from DashAI.back.credentials.sync import sync_credentials_status

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)
router = APIRouter()


class AuthRequest(BaseModel):
    """Request body for authenticating a credential.

    Parameters
    ----------
    key : str
        The platform key/token to validate and store.
    """

    key: str


def _credential_components(registry: "ComponentRegistry") -> Dict[str, Dict[str, Any]]:
    """Return the registry's Credential-type components.

    Parameters
    ----------
    registry : ComponentRegistry
        The component registry.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of credential name to component dict.
    """
    return registry._registry.get("Credential", {})


def _status_payload(
    name: str, component_dict: Dict[str, Any], is_authenticated: bool
) -> Dict[str, Any]:
    """Build the public status payload for a credential.

    Parameters
    ----------
    name : str
        Credential component name.
    component_dict : Dict[str, Any]
        The registry component dict.
    is_authenticated : bool
        Whether the credential is currently verified.

    Returns
    -------
    Dict[str, Any]
        Public, key-free status payload.
    """
    display_name = component_dict.get("display_name")
    if hasattr(display_name, "get"):
        display_name = display_name.get("en")
    return {
        "name": name,
        "display_name": display_name or name,
        "is_authenticated": is_authenticated,
    }


@router.get("/")
async def list_credentials(
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> List[Dict[str, Any]]:
    """List all credential components and their authentication status.

    Parameters
    ----------
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    list[dict]
        Credential status payloads (never includes keys).
    """
    creds = _credential_components(registry)
    statuses = di["credential_store"].all_statuses()
    return [
        _status_payload(name, cdict, statuses.get(name, False))
        for name, cdict in creds.items()
    ]


@router.get("/{name}")
async def get_credential_status(
    name: str,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> Dict[str, Any]:
    """Return the status of a single credential.

    Parameters
    ----------
    name : str
        Credential component name.
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    dict
        Status payload.

    Raises
    ------
    HTTPException
        404 if the credential is not registered.
    """
    creds = _credential_components(registry)
    if name not in creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential '{name}' not found.",
        )
    is_authenticated = di["credential_store"].is_verified(name)
    return _status_payload(name, creds[name], is_authenticated)


@router.post("/{name}/auth")
async def authenticate_credential(
    name: str,
    body: AuthRequest,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> Dict[str, Any]:
    """Verify and store a credential key.

    Parameters
    ----------
    name : str
        Credential component name.
    body : AuthRequest
        Contains the key to authenticate with.
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    dict
        ``{"is_authenticated": True}`` on success.

    Raises
    ------
    HTTPException
        404 if the credential is unknown, 400 if the key is invalid.
    """
    creds = _credential_components(registry)
    if name not in creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential '{name}' not found.",
        )
    credential = creds[name]["class"]()
    try:
        credential.auth(body.key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential key.",
        ) from exc

    affected = registry.get_required_credentials(name)
    sync_credentials_status(only=affected)
    return {"is_authenticated": True}


@router.delete("/{name}")
async def delete_credential(
    name: str,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> Dict[str, Any]:
    """Remove a stored credential key.

    Parameters
    ----------
    name : str
        Credential component name.
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    dict
        ``{"is_authenticated": False}``.

    Raises
    ------
    HTTPException
        404 if the credential is not registered.
    """
    creds = _credential_components(registry)
    if name not in creds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Credential '{name}' not found.",
        )
    di["credential_store"].delete(name)
    affected = registry.get_required_credentials(name)
    sync_credentials_status(only=affected)
    return {"is_authenticated": False}
