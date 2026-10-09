# tests/conftest.py
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope='session', autouse=True)
def guard_test_database() -> None:
    """
    Abort the entire run unless the configured database is a test one.

    Fixtures below rebuild the schema from scratch, so pointing them at
    a development database would destroy real data.
    """
    db_name = settings.postgres_db_test
    if not db_name.endswith('_test'):
        pytest.exit(
            f'Refusing to run: {db_name!r} does not look like a test '
            f'database. Expected a name ending with "_test".',
            returncode=1,
        )


@pytest.fixture(scope='session', autouse=True)
def apply_migrations(guard_test_database: None) -> None:
    """
    Rebuild the test schema from scratch via Alembic, once per session.

    Running real migrations (instead of metadata.create_all) also seeds
    currencies and the system user, and fails loudly on a broken revision.
    """
    alembic_cfg = Config(str(BASE_DIR / 'alembic.ini'))
    alembic_cfg.set_main_option('sqlalchemy.url', settings.test_database_url)

    command.downgrade(alembic_cfg, 'base')
    command.upgrade(alembic_cfg, 'head')


@pytest.fixture(scope='session')
def engine(apply_migrations: None):
    """Session-wide async engine bound to the test database."""
    return create_async_engine(
        settings.test_database_url,
        poolclass=NullPool,
    )


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Session bound to a single connection inside an outer transaction.

    Everything the test and the app write is rolled back on teardown,
    so seed data survives untouched.
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode='create_savepoint',
            expire_on_commit=False
        )
        try:
            yield session
        finally:
            await session.close()
            if transaction.is_active:
                await transaction.rollback()
