# app/core/exception_handlers.py
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    InvalidWalletsDataError,
    InvalidWebhookSignatureError,
    PaymentProviderError,
    UserAlreadyExistsError,
    UserNotFoundError,
    WalletAlreadyExistsError,
    WalletNotFoundError,
)


async def handle_invalid_credentials(
        request: Request, exc: InvalidCredentialsError
) -> JSONResponse:
    """Return 401 for invalid login credentials."""
    return JSONResponse(
        status_code=HTTPStatus.UNAUTHORIZED,
        content={'detail': str(exc)}
    )


async def handle_invalid_token(
        request: Request, exc: InvalidTokenError
) -> JSONResponse:
    """Return 401 for invalid or expired tokens."""
    return JSONResponse(
        status_code=HTTPStatus.UNAUTHORIZED,
        content={'detail': str(exc)}
    )


async def handle_user_already_exists(
        request: Request, exc: UserAlreadyExistsError
) -> JSONResponse:
    """Return 409 when username or email is already taken."""
    return JSONResponse(
        status_code=HTTPStatus.CONFLICT,
        content={'detail': str(exc)}
    )


async def handle_user_not_found(
        request: Request, exc: UserNotFoundError
) -> JSONResponse:
    """Return 404 when requested user does not exist."""
    return JSONResponse(
        status_code=HTTPStatus.NOT_FOUND,
        content={'detail': str(exc)}
    )


async def handle_wallet_already_exists(
        request: Request, exc: WalletAlreadyExistsError
) -> JSONResponse:
    """Return 409 when wallet already exists."""
    return JSONResponse(
        status_code=HTTPStatus.CONFLICT,
        content={'detail': str(exc)}
    )


async def handle_wallet_not_found(
        request: Request, exc: WalletNotFoundError
) -> JSONResponse:
    """Return 404 when wallet does not exist."""
    return JSONResponse(
        status_code=HTTPStatus.NOT_FOUND,
        content={'detail': str(exc)}
    )


async def handle_invalid_wallet_data(
        request: Request, exc: InvalidWalletsDataError
) -> JSONResponse:
    """Return 400 when wallet operation data is invalid."""
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={'detail': str(exc)}
    )


async def handle_payment_provider_unavailable(
        request: Request, exc: PaymentProviderError
) -> JSONResponse:
    """Return 502 when payment provider is unavailable."""
    return JSONResponse(
        status_code=HTTPStatus.BAD_GATEWAY,
        content={'detail': str(exc)}
    )


async def handle_invalid_webhook_signature_error(
        request: Request, exc: InvalidWebhookSignatureError
) -> JSONResponse:
    """Return 400 when webhook signature is invalid."""
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={'detail': str(exc)}
    )


EXCEPTION_HANDLERS = {
    InvalidCredentialsError: handle_invalid_credentials,
    InvalidTokenError: handle_invalid_token,
    InvalidWalletsDataError: handle_invalid_wallet_data,
    InvalidWebhookSignatureError: handle_invalid_webhook_signature_error,
    PaymentProviderError: handle_payment_provider_unavailable,
    UserAlreadyExistsError: handle_user_already_exists,
    UserNotFoundError: handle_user_not_found,
    WalletAlreadyExistsError: handle_wallet_already_exists,
    WalletNotFoundError: handle_wallet_not_found,
}
