# app/api/v1/auth_api.py
from fastapi import (
    APIRouter, Cookie, Depends,
    HTTPException, Response
)

from app.api.dependencies import get_auth_service
from app.core.utils import set_refresh_cookie
from app.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post(
    '/register',
    response_model=TokenResponse,
    status_code=201
)
async def register(
        data: RegisterRequest,
        response: Response,
        service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Register a new user and return access token.

    Refresh token is set as httpOnly cookie.
    """
    token_response, refresh_token = await service.register(data)
    set_refresh_cookie(response, refresh_token)
    return token_response


@router.post(
    '/login',
    response_model=TokenResponse,
    status_code=200
)
async def login(
        data: LoginRequest,
        response: Response,
        service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Authenticate user and return access token.

    Refresh token is set as httpOnly cookie.
    """
    token_response, refresh_token = await service.login(data)
    set_refresh_cookie(response, refresh_token)
    return token_response


@router.post(
    '/refresh',
    response_model=TokenResponse,
    status_code=200
)
async def refresh(
        response: Response,
        refresh_token: str | None = Cookie(default=None),
        service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    """Issue new token pair using refresh token from cookie."""
    if refresh_token is None:
        raise HTTPException(status_code=401, detail='Refresh token missing')
    token_response, refresh_token = await service.refresh(refresh_token)
    set_refresh_cookie(response, refresh_token)
    return token_response


@router.post(
    '/logout',
    response_model=None,
    status_code=204
)
async def logout(
        response: Response,
        refresh_token: str | None = Cookie(default=None),
        service: AuthService = Depends(get_auth_service)
) -> None:
    """Revoke refresh token and clear cookie."""
    if refresh_token is None:
        raise HTTPException(status_code=401, detail='Refresh token missing')
    await service.logout(refresh_token)
    response.delete_cookie(
        key='refresh_token',
        httponly=True,
        secure=True,
        samesite='lax'
    )
