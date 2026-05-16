# app/core/utils.py
from fastapi import Response

from app.core.constants import (
    REFRESH_EXPIRE,
)


def set_refresh_cookie(response: Response, token: str) -> None:
    """Set httpOnly refresh token cookie on the response."""
    response.set_cookie(
        key='refresh_token',
        value=token,
        httponly=True,
        secure=True,
        samesite='lax',
        max_age=REFRESH_EXPIRE
    )
