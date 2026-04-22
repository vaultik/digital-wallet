# app/core/db.py
import logging
from typing import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
     """A generator for asynchronous sessions for dependency injection."""
     async with AsyncSessionLocal() as async_session:
         try:
             yield async_session
         except SQLAlchemyError as e:
             await async_session.rollback()
             logger.error('DB Error: %s', e, exc_info=True)
             raise
         finally:
             await async_session.close()
