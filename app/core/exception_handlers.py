# app/core/exception_handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


async def handle_invalid_credentials(
        request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    """Return 401 for invalid login credentials."""
    return JSONResponse(
        status_code=401,
        content={'detail': str(exc)}
    )

async def handle_invalid_token(
        request: Request, exc: InvalidTokenError
) -> JSONResponse:
    """Return 401 for invalid or expired tokens."""
    return JSONResponse(
        status_code=401,
        content={'detail': str(exc)}
    )

async def handle_user_already_exists(
        request: Request, exc: UserAlreadyExistsError
) -> JSONResponse:
    """Return 409 when username or email is already taken."""
    return JSONResponse(
        status_code=409,
        content={'detail': str(exc)}
    )

async def handle_user_not_found(
        request: Request, exc: UserNotFoundError
) -> JSONResponse:
    """Return 404 when requested user does not exist."""
    return JSONResponse(
        status_code=404,
        content={'detail': str(exc)}
    )


EXCEPTION_HANDLERS = {
    InvalidCredentialsError: handle_invalid_credentials,
    InvalidTokenError: handle_invalid_token,
    UserAlreadyExistsError: handle_user_already_exists,
    UserNotFoundError: handle_user_not_found,
}
