# tests/integration/conftest.py
import pytest


@pytest.fixture
def test_user() -> dict:
    """Standard test user credentials."""
    return {
        'username': 'test_user',
        'email': 'test@test.com',
        'password': 'Test12345!'
    }

@pytest.fixture
def wrong_password_user() -> dict:
    """Test user with incorrect password."""
    return {
        'username': 'test_user',
        'email': 'test@test.com',
        'password': 'Test1wtgweg2345!'
    }

@pytest.fixture
def nonexistent_user() -> dict:
    """Credentials for a user that doesn't exist."""
    return {
        'username': 'nobody',
        'password': 'Tes2424t12345!'
    }
