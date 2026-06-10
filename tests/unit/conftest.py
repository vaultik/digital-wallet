# tests/unit/conftest.py
import pytest

from app.core.security import (
    create_access_token,
    hash_password,
)


@pytest.fixture
def plain_password() -> str:
    """Plain text password for testing."""
    return 'Test12345&!'

@pytest.fixture
def hashed_password(plain_password: str) -> str:
    """Bcrypt hashed version of the plain test password."""
    return hash_password(plain_password)

@pytest.fixture
def access_token() -> str:
    """Valid access token for a test user."""
    return create_access_token('test-user-id', 'test-session-id')
