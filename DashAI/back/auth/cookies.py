"""Session cookie that carries the access token."""

from fastapi import Response

from DashAI.back.auth.tokens import TOKEN_LIFETIME

AUTH_COOKIE_NAME = "dashai_session"


def set_auth_cookie(response: Response, token: str, secure: bool) -> None:
    """Store the access token in the browser.

    Parameters
    ----------
    response : Response
        Response that will carry the ``Set-Cookie`` header.
    token : str
        The encoded access token.
    secure : bool
        Whether the browser may send the cookie over HTTPS only.
    """
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=int(TOKEN_LIFETIME.total_seconds()),
        path="/",
        # Not readable from JavaScript, so an injected script cannot steal it
        httponly=True,
        # Not sent on requests started by other sites (CSRF protection)
        samesite="lax",
        secure=secure,
    )


def clear_auth_cookie(response: Response, secure: bool) -> None:
    """Remove the access token from the browser.

    Parameters
    ----------
    response : Response
        Response that will carry the ``Set-Cookie`` header.
    secure : bool
        Must match the value used when the cookie was set.
    """
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=secure,
    )
