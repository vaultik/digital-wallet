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
    """Clean up tables after each test."""
    yield
    async with TestSessionLocal() as session:
        await session.execute(text('DELETE FROM "user"'))
        await session.commit()
