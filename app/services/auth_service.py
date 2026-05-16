# app/services/auth_service.py
from uuid import uuid4

from app.core.constants import (
    ACCESS_EXPIRE,
    REFRESH_EXPIRE,
)
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotFoundError
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories import (
    TokenRepository,
    UserRepository
)
from app.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)


class AuthService:

    def __init__(
            self,
            token_repo: TokenRepository,
            user_repo: UserRepository,
    ):
        self._token_repo = token_repo
        self._user_repo = user_repo

    async def register(
            self,
            data: RegisterRequest,
    ) -> TokenResponse:
        user = await self._user_repo.get_by_username(data.username)
        if user is not None:
            raise UserAlreadyExistsError('Username already taken')
        if data.email is not None:
            user = await self._user_repo.get_by_email(data.email)
            if user is not None:
                raise UserAlreadyExistsError('Email already taken')
        hashed_pass = hash_password(data.password)
        user = await self._user_repo.create_user(
            data.username,
            data.email,
            hashed_pass
        )
        session_id = str(uuid4())
        access_token = create_access_token(user.id, session_id)
        refresh_token = create_refresh_token(user.id, session_id)
        ttl = REFRESH_EXPIRE
        await self._token_repo.save_refresh_token(
            user.id,
            session_id,
            refresh_token,
            ttl
        )
        payload = {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_EXPIRE,
        }
        return TokenResponse(**payload)

    async def login(
            self,
            data: LoginRequest,
    ) -> TokenResponse:
        user = await self._user_repo.get_by_username(data.username)
        if user is None:
            raise UserNotFoundError('Invalid username or password')
        password = verify_password(data.password, user.hashed_password)
        if not password:
            raise InvalidCredentialsError('Invalid username or password')
        session_id = str(uuid4())
        access_token = create_access_token(user.id, session_id)
        refresh_token = create_refresh_token(user.id, session_id)
        ttl = REFRESH_EXPIRE
        await self._token_repo.save_refresh_token(
            user.id,
            session_id,
            refresh_token,
            ttl
        )
        payload = {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_EXPIRE,
        }
        return TokenResponse(**payload)

    async def refresh(
            self,
            refresh_token: str,
    ) -> TokenResponse:
        data = decode_token(refresh_token)
        redis_refresh_token = await self._token_repo.get_refresh_token(
            data.sub,
            data.sid
        )
        if refresh_token != redis_refresh_token:
            raise InvalidTokenError('Please auth again...')
        access_token = create_access_token(
            data.sub,
            data.sid
        )
        refresh_token = create_refresh_token(
            data.sub,
            data.sid
        )
        await self._token_repo.delete_refresh_token(data.sub, data.sid)
        await self._token_repo.save_refresh_token(
            data.sub,
            data.sid,
            refresh_token,
            REFRESH_EXPIRE
        )
        payload = {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': ACCESS_EXPIRE,
        }
        return TokenResponse(**payload)

    async def logout(
            self,
            refresh_token: str,
    ) -> None:
        data = decode_token(refresh_token)
        await self._token_repo.delete_refresh_token(
            data.sub,
            data.sid,
        )
