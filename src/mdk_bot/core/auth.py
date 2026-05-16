"""Auth primitives — session cookie for the operator, internal token for services.

This is intentionally simple. The single-user MVP swaps in a real
OTP/OIDC flow later by replacing this module; callers only depend on
:func:`require_session` and :func:`require_internal_token`.
"""

from __future__ import annotations

import hmac
from typing import Final

from fastapi import Cookie, Header, HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeSerializer

from mdk_bot.config import get_settings

SESSION_COOKIE: Final[str] = "mdk_session"
SESSION_SALT: Final[str] = "mdk-bot-session-v1"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().SECRET_KEY, salt=SESSION_SALT)


def issue_session(subject: str = "operator") -> str:
    """Sign and return a session-cookie value identifying ``subject``."""
    return _serializer().dumps({"sub": subject})


def verify_session(value: str) -> str | None:
    """Return the subject if ``value`` is a valid session cookie, else ``None``."""
    try:
        data = _serializer().loads(value)
    except BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    sub = data.get("sub")
    return sub if isinstance(sub, str) else None


def check_login_token(submitted: str) -> bool:
    """Constant-time comparison of the submitted token against the configured one."""
    expected = get_settings().WEB_SESSION_TOKEN
    return hmac.compare_digest(expected.encode(), submitted.encode())


async def require_session(
    request: Request,
    mdk_session: str | None = Cookie(default=None),
    x_internal_token: str | None = Header(default=None),
) -> str:
    """FastAPI dependency: accept a valid session cookie OR an internal token.

    The internal token lets bot/scheduler call the API without going
    through the login flow.
    """
    settings = get_settings()
    if x_internal_token and hmac.compare_digest(
        x_internal_token.encode(), settings.INTERNAL_API_TOKEN.encode()
    ):
        return "service"

    if mdk_session:
        subject = verify_session(mdk_session)
        if subject is not None:
            return subject

    # For web routes we want a redirect to /web/login; the route handler
    # turns this exception into a redirect. For API routes the 401 is final.
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/web/") and "text/html" in accept:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="login required",
            headers={"Location": "/web/login"},
        )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")


async def require_internal_token(
    x_internal_token: str | None = Header(default=None),
) -> str:
    """Reject unless the caller presents the internal service token."""
    settings = get_settings()
    if not x_internal_token or not hmac.compare_digest(
        x_internal_token.encode(), settings.INTERNAL_API_TOKEN.encode()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="internal only")
    return "service"
