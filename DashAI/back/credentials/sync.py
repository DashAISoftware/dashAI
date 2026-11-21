"""Credential availability of components, for the user the backend acts for.

Credentials belong to each user, so whether a component has the credentials
it requires depends on who asks. The registry keeps the flag computed without
any credential; responses replace it with the acting user's.
"""

from typing import Any, Dict

from kink import di

from DashAI.back.auth.acting_user import get_acting_user_id


def acting_user_credential_statuses() -> Dict[str, bool]:
    """Return the verified status of the acting user's credentials.

    Returns
    -------
    Dict[str, bool]
        Mapping of credential name to verified status; empty when the backend
        acts for nobody.
    """
    user_id = get_acting_user_id()
    if user_id is None:
        return {}
    return di["credential_store"].all_statuses(user_id=user_id)


def credentials_satisfied(
    component_dict: Dict[str, Any], statuses: Dict[str, bool]
) -> bool:
    """Tell whether every credential a component requires is verified.

    Parameters
    ----------
    component_dict : Dict[str, Any]
        The registry component dict.
    statuses : Dict[str, bool]
        A user's credential statuses, from ``acting_user_credential_statuses``.

    Returns
    -------
    bool
        True when no required credential is missing.
    """
    required = component_dict.get("required_credentials") or []
    return all(statuses.get(name, False) for name in required)
