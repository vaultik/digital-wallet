# app/repositories/currency_repository.py
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.models import Currency


class CurrencyRepository:

    def __init__(
            self,
            db: AsyncSession = Depends(get_async_session)
    ):
        self._db = db

    async def get_by_code(self, code: str) -> Currency | None:
        result = await self._db.execute(
            select(Currency).where(Currency.code == code)
        )
        return result.scalar_one_or_none()
