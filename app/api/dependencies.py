# app/api/dependencies.py
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import UserNotFoundError
from app.core.security import decode_token
from app.models import User
from app.repositories import (
    TokenRepository,
    UserRepository,
)
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        user_repo: UserRepository = Depends(UserRepository)
) -> User:
    """Decode Bearer token and return the active user. Raise 401 if invalid."""
    payload = decode_token(token)
    user = await user_repo.get_by_id(payload.sub)
    if user is None or not user.is_active:
        raise UserNotFoundError('User not found')
    return user


async def get_auth_service(
        token_repo: TokenRepository = Depends(TokenRepository),
        user_repo: UserRepository = Depends(UserRepository),
) -> AuthService:
    """Dependency factory for AuthService with injected repositories."""
    return AuthService(
        token_repo=token_repo,
        user_repo=user_repo
    )
