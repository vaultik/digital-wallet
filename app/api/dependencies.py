# app/api/dependencies.py
from fastapi import Depends

from app.repositories import (
    TokenRepository,
    UserRepository,
)
from app.services.auth_service import AuthService


async def get_auth_service(
        token_repo: TokenRepository = Depends(TokenRepository),
        user_repo: UserRepository = Depends(UserRepository),
) -> AuthService:
    return AuthService(user_repo, token_repo)
