# tests/helpers.py
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntryType
from app.models import Transaction, Wallet


async def assert_double_entry(
        session: AsyncSession,
        group_id: UUID,
        debit_wallet_id: UUID,
        credit_wallet_id: UUID,
        amount: Decimal,
        transaction_type: str,
) -> None:
    """Assert the ledger holds exactly one balanced DEBIT/CREDIT pair."""
    result = await session.execute(
        select(Transaction).where(Transaction.group_id == group_id)
    )
    entries = result.scalars().all()
    assert len(entries) == 2

    transactions_by_type = {e.entry_type: e for e in entries}
    debit_transaction = transactions_by_type[EntryType.DEBIT]
    credit_transaction = transactions_by_type[EntryType.CREDIT]
    assert (transaction_type == debit_transaction.transaction_type
            == credit_transaction.transaction_type)
    assert debit_transaction.amount > 0 and credit_transaction.amount > 0
    assert amount == debit_transaction.amount == credit_transaction.amount
    assert debit_transaction.wallet_id == debit_wallet_id
    assert credit_transaction.wallet_id == credit_wallet_id
