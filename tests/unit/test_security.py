# tests/unit/test_security.py
import pytest

from app.core.exceptions import InvalidTokenError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password
)


def test_hash_password_returns_hash():
    plain = 'Test12345&!'
    hashed = hash_password(plain)
    assert plain != hashed
    assert isinstance(hashed, str)

def test_verify_password_correct():
    plain = 'Test12345&!'
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)

def test_verify_password_wrong():
    plain = 'Test12345&!'
    hashed = hash_password(plain)
    assert not verify_password('Wrong!', hashed)

def test_create_access_token_returns_string():
    cat = create_access_token('ere34', 'df33')
    assert isinstance(cat, str) and cat.startswith('eyJ')

def test_decode_token_valid():
    cat = create_access_token('ere34', 'df33')
    d_token = decode_token(cat)
    assert d_token.sub == 'ere34' and d_token.sid == 'df33'

def test_decode_token_invalid_raises_error():
    with pytest.raises(InvalidTokenError):
        decode_token('invalid.token.here')
