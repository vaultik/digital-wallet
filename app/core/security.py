# app/core/security.py
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.schemas.auth_schemas import TokenPayload
from app.core.exceptions import InvalidTokenError
from app.core.config import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain:str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(
        user_id: str,
        session_id: str,
        expire_delta: timedelta
) -> str:
    try:
        payload = {
            'sub': str(user_id),
            'sid': str(session_id),
            'exp': datetime.now(timezone.utc) + expire_delta,
            'iat': datetime.now(timezone.utc)
        }
        return jwt.encode(payload, settings.secret, algorithm='HS256')
    except JWTError:
        raise InvalidTokenError('Token is invalid or expired')


def create_access_token(
        user_id: str,
        session_id: str,
) -> str:
    return _create_token(user_id, session_id, timedelta(minutes=15))


def create_refresh_token(
        user_id: str,
        session_id: str,
) -> str:
    return _create_token(user_id, session_id, timedelta(days=7))


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.secret,
            algorithms=['HS256'],
        )
        return TokenPayload(**payload)
    except JWTError:
        raise InvalidTokenError('Token is invalid or expired')
