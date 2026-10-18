# tests/integration/test_concurrency.py
import asyncio
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import User, Wallet
from app.repositories import WalletRepository


async def _seed_wallets(
        sessionmaker: async_sessionmaker,
) -> tuple[UUID, UUID]:
    """Create two users with USD wallets, the first funded with 1000."""
    async with sessionmaker() as session:
        sender_user = User(username='race_sender', hashed_password='x')
        receiver_user = User(username='race_receiver', hashed_password='x')
        session.add_all([sender_user, receiver_user])
        await session.flush()

        sender = Wallet(
            user_id=sender_user.id, currency='USD', balance=Decimal('1000')
        )
        receiver = Wallet(
            user_id=receiver_user.id, currency='USD'
        )
        session.add_all([sender, receiver])
        await session.commit()

        return sender.id, receiver.id


async def test_wallet_row_is_locked_for_concurrent_update(
        committing_sessionmaker: async_sessionmaker,
):
    """
    A wallet locked by one transaction is not grantable to another.

    This is what prevents two concurrent transfers from reading the same
    balance and both deciding it is sufficient (lost update).
    """
    sender_id, _ = await _seed_wallets(committing_sessionmaker)

    async with committing_sessionmaker() as first:
        await WalletRepository(first).get_wallets_for_update([sender_id])
        # Lock held: `first` has not committed yet.

        async with committing_sessionmaker() as second:
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(1):
                    await WalletRepository(second).get_wallets_for_update(
                        [sender_id]
                    )
