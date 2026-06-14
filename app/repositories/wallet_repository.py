# app/repositories/wallet_repository.py
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.models import Wallet


class WalletRepository:

    def __init__(
            self,
            db: AsyncSession = Depends(get_async_session),
    ):
        self._db = db

    async def get_by_id(
            self, wallet_id: UUID
    ) -> Wallet | None:
        """Fetch wallet by primary key. Return None if not found."""
        result = await self._db.execute(
            select(Wallet).where(Wallet.id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_currency(
            self, user_id: UUID, currency: str
    ) -> Wallet | None:
        """
        Fetch wallet by owner and currency code. Used for duplicate detection.
        """
        result = await self._db.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.currency == currency
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(
            self, user_id: UUID, limit: int, offset: int
    ) -> tuple[list[Wallet], int]:
        """Return paginated wallets and total count for a given user."""
        count_stmt = select(func.count()).select_from(Wallet).where(
                Wallet.user_id == user_id
            )
        total = await self._db.scalar(count_stmt)

        data_stmt = select(Wallet).where(
                Wallet.user_id == user_id
            ).limit(limit).offset(offset)
        result = await self._db.execute(data_stmt)
        wallets = result.scalars().all()

        return wallets, total

    async def create(
            self, user_id: UUID, currency: str
    ) -> Wallet:
        """Persist a new wallet with zero balance. Flush but do not commit."""
        payload = {
            'user_id': user_id,
            'currency': currency
        }
        wallet = Wallet(**payload)
        self._db.add(wallet)
        await self._db.flush()
        await self._db.refresh(wallet)
        return wallet

    async def get_wallets_for_update(
            self, wallets_ids: list[UUID]
    ) -> list[Wallet]:
        """
        Lock wallet rows for atomic update using SELECT FOR UPDATE.

        Rows are ordered by ID to prevent deadlocks (lock ordering convention).
        """
        result = await self._db.execute(
            select(Wallet).with_for_update(of=Wallet).where(
                Wallet.id.in_(wallets_ids)
            ).order_by(Wallet.id)
        )
        return result.scalars().all()
