"""The user the backend is acting for, where no dependency can provide it.

Endpoints receive the user through ``get_current_user``, but some code runs
far from any endpoint and still needs to know it: a credential read inside a
job, or the job queue recording who enqueued a job. This module keeps that
user in context variables:

- During a request, ``SessionTokenMiddleware`` keeps the session cookie, and
  the user is resolved from it only when something asks for it.
- Inside a job, ``acting_as`` sets the user that enqueued it.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Receive, Scope, Send

from DashAI.back.auth.cookies import AUTH_COOKIE_NAME

_session_token: ContextVar[Optional[str]] = ContextVar(
    "dashai_session_token", default=None
)
_acting_user_id: ContextVar[Optional[int]] = ContextVar(
    "dashai_acting_user_id", default=None
)


def get_acting_user_id() -> Optional[int]:
    """Return the id of the user the backend is acting for, or None.

    An explicit ``acting_as`` wins; otherwise the session cookie of the
    current request is checked like ``get_current_user`` does, so an expired
    or revoked session acts for nobody.
    """
    user_id = _acting_user_id.get()
    if user_id is not None:
        return user_id

    token = _session_token.get()
    if token is None:
        return None

    from kink import di

    from DashAI.back.auth.dependencies import resolve_session_user

    user = resolve_session_user(token, di["session_factory"], di["auth_secret"])
    return user.id if user is not None else None


@contextmanager
def acting_as(user_id: Optional[int]) -> Iterator[None]:
    """Act for ``user_id`` inside the block (None acts for nobody)."""
    reset_token = _acting_user_id.set(user_id)
    try:
        yield
    finally:
        _acting_user_id.reset(reset_token)


class SessionTokenMiddleware:
    """Keeps the session cookie of each request for ``get_acting_user_id``.

    A plain ASGI middleware, so the context variable it sets is seen by the
    endpoint and its dependencies.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = HTTPConnection(scope).cookies.get(AUTH_COOKIE_NAME)
        reset_token = _session_token.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            _session_token.reset(reset_token)
