"""Credential API endpoints."""

import logging
from typing import TYPE_CHECKING, Any, Dict

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


@router.get("/{name}")
async def get_credential_status(
    name: str,
    registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
) -> Dict[str, Any]:
    """Return the authentication state of a single credential.

    The catalog metadata (display name, description) is served by the
    components endpoint; this endpoint only reports credential-specific state:
    whether it is authenticated and the stored key.

    Parameters
    ----------
    name : str
        Credential component name.
    registry : ComponentRegistry
        Injected component registry.

    Returns
    -------
    dict
        ``{"name", "is_authenticated", "key"}``. The stored key is included so
        the configuration modal can display it, which is acceptable for
        DashAI's local-first, single-user desktop model.

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
    store = di["credential_store"]
    return {
        "name": name,
        "is_authenticated": store.is_verified(name),
        "key": store.load(name),
    }


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
