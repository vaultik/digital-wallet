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
    """
    Handles user authentication: registration, login, token refresh and logout.
    """

    def __init__(
            self,
            token_repo: TokenRepository,
            user_repo: UserRepository,
    ):
        self._token_repo = token_repo
        self._user_repo = user_repo

    async def _issue_tokens(
            self,
            user_id: str,
            session_id: str | None = None,
    ) -> tuple[TokenResponse, str]:
        """Create access/refresh token pair and save refresh token to Redis.

        If session_id is not provided, a new one is generated (register/login).
        If session_id is provided, it means we're rotating tokens (refresh).
        """
        if session_id is None:
            session_id = str(uuid4())

        access_token = create_access_token(user_id, session_id)
        refresh_token = create_refresh_token(user_id, session_id)

        await self._token_repo.save_refresh_token(
            user_id,
            session_id,
            refresh_token,
            REFRESH_EXPIRE
        )
        return TokenResponse(
            access_token=access_token,
            token_type='Bearer',
            expires_in=ACCESS_EXPIRE,
        ), refresh_token

    async def register(self, data: RegisterRequest) -> tuple[TokenResponse, str]:
        """Register a new user and return token pair.

        Raises UserAlreadyExistsError if username or email is already taken.
        """
        # Check username uniqueness
        user = await self._user_repo.get_by_username(data.username)
        if user is not None:
            raise UserAlreadyExistsError('Username already taken')

        # Check email uniqueness only if provided
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
        return await self._issue_tokens(user.id)

    async def login(self, data: LoginRequest) -> tuple[TokenResponse, str]:
        """Authenticate user and return token pair.

        Always raises the same error for wrong username or password
        to avoid exposing which one is incorrect.
        """
        user = await self._user_repo.get_by_username(data.username)

        if user is None or not user.is_active:
            raise InvalidCredentialsError('Invalid username or password')
        if not verify_password(data.password, user.hashed_password):
            raise InvalidCredentialsError('Invalid username or password')

        return await self._issue_tokens(user.id)

    async def refresh(
            self,
            refresh_token: str,
    ) -> tuple[TokenResponse, str]:
        """Rotate refresh token and issue new access token.

        Validates token signature first, then checks Redis to ensure
        the token hasn't been revoked (e.g. after logout).
        """
        data = decode_token(refresh_token)

        # Verify token exists in Redis (not revoked)
        stored_token = await self._token_repo.get_refresh_token(
            data.sub,
            data.sid
        )
        if refresh_token != stored_token:
            raise InvalidTokenError('Please auth again...')

        user = await self._user_repo.get_by_id(data.sub)
        if user is None or not user.is_active or user.is_system_user:
            await self._token_repo.delete_refresh_token(data.sub, data.sid)
            raise InvalidTokenError('Please auth again...')

        # Rotate: delete old token, issue new pair with same session_id
        await self._token_repo.delete_refresh_token(data.sub, data.sid)
        return await self._issue_tokens(data.sub, data.sid)

    async def logout(
            self,
            refresh_token: str,
    ) -> None:
        """Revoke refresh token by removing it from Redis.

        After logout, the refresh token is invalid even if not expired.
        The access token will expire naturally within its TTL.
        """
        data = decode_token(refresh_token)
        await self._token_repo.delete_refresh_token(data.sub, data.sid)
