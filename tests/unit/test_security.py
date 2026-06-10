# tests/unit/test_security.py
import pytest

from app.core.exceptions import InvalidTokenError
from app.core.security import (
    decode_token,
    verify_password
)


def test_hash_password_returns_hash(
        plain_password: str,
        hashed_password: str
):
    """Hash must differ from plain text and be a string."""
    assert plain_password != hashed_password
    assert isinstance(hashed_password, str)


def test_verify_password_correct(
        plain_password: str,
        hashed_password: str
):
    """Correct password must pass verification."""
    assert verify_password(plain_password, hashed_password)


def test_verify_password_wrong(
        hashed_password: str
):
    """Wrong password must fail verification."""
    assert not verify_password('Wrong!', hashed_password)


def test_create_access_token_returns_string(access_token: str):
    """Access token must be a JWT string starting with 'eyJ'."""
    assert isinstance(access_token, str) and access_token.startswith('eyJ')


def test_decode_token_valid(access_token: str):
    """Decoded token must contain correct user_id and session_id."""
    d_token = decode_token(access_token)
    assert d_token.sub == 'test-user-id' and d_token.sid == 'test-session-id'


def test_decode_token_invalid_raises_error():
    """Invalid token string must raise InvalidTokenError."""
    with pytest.raises(InvalidTokenError):
        decode_token('invalid.token.here')
