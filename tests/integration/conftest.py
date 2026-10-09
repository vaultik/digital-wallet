# tests/integration/conftest.py
from decimal import Decimal
from typing import AsyncGenerator
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.main import app
from app.models import Wallet


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
@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def auth_client(
        async_client: AsyncClient,
        registered_user: dict
) -> AsyncClient:
    """Return async client with Bearer token pre-set in Authorization header."""
    async_client.headers.update({
        'Authorization': f'Bearer {registered_user["access_token"]}'
    })
    return async_client


@pytest_asyncio.fixture
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


@pytest_asyncio.fixture
async def second_user_with_wallet(
        async_client: AsyncClient,
) -> AsyncGenerator[tuple[AsyncClient, str], None]:
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

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
            headers={'Authorization': f'Bearer {token}'},
    ) as second_client:
        wallet_response = await second_client.post(
            '/api/v1/wallets', json={'currency': 'USD'}
        )
        yield second_client, wallet_response.json()['wallet_id']


@pytest_asyncio.fixture
async def third_user_with_wallet_diff_currency(
        async_client: AsyncClient,
) -> AsyncGenerator[tuple[AsyncClient, str], None]:
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

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
            headers={'Authorization': f'Bearer {token}'},
    ) as third_client:
        wallet_response = await third_client.post(
            '/api/v1/wallets', json={'currency': 'BTC'}
        )
        yield third_client, wallet_response.json()['wallet_id']


@pytest_asyncio.fixture
async def funded_wallets(
        db_session: AsyncSession,
        user_with_wallet: tuple[AsyncClient, str],
        second_user_with_wallet: tuple[AsyncClient, str]
) -> tuple[AsyncClient, str, AsyncClient, str]:
    """
    Provision two users with USD wallets and seed the first with 1000 USD.

    Writes through the test session, so the app sees the balance inside
    the same transaction.
    """
    client1, wallet_id1 = user_with_wallet
    client2, wallet_id2 = second_user_with_wallet

    await db_session.execute(
        update(Wallet)
        .where(Wallet.id == UUID(wallet_id1))
        .values(balance=Decimal('1000'))
    )
    await db_session.commit()
    db_session.expire_all()

    return client1, wallet_id1, client2, wallet_id2


@pytest_asyncio.fixture(autouse=True)
async def override_session(
        db_session: AsyncSession
) -> AsyncGenerator[None, None]:
    """Make the app use the test's session, then restore the app state."""
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(override_session: None) -> AsyncGenerator[AsyncClient, None]:
    """Anonymous HTTP client; auth is layered on top by other fixtures."""
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test'
    ) as client:
        yield client
