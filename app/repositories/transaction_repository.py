# app/repositories/wallet_repository.py
from decimal import Decimal
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.models import Transaction


class TransactionRepository:

    def __init__(self, db: AsyncSession = Depends(get_async_session)):
        self._db = db

    async def create_entry(
            self,
            wallet_id: UUID,
            entry_type: str,
            amount: Decimal,
            group_id: UUID,
            transaction_type: str
    ) -> Transaction:
        payload = {
            'wallet_id': wallet_id,
            'entry_type': entry_type,
            'amount': amount,
            'group_id': group_id,
            'transaction_type': transaction_type
        }
        transaction = Transaction(**payload)
        self._db.add(transaction)
        return transaction
