# tests/integration/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# Auth
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


# Wallet
@pytest.fixture
async def registered_user(
        async_client: AsyncClient,
        test_user: dict
) -> dict:
    """Registers user and returns access token + user data."""
    response = await async_client.post(
        '/api/v1/auth/register',
        json=test_user
    )
    return {
        'access_token': response.json()['access_token'],
        'username': test_user['username'],
    }


@pytest.fixture
async def auth_client(
        async_client: AsyncClient,
        registered_user: dict
) -> AsyncClient:
    """Return async client with Bearer token pre-set in Authorization header."""
    async_client.headers.update({
        'Authorization': f'Bearer {registered_user["access_token"]}'
    })
    return async_client


@pytest.fixture
async def user_with_wallet(
        auth_client: AsyncClient
) -> tuple[AsyncClient, str]:
    """Creates USD wallet, returns (auth_client, wallet_id)."""
    response = await auth_client.post(
        '/api/v1/wallets',
        json={'currency': 'USD'}
    )
    wallet_id = response.json()['wallet_id']
    return auth_client, wallet_id


@pytest.fixture
async def second_user_with_wallet(
        async_client: AsyncClient,
) -> tuple[AsyncClient, str]:
    """Creates second user with USD wallet for transfer tests."""
    second_user = {
        'username': 'second_user',
        'email': 'second@test.com',
        'password': 'Test112233!'
    }
    response = await async_client.post(
        '/api/v1/auth/register',
        json=second_user
    )
    token = response.json()['access_token']

    second_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test'
    )
    second_client.headers.update({
        'Authorization': f'Bearer {token}'
    })
    wallet_response = await second_client.post(
        '/api/v1/wallets',
        json={'currency': 'USD'}
    )
    wallet_id = wallet_response.json()['wallet_id']
    return second_client, wallet_id


@pytest.fixture
async def third_user_with_wallet_diff_currency(
        async_client: AsyncClient,
) -> tuple[AsyncClient, str]:
    """Creates third user with BTC wallet for transfer tests."""
    third_user = {
        'username': 'third_user',
        'email': 'third@test.com',
        'password': 'Te23dwfvsvst112233!'
    }
    response = await async_client.post(
        '/api/v1/auth/register',
        json=third_user
    )
    token = response.json()['access_token']

    third_client = AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test'
    )
    third_client.headers.update({
        'Authorization': f'Bearer {token}'
    })
    wallet_response = await third_client.post(
        '/api/v1/wallets',
        json={'currency': 'BTC'}
    )
    wallet_id = wallet_response.json()['wallet_id']
    return third_client, wallet_id
