# tests/integration/conftest.py
from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
import stripe
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.stripe_client import get_stripe_client
from app.main import app
from app.models import User, Wallet
from app.repositories import (
    TransactionRepository,
    WalletRepository,
)
from app.services import WalletService


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
) -> AsyncGenerator[AsyncSession, None]:
    """Make the app use the test's session, then restore the app state."""
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.pop(get_async_session, None)


@pytest_asyncio.fixture
async def async_client(override_session: None) -> AsyncGenerator[AsyncClient, None]:
    """Anonymous HTTP client; auth is layered on top by other fixtures."""
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test'
    ) as client:
        yield client


@pytest_asyncio.fixture
def wallet_service(db_session: AsyncSession) -> WalletService:
    """WalletService wired to the test session."""
    return WalletService(
        wallet_repo=WalletRepository(db_session),
        transaction_repo=TransactionRepository(db_session),
        db=db_session
    )


@pytest_asyncio.fixture
async def deposit_wallet(db_session: AsyncSession) -> Wallet:
    """A plain EUR wallet to receive deposits, created without the API."""
    user = User(
        username='deposit_user',
        hashed_password='not-a-real-hash',
    )
    db_session.add(user)
    await db_session.flush()

    wallet = Wallet(user_id=user.id, currency='EUR')
    db_session.add(wallet)
    await db_session.flush()

    return wallet


@pytest.fixture
def fake_stripe_client() -> MagicMock:
    """Stripe client whose checkout session creation is stubbed."""
    client = MagicMock()
    session = MagicMock()
    session.url = 'https://checkout.stripe.com/c/pay/test_session'
    client.v1.checkout.sessions.create_async = AsyncMock(return_value=session)
    return client


@pytest_asyncio.fixture
async def stripe_client_override(
        fake_stripe_client: MagicMock,
) -> AsyncGenerator[MagicMock, None]:
    """Replace the real Stripe client for the duration of a test."""
    async def _override():
        yield fake_stripe_client
    app.dependency_overrides[get_stripe_client] = _override
    yield fake_stripe_client
    app.dependency_overrides.pop(get_stripe_client, None)


@pytest_asyncio.fixture
async def stripe_webhook_override() -> AsyncGenerator[None, None]:
    """
    Stripe client that verifies signatures for real.

    Only `construct_event` is wired up — webhook handling never calls the
    Stripe API, so nothing else needs stubbing.
    """
    client = MagicMock()
    client.construct_event = stripe.Webhook.construct_event

    async def _override():
        yield client

    app.dependency_overrides[get_stripe_client] = _override
    yield
    app.dependency_overrides.pop(get_stripe_client, None)
