# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import get_async_session
from app.main import app

test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_async_session():
    """Replace real DB session with test session."""
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_async_session] = override_get_async_session


@pytest_asyncio.fixture(scope='function')
async def async_client():
    """HTTP client for each test."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test'
    ) as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """
    Truncate all data-bearing tables after each test.

    Order respects FK constraints: child tables first, parent tables last.
    'transaction' and 'user' are quoted — reserved SQL keywords.
    """
    yield
    async with TestSessionLocal() as session:
        await session.execute(text('DELETE FROM "transaction"'))
        await session.execute(text('DELETE FROM "wallet"'))
        await session.execute(text('DELETE FROM "user"'))
        await session.commit()


@pytest_asyncio.fixture
async def funded_wallets(
        user_with_wallet: tuple[AsyncClient, str],
        second_user_with_wallet: tuple[AsyncClient, str]
) -> tuple[AsyncClient, str, AsyncClient, str]:
    """
    Provision two users with USD wallets, seed first user balance to 1000 USD.

    Bypasses deposit endpoint (not yet implemented) via direct DB update.
    Returns (client1, wallet_id1, client2, wallet_id2).
    """
    client1, wallet_id1 = user_with_wallet
    client2, wallet_id2 = second_user_with_wallet

    async with TestSessionLocal() as session:
        await session.execute(
            text('UPDATE wallet SET balance = 1000 WHERE id = :id'),
            {'id': wallet_id1}
        )
        await session.commit()

    return client1, wallet_id1, client2, wallet_id2
